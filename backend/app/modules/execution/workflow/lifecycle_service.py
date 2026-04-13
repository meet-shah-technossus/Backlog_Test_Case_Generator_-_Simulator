from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import platform
import re
import shutil
import traceback
from datetime import datetime, timezone
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from uuid import uuid4

from app.core import config
from app.infrastructure.store import store
from app.infrastructure.telemetry_service import log_stage_event
from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.execution.db.execution_run_repository import ExecutionRunRepository
from app.modules.execution.runtime.playwright_runtime_service import PlaywrightRuntimeService


class ExecutionLifecycleService:
    TERMINAL_STATES = {"completed", "failed", "canceled"}
    PAUSABLE_STATES = {"queued", "running"}

    def __init__(
        self,
        execution_repo: ExecutionRunRepository,
        agent4_run_repo: Agent4RunRepository,
        runtime_service: PlaywrightRuntimeService,
    ) -> None:
        self._execution_repo = execution_repo
        self._agent4_run_repo = agent4_run_repo
        self._runtime_service = runtime_service

    @staticmethod
    def _infer_target_url_from_text(value: str) -> str | None:
        text = str(value or "").lower()
        if not text:
            return None
        mapping = {
            "amazon": "https://www.amazon.in",
            "airbnb": "https://www.airbnb.com",
            "booking.com": "https://www.booking.com",
            "flipkart": "https://www.flipkart.com",
            "myntra": "https://www.myntra.com",
            "walmart": "https://www.walmart.com",
            "ebay": "https://www.ebay.com",
        }
        for keyword, url in mapping.items():
            if keyword in text:
                return url
        return None

    def _resolve_target_url(self, *, run: dict, requested_target_url: str | None) -> str | None:
        direct = str(requested_target_url or "").strip()
        if direct:
            return direct

        backlog_item_id = str(run.get("backlog_item_id") or "").strip()
        if not backlog_item_id:
            return None

        backlog_item = store.get_backlog_item(backlog_item_id)
        if isinstance(backlog_item, dict):
            stored = str(backlog_item.get("target_url") or "").strip()
            if stored:
                return stored

            title = str(backlog_item.get("story_title") or "")
            description = str(backlog_item.get("story_description") or "")
            return self._infer_target_url_from_text(f"{title} {description}")

        return None

    def enqueue_execution(
        self,
        *,
        agent4_run_id: str,
        requested_by: str,
        reason: str | None = None,
        max_attempts: int = 1,
        target_url: str | None = None,
        max_scripts: int | None = None,
        early_stop_after_failures: int | None = None,
        parallel_workers: int | None = None,
        selected_script_paths: list[str] | None = None,
        use_smoke_probe_script: bool = False,
    ) -> dict:
        run = self._agent4_run_repo.get_run(agent4_run_id)
        if not run:
            raise ValueError(f"Agent4 run '{agent4_run_id}' not found")

        execution_run_id = str(uuid4())
        resolved_target_url = self._resolve_target_url(run=run, requested_target_url=target_url)
        request_payload = {
            "requested_by": requested_by,
            "reason": reason,
            "target_url": resolved_target_url,
            "max_scripts": max_scripts,
            "early_stop_after_failures": early_stop_after_failures,
            "parallel_workers": parallel_workers,
            "selected_script_paths": selected_script_paths,
            "use_smoke_probe_script": bool(use_smoke_probe_script),
        }

        execution = self._execution_repo.create_run(
            execution_run_id=execution_run_id,
            source_agent4_run_id=agent4_run_id,
            backlog_item_id=str(run.get("backlog_item_id") or "") or None,
            trace_id=str(run.get("trace_id") or f"agent4-{agent4_run_id}"),
            state="queued",
            stage="phase10_execution_queued",
            request_payload=request_payload,
            runtime_policy=self._runtime_service.get_execution_policy().model_dump(),
            max_attempts=max_attempts,
        )
        self._emit_queue_lifecycle_event(
            stage="queue.enqueue",
            status="queued",
            snapshot=execution,
            metadata={
                "requested_by": requested_by,
                "reason": reason,
                "max_attempts": max_attempts,
                "source_agent4_run_id": agent4_run_id,
            },
        )
        return execution

    @staticmethod
    def _coerce_target_url(value: str | None) -> str:
        candidate = str(value or "").strip()
        if not candidate:
            return "about:blank"
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate
        return f"https://{candidate}"

    @staticmethod
    def _rewrite_script_for_target_url(content: str, target_url: str) -> str:
        patched = content
        patched = patched.replace('await page.goto("/")', f'await page.goto("{target_url}")')
        patched = patched.replace("await page.goto('/')", f'await page.goto("{target_url}")')

        # Auto-heal a common brittle selector pattern in generated scripts so
        # existing persisted bundles can execute without regeneration.
        pattern = re.compile(
            r'(?m)^\s*await\s+page\.locator\(["\']input\[type=(["\'])search\1\]["\']\)\.fill\((["\'])(.*?)\2\)\s*$'
        )
        if pattern.search(patched):
            helper = (
                "\n"
                "async def __copilot_fill_search(page, value):\n"
                "    selectors = [\n"
                "        \"input[type='search']\",\n"
                "        \"#twotabsearchtextbox\",\n"
                "        \"input[name='field-keywords']\",\n"
                "        \"input[name='q']\",\n"
                "        \"input[aria-label*='Search' i]\",\n"
                "        \"input[placeholder*='Search' i]\",\n"
                "    ]\n"
                "    for selector in selectors:\n"
                "        locator = page.locator(selector).first\n"
                "        if await locator.count() > 0:\n"
                "            await locator.fill(value)\n"
                "            return\n"
                "    raise AssertionError(f\"search input not found for value '{value}'\")\n"
                "\n"
            )
            if "async def __copilot_fill_search(page, value):" not in patched:
                anchor = "from playwright.async_api import Page, expect\n\n"
                if anchor in patched:
                    patched = patched.replace(anchor, anchor + helper, 1)
                else:
                    patched = helper + patched

            patched = pattern.sub(r"    await __copilot_fill_search(page, \2\3\2)", patched)
        return patched

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        text = str(value or "").strip()
        if not text:
            return None
        normalized = text.replace(" ", "T")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _queue_telemetry_context(self, snapshot: dict) -> tuple[str, str | None]:
        trace_id = str(snapshot.get("trace_id") or "").strip()
        story_id = str(snapshot.get("backlog_item_id") or "").strip() or None

        source_agent4_run_id = str(snapshot.get("source_agent4_run_id") or "").strip()
        if source_agent4_run_id:
            source_run = self._agent4_run_repo.get_run(source_agent4_run_id)
            if source_run:
                if not trace_id:
                    trace_id = str(source_run.get("trace_id") or "").strip()
                if not story_id:
                    source_story = str(source_run.get("backlog_item_id") or "").strip()
                    if source_story:
                        story_id = source_story

        if not trace_id:
            execution_run_id = str(snapshot.get("execution_run_id") or "unknown")
            trace_id = f"execution-{execution_run_id}"

        return trace_id, story_id

    def _emit_queue_lifecycle_event(
        self,
        *,
        stage: str,
        status: str,
        snapshot: dict,
        duration_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        trace_id, story_id = self._queue_telemetry_context(snapshot)
        execution_run_id = str(snapshot.get("execution_run_id") or "").strip() or None
        payload = metadata if isinstance(metadata, dict) else {}
        try:
            log_stage_event(
                trace_id=trace_id,
                stage=stage,
                status=status,
                run_id=execution_run_id,
                story_id=story_id,
                duration_ms=duration_ms,
                error_code=error_code,
                error_message=error_message,
                metadata=payload,
            )
        except Exception:
            # Telemetry must never break execution flow.
            return

    @staticmethod
    def _sha256_json(payload: dict) -> str:
        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _sha256_text(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_target_closed_error(exc: Exception) -> bool:
        message = str(exc).lower()
        return "target page, context or browser has been closed" in message

    async def _safe_playwright_cleanup(
        self,
        action: Callable[[], Awaitable[None]],
        *,
        label: str,
        warnings: list[str],
    ) -> None:
        try:
            await action()
        except Exception as exc:
            if not self._is_target_closed_error(exc):
                warnings.append(f"{label}: {exc}")

    def _artifacts_root(self) -> Path:
        backend_root = Path(__file__).resolve().parents[4]
        root = backend_root / "execution_artifacts"
        root.mkdir(parents=True, exist_ok=True)
        return root

    def _prepare_execution_workspace(self, execution_run_id: str) -> Path:
        root = self._artifacts_root() / execution_run_id
        (root / "screenshots").mkdir(parents=True, exist_ok=True)
        (root / "traces").mkdir(parents=True, exist_ok=True)
        (root / "videos").mkdir(parents=True, exist_ok=True)
        (root / "logs").mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _relative_artifact_path(path: Path) -> str:
        parts = path.parts
        if "execution_artifacts" in parts:
            idx = parts.index("execution_artifacts")
            return "/".join(parts[idx:])
        return str(path)

    def _find_latest_script_bundle_for_agent4_run(self, agent4_run_id: str) -> dict:
        artifacts = self._agent4_run_repo.get_artifacts(agent4_run_id)
        for artifact_row in artifacts:
            artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
            if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
                return artifact
        raise ValueError(f"Agent4 run '{agent4_run_id}' has no generated script bundle")

    async def _execute_single_script(
        self,
        *,
        script: dict,
        page,
        context,
        target_url: str,
        workspace: Path,
        step_index: int,
    ) -> dict[str, object]:
        path = str(script.get("path") or "tests/generated/unknown.py")
        raw_content = str(script.get("content") or "")
        content = self._rewrite_script_for_target_url(raw_content, target_url)
        started_at = self._utc_now_iso()
        started_perf = asyncio.get_running_loop().time()
        evidence: dict[str, object] = {
            "screenshot_path": None,
            "trace_path": None,
            "video_path": None,
        }
        metadata: dict[str, object] = {
            "script_hash": self._sha256_text(content),
            "script_case_id": str(script.get("case_id") or ""),
        }

        try:
            code = compile(content, path, "exec")
        except Exception as exc:
            finished_at = self._utc_now_iso()
            return {
                "script_path": path,
                "status": "failed",
                "error_code": "compile_error",
                "error_message": str(exc),
                "stack_trace": traceback.format_exc(),
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": int((asyncio.get_running_loop().time() - started_perf) * 1000),
                "evidence": evidence,
                "metadata": metadata,
            }

        namespace: dict = {}
        try:
            exec(code, namespace)
        except Exception as exc:
            finished_at = self._utc_now_iso()
            return {
                "script_path": path,
                "status": "failed",
                "error_code": "import_or_exec_error",
                "error_message": str(exc),
                "stack_trace": traceback.format_exc(),
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": int((asyncio.get_running_loop().time() - started_perf) * 1000),
                "evidence": evidence,
                "metadata": metadata,
            }

        async_test_fn = None
        for name, value in namespace.items():
            if name.startswith("test_") and inspect.iscoroutinefunction(value):
                async_test_fn = value
                break

        if async_test_fn is None:
            finished_at = self._utc_now_iso()
            return {
                "script_path": path,
                "status": "failed",
                "error_code": "missing_async_test",
                "error_message": "No async test_* function found in script",
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": int((asyncio.get_running_loop().time() - started_perf) * 1000),
                "evidence": evidence,
                "metadata": metadata,
            }

        try:
            step_slug = f"{step_index:03d}_{Path(path).stem}"
            trace_path = workspace / "traces" / f"{step_slug}.zip"
            screenshot_path = workspace / "screenshots" / f"{step_slug}.png"
            cleanup_warnings: list[str] = []

            await context.tracing.start(screenshots=True, snapshots=True, sources=True)
            await async_test_fn(page)

            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
            except Exception as exc:
                if not self._is_target_closed_error(exc):
                    raise
                cleanup_warnings.append(f"screenshot skipped: {exc}")

            await self._safe_playwright_cleanup(
                lambda: context.tracing.stop(path=str(trace_path)),
                label="tracing.stop",
                warnings=cleanup_warnings,
            )

            if screenshot_path.exists():
                evidence["screenshot_path"] = self._relative_artifact_path(screenshot_path)
            if trace_path.exists():
                evidence["trace_path"] = self._relative_artifact_path(trace_path)
            if cleanup_warnings:
                metadata["cleanup_warnings"] = cleanup_warnings

            finished_at = self._utc_now_iso()
            return {
                "script_path": path,
                "status": "passed",
                "error_code": None,
                "error_message": None,
                "stack_trace": None,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": int((asyncio.get_running_loop().time() - started_perf) * 1000),
                "evidence": evidence,
                "metadata": metadata,
            }
        except Exception as exc:
            full_trace = traceback.format_exc()
            finished_at = self._utc_now_iso()
            error_code = "target_closed" if self._is_target_closed_error(exc) else "runtime_error"
            return {
                "script_path": path,
                "status": "failed",
                "error_code": error_code,
                "error_message": str(exc),
                "stack_trace": full_trace,
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": int((asyncio.get_running_loop().time() - started_perf) * 1000),
                "evidence": evidence,
                "metadata": metadata,
            }

    async def _emit(
        self,
        on_event: Callable[[dict], Awaitable[None]] | None,
        payload: dict,
    ) -> None:
        if on_event is not None:
            await on_event(payload)

    async def _wait_while_paused(
        self,
        *,
        execution_run_id: str,
        on_event: Callable[[dict], Awaitable[None]] | None,
    ) -> dict | None:
        pause_reported = False
        while True:
            snapshot = self.get_execution(execution_run_id)
            state = str(snapshot.get("state") or "")

            if state in self.TERMINAL_STATES:
                return snapshot

            if state != "paused":
                if pause_reported:
                    await self._emit(
                        on_event,
                        {
                            "type": "run_resumed",
                            "execution_run_id": execution_run_id,
                            "state": state,
                        },
                    )
                return None

            if not pause_reported:
                await self._emit(
                    on_event,
                    {
                        "type": "run_paused",
                        "execution_run_id": execution_run_id,
                    },
                )
                pause_reported = True

            await asyncio.sleep(0.2)

    async def _run_bundle(
        self,
        *,
        execution_run_id: str,
        started_by: str,
        on_event: Callable[[dict], Awaitable[None]] | None,
    ) -> dict:
        snapshot = self.get_execution(execution_run_id)
        source_agent4_run_id = str(snapshot.get("source_agent4_run_id") or "")
        if not source_agent4_run_id:
            raise ValueError("Execution run missing source Agent4 run id")

        runtime = await self._runtime_service.check_runtime(launch_probe=True)
        if not runtime.ready:
            raise RuntimeError("Execution runtime is not ready for Playwright execution")

        bundle = self._find_latest_script_bundle_for_agent4_run(source_agent4_run_id)
        scripts = bundle.get("scripts") if isinstance(bundle, dict) else []
        scripts = scripts if isinstance(scripts, list) else []

        raw_request = snapshot.get("request")
        request_payload: dict[str, object]
        if isinstance(raw_request, dict):
            request_payload = raw_request
        else:
            request_payload = {}

        use_smoke_probe_script = bool(request_payload.get("use_smoke_probe_script") is True)
        if use_smoke_probe_script:
            scripts = [
                {
                    "case_id": "probe-smoke",
                    "path": "tests/generated/probe_smoke.py",
                    "content": (
                        "async def test_probe_smoke(page):\n"
                        "    await page.goto('about:blank')\n"
                        "    await page.set_content('<main id=\"probe\">probe-smoke-pass</main>')\n"
                        "    value = await page.text_content('#probe')\n"
                        "    assert value == 'probe-smoke-pass'\n"
                        "    await page.wait_for_timeout(350)\n"
                    ),
                }
            ]

        raw_selected_script_paths = request_payload.get("selected_script_paths")
        selected_script_paths = {
            str(item).strip()
            for item in (raw_selected_script_paths if isinstance(raw_selected_script_paths, list) else [])
            if str(item).strip()
        }
        if selected_script_paths:
            filtered_scripts = [
                script
                for script in scripts
                if isinstance(script, dict) and str(script.get("path") or "").strip() in selected_script_paths
            ]
            if not filtered_scripts:
                raise ValueError("Selected script paths do not match any generated scripts for this run")
            scripts = filtered_scripts

        raw_max_scripts = request_payload.get("max_scripts")
        if isinstance(raw_max_scripts, int) and raw_max_scripts > 0:
            scripts = scripts[:raw_max_scripts]

        if not scripts:
            raise ValueError("Generated script bundle has no scripts")

        raw_target_url = request_payload.get("target_url")
        target_url = self._coerce_target_url(raw_target_url if isinstance(raw_target_url, str) else None)
        workspace = self._prepare_execution_workspace(execution_run_id)

        raw_runtime_policy = snapshot.get("runtime_policy")
        runtime_policy: dict[str, object]
        if isinstance(raw_runtime_policy, dict):
            runtime_policy = raw_runtime_policy
        else:
            runtime_policy = {}

        raw_early_stop = request_payload.get("early_stop_after_failures")
        early_stop_after_failures = raw_early_stop if isinstance(raw_early_stop, int) and raw_early_stop > 0 else 0

        # Keep a single browser session/page for the full batch so UI/evidence
        # reflects one continuous execution and avoids browser relaunch per case.
        worker_count = 1

        await self._emit(
            on_event,
            {
                "type": "run_started",
                "execution_run_id": execution_run_id,
                "script_count": len(scripts),
                "target_url": target_url,
                "worker_count": worker_count,
                "early_stop_after_failures": early_stop_after_failures,
                "use_smoke_probe_script": use_smoke_probe_script,
                "workspace": self._relative_artifact_path(workspace),
            },
        )

        step_results: list[dict[str, object]] = []
        remaining_indexes = list(range(1, len(scripts) + 1))
        stop_scheduling = False
        failed_count = 0
        step_timeout = max(1, min(config.EXECUTION_SCRIPT_TIMEOUT_SECONDS, config.EXECUTION_RUN_TIMEOUT_SECONDS))
        shared_video_path: str | None = None

        from playwright.async_api import async_playwright

        browser_name = str(runtime_policy.get("browser") or "chromium")
        headed = bool(runtime_policy.get("headed", True))
        raw_slow_mo = runtime_policy.get("slow_mo_ms")
        slow_mo_ms = int(raw_slow_mo) if isinstance(raw_slow_mo, (int, float, str)) else 0

        async with async_playwright() as pw:
            launcher = getattr(pw, browser_name, pw.chromium)
            browser = await launcher.launch(headless=not headed, slow_mo=slow_mo_ms)
            if config.EXECUTION_CAPTURE_VIDEO:
                context = await browser.new_context(
                    record_video_dir=str(workspace / "videos"),
                    record_video_size={
                        "width": max(320, int(config.EXECUTION_VIDEO_WIDTH)),
                        "height": max(240, int(config.EXECUTION_VIDEO_HEIGHT)),
                    },
                )
            else:
                context = await browser.new_context()

            page = await context.new_page()
            page.set_default_timeout(min(8_000, max(1_000, config.EXECUTION_SCRIPT_TIMEOUT_SECONDS * 1000 - 500)))

            for index, script in enumerate(scripts, start=1):
                if stop_scheduling:
                    break

                terminal_snapshot = await self._wait_while_paused(
                    execution_run_id=execution_run_id,
                    on_event=on_event,
                )
                if terminal_snapshot is not None:
                    stop_scheduling = True
                    break

                script_path = str((script or {}).get("path") or f"script_{index}.py")
                await self._emit(
                    on_event,
                    {
                        "type": "step_started",
                        "execution_run_id": execution_run_id,
                        "step_index": index,
                        "script_path": script_path,
                    },
                )

                try:
                    step_result: dict[str, object] = await asyncio.wait_for(
                        self._execute_single_script(
                            script=script,
                            page=page,
                            context=context,
                            target_url=target_url,
                            workspace=workspace,
                            step_index=index,
                        ),
                        timeout=step_timeout,
                    )
                except asyncio.TimeoutError:
                    step_result = {
                        "script_path": script_path,
                        "status": "failed",
                        "error_code": "script_timeout",
                        "error_message": "Script execution timed out",
                        "stack_trace": None,
                        "started_at": None,
                        "finished_at": self._utc_now_iso(),
                        "duration_ms": step_timeout * 1000,
                        "evidence": {
                            "screenshot_path": None,
                            "trace_path": None,
                            "video_path": None,
                        },
                        "metadata": {},
                    }

                step_result["step_index"] = index
                step_results.append(step_result)
                if index in remaining_indexes:
                    remaining_indexes.remove(index)

                if step_result.get("status") == "failed":
                    failed_count += 1
                    if early_stop_after_failures > 0 and failed_count >= early_stop_after_failures:
                        stop_scheduling = True

                await self._emit(
                    on_event,
                    {
                        "type": "step_finished",
                        "execution_run_id": execution_run_id,
                        "step_index": index,
                        "result": step_result,
                    },
                )

            video = page.video
            await self._safe_playwright_cleanup(page.close, label="page.close", warnings=[])
            if video is not None:
                try:
                    video_path_raw = await video.path()
                    if video_path_raw:
                        source_video_path = Path(video_path_raw)
                        if source_video_path.exists():
                            video_output_path = workspace / "videos" / f"{execution_run_id}.webm"
                            if source_video_path != video_output_path:
                                shutil.copy2(source_video_path, video_output_path)
                            shared_video_path = self._relative_artifact_path(video_output_path)
                except Exception:
                    shared_video_path = None

            await self._safe_playwright_cleanup(context.close, label="context.close", warnings=[])
            await self._safe_playwright_cleanup(browser.close, label="browser.close", warnings=[])

        final_control_snapshot = self.get_execution(execution_run_id)
        final_control_state = str(final_control_snapshot.get("state") or "")
        if final_control_state in self.TERMINAL_STATES:
            return {
                "aborted": True,
                "aborted_state": final_control_state,
                "execution_run_id": execution_run_id,
            }

        if stop_scheduling and remaining_indexes:
            for idx in sorted(remaining_indexes):
                script = scripts[idx - 1] if idx - 1 < len(scripts) else {}
                script_path = str((script or {}).get("path") or f"script_{idx}.py")
                skipped_result: dict[str, object] = {
                    "script_path": script_path,
                    "status": "skipped",
                    "error_code": "early_stop",
                    "error_message": "Execution stopped after failure threshold",
                    "stack_trace": None,
                    "started_at": None,
                    "finished_at": self._utc_now_iso(),
                    "duration_ms": 0,
                    "evidence": {
                        "screenshot_path": None,
                        "trace_path": None,
                        "video_path": None,
                    },
                    "metadata": {},
                    "step_index": idx,
                }
                step_results.append(skipped_result)
                await self._emit(
                    on_event,
                    {
                        "type": "step_skipped",
                        "execution_run_id": execution_run_id,
                        "step_index": idx,
                        "result": skipped_result,
                    },
                )

        def _step_index(item: dict[str, object]) -> int:
            value = item.get("step_index")
            return value if isinstance(value, int) else 0

        step_results.sort(key=_step_index)

        passed = sum(1 for item in step_results if item.get("status") == "passed")
        failed = sum(1 for item in step_results if item.get("status") == "failed")
        skipped = sum(1 for item in step_results if item.get("status") == "skipped")

        artifact_hash_input = {
            "execution_run_id": execution_run_id,
            "source_agent4_run_id": source_agent4_run_id,
            "target_url": target_url,
            "scripts": [
                {
                    "path": str((script or {}).get("path") or ""),
                    "content_hash": self._sha256_text(str((script or {}).get("content") or "")),
                }
                for script in scripts
            ],
        }
        runner_config_snapshot = {
            "runtime_policy": runtime_policy,
            "step_timeout_seconds": step_timeout,
            "run_timeout_seconds": config.EXECUTION_RUN_TIMEOUT_SECONDS,
            "script_timeout_seconds": config.EXECUTION_SCRIPT_TIMEOUT_SECONDS,
            "worker_count": worker_count,
            "early_stop_after_failures": early_stop_after_failures,
            "use_smoke_probe_script": use_smoke_probe_script,
        }
        environment_metadata = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "playwright_version": runtime.capabilities.playwright_version,
            "browser_types": runtime.capabilities.browser_types,
        }

        screenshot_paths: list[str] = []
        trace_paths: list[str] = []
        video_paths: list[str] = []
        for item in step_results:
            raw_evidence = item.get("evidence")
            if not isinstance(raw_evidence, dict):
                continue
            if shared_video_path and not raw_evidence.get("video_path"):
                raw_evidence["video_path"] = shared_video_path
            screenshot_path = raw_evidence.get("screenshot_path")
            trace_path = raw_evidence.get("trace_path")
            video_path = raw_evidence.get("video_path")
            if isinstance(screenshot_path, str) and screenshot_path:
                screenshot_paths.append(screenshot_path)
            if isinstance(trace_path, str) and trace_path:
                trace_paths.append(trace_path)
            if isinstance(video_path, str) and video_path:
                video_paths.append(video_path)

        evidence_manifest = {
            "workspace": self._relative_artifact_path(workspace),
            "step_count": len(step_results),
            "screenshots": screenshot_paths,
            "traces": trace_paths,
            "videos": video_paths,
        }

        return {
            "started_by": started_by,
            "simulated": False,
            "runtime_ready": runtime.ready,
            "launch_probe_ok": runtime.launch_probe_ok,
            "playwright_version": runtime.capabilities.playwright_version,
            "target_url": target_url,
            "worker_count": worker_count,
            "early_stop_after_failures": early_stop_after_failures,
            "use_smoke_probe_script": use_smoke_probe_script,
            "stopped_early": bool(stop_scheduling),
            "script_count": len(step_results),
            "passed_count": passed,
            "failed_count": failed,
            "skipped_count": skipped,
            "step_results": step_results,
            "per_script_status": [
                {
                    "script_path": item.get("script_path"),
                    "step_index": item.get("step_index"),
                    "status": item.get("status"),
                    "duration_ms": item.get("duration_ms"),
                    "error_code": item.get("error_code"),
                }
                for item in step_results
            ],
            "summary": {
                "total": len(step_results),
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "final_verdict": "passed" if failed == 0 else "failed",
            },
            "evidence": evidence_manifest,
            "integrity": {
                "artifact_hash": self._sha256_json(artifact_hash_input),
                "runner_config_hash": self._sha256_json(runner_config_snapshot),
                "runner_config_snapshot": runner_config_snapshot,
                "environment_metadata": environment_metadata,
            },
        }

    def get_execution(self, execution_run_id: str) -> dict:
        snapshot = self._execution_repo.get_run(execution_run_id)
        if not snapshot:
            raise ValueError(f"Execution run '{execution_run_id}' not found")
        return snapshot

    def list_for_agent4_run(self, agent4_run_id: str, limit: int = 20) -> list[dict]:
        return self._execution_repo.list_for_agent4_run(agent4_run_id, limit=limit)

    def recover_stale_executions(self, *, ttl_seconds: int) -> dict:
        recovered_ids = self._execution_repo.recover_stale_runs(ttl_seconds=ttl_seconds)
        return {
            "ttl_seconds": max(1, int(ttl_seconds)),
            "recovered_count": len(recovered_ids),
            "recovered_execution_run_ids": recovered_ids,
        }

    def expire_pending_executions(self, *, ttl_seconds: int) -> dict:
        expired_ids = self._execution_repo.expire_pending_runs(ttl_seconds=ttl_seconds)
        ttl_value = max(1, int(ttl_seconds))
        for execution_run_id in expired_ids:
            snapshot = self._execution_repo.get_run(execution_run_id)
            if not snapshot:
                continue
            self._emit_queue_lifecycle_event(
                stage="queue.expire",
                status="expired",
                snapshot=snapshot,
                error_code="pending_ttl_expired",
                error_message="Expired in queue (pending TTL exceeded)",
                metadata={
                    "ttl_seconds": ttl_value,
                    "execution_run_id": execution_run_id,
                },
            )
        return {
            "ttl_seconds": ttl_value,
            "expired_count": len(expired_ids),
            "expired_execution_run_ids": expired_ids,
        }

    def cancel_execution(self, execution_run_id: str, canceled_by: str) -> dict:
        snapshot = self.get_execution(execution_run_id)
        if snapshot.get("state") in self.TERMINAL_STATES:
            return snapshot

        self._execution_repo.update_state(
            execution_run_id=execution_run_id,
            state="canceled",
            stage="phase10_execution_canceled",
            result_payload={"canceled_by": canceled_by},
        )
        final_snapshot = self.get_execution(execution_run_id)
        self._emit_queue_lifecycle_event(
            stage="queue.cancel",
            status="canceled",
            snapshot=final_snapshot,
            metadata={
                "canceled_by": canceled_by,
                "prior_state": str(snapshot.get("state") or ""),
            },
        )
        return final_snapshot

    def pause_execution(self, execution_run_id: str, paused_by: str) -> dict:
        snapshot = self.get_execution(execution_run_id)
        state = str(snapshot.get("state") or "")

        if state in self.TERMINAL_STATES or state == "paused":
            return snapshot
        if state not in self.PAUSABLE_STATES:
            return snapshot

        self._execution_repo.update_state(
            execution_run_id=execution_run_id,
            state="paused",
            stage="phase10_execution_paused",
            result_payload={
                "paused_by": paused_by,
                "paused_at": self._utc_now_iso(),
            },
        )
        return self.get_execution(execution_run_id)

    def resume_execution(self, execution_run_id: str, resumed_by: str) -> dict:
        snapshot = self.get_execution(execution_run_id)
        state = str(snapshot.get("state") or "")

        if state in self.TERMINAL_STATES:
            return snapshot
        if state != "paused":
            return snapshot

        started_at = snapshot.get("started_at")
        resume_to_running = bool(started_at)
        self._execution_repo.update_state(
            execution_run_id=execution_run_id,
            state="running" if resume_to_running else "queued",
            stage="phase10_execution_running" if resume_to_running else "phase10_execution_queued",
            result_payload={
                "resumed_by": resumed_by,
                "resumed_at": self._utc_now_iso(),
            },
        )
        return self.get_execution(execution_run_id)

    async def process_execution(
        self,
        execution_run_id: str,
        *,
        started_by: str = "dispatcher",
        on_event: Callable[[dict], Awaitable[None]] | None = None,
    ) -> dict:
        snapshot = self.get_execution(execution_run_id)
        state = str(snapshot.get("state") or "")
        if state in self.TERMINAL_STATES:
            return snapshot

        if state == "queued":
            self._execution_repo.mark_running(execution_run_id=execution_run_id)
            snapshot = self.get_execution(execution_run_id)
            state = str(snapshot.get("state") or "")
        elif state not in {"running", "paused"}:
            raise ValueError(f"Execution run '{execution_run_id}' is not runnable from state '{state}'")

        created_at = self._parse_dt(str(snapshot.get("created_at") or ""))
        started_at = self._parse_dt(str(snapshot.get("started_at") or ""))
        queue_wait_ms = None
        if created_at and started_at and started_at >= created_at:
            queue_wait_ms = int((started_at - created_at).total_seconds() * 1000)
        self._emit_queue_lifecycle_event(
            stage="queue.run_start",
            status="started",
            snapshot=snapshot,
            duration_ms=queue_wait_ms,
            metadata={
                "started_by": started_by,
                "attempt_count": int(snapshot.get("attempt_count") or 0),
                "max_attempts": int(snapshot.get("max_attempts") or 1),
                "queue_wait_ms": queue_wait_ms,
            },
        )

        try:
            result = await asyncio.wait_for(
                self._run_bundle(
                    execution_run_id=execution_run_id,
                    started_by=started_by,
                    on_event=on_event,
                ),
                timeout=config.EXECUTION_RUN_TIMEOUT_SECONDS,
            )

            aborted_state = str(result.get("aborted_state") or "")
            if aborted_state in self.TERMINAL_STATES:
                final_snapshot = self.get_execution(execution_run_id)
                run_started_at = self._parse_dt(str(final_snapshot.get("started_at") or ""))
                run_completed_at = self._parse_dt(str(final_snapshot.get("completed_at") or ""))
                run_duration_ms = None
                if run_started_at and run_completed_at and run_completed_at >= run_started_at:
                    run_duration_ms = int((run_completed_at - run_started_at).total_seconds() * 1000)
                self._emit_queue_lifecycle_event(
                    stage="queue.run_end",
                    status=aborted_state,
                    snapshot=final_snapshot,
                    duration_ms=run_duration_ms,
                    error_code=str(final_snapshot.get("last_error_code") or "") or None,
                    error_message=str(final_snapshot.get("last_error_message") or "") or None,
                    metadata={
                        "started_by": started_by,
                        "aborted": True,
                        "attempt_count": int(final_snapshot.get("attempt_count") or 0),
                        "max_attempts": int(final_snapshot.get("max_attempts") or 1),
                    },
                )
                await self._emit(on_event, {"type": "run_finished", "execution": final_snapshot})
                return final_snapshot

            if int(result.get("failed_count") or 0) == 0:
                self._execution_repo.update_state(
                    execution_run_id=execution_run_id,
                    state="completed",
                    stage="phase10_execution_completed",
                    result_payload=result,
                )
                final_snapshot = self.get_execution(execution_run_id)
                run_started_at = self._parse_dt(str(final_snapshot.get("started_at") or ""))
                run_completed_at = self._parse_dt(str(final_snapshot.get("completed_at") or ""))
                run_duration_ms = None
                if run_started_at and run_completed_at and run_completed_at >= run_started_at:
                    run_duration_ms = int((run_completed_at - run_started_at).total_seconds() * 1000)
                self._emit_queue_lifecycle_event(
                    stage="queue.run_end",
                    status="completed",
                    snapshot=final_snapshot,
                    duration_ms=run_duration_ms,
                    metadata={
                        "started_by": started_by,
                        "attempt_count": int(final_snapshot.get("attempt_count") or 0),
                        "max_attempts": int(final_snapshot.get("max_attempts") or 1),
                        "failed_count": int(result.get("failed_count") or 0),
                    },
                )
                await self._emit(on_event, {"type": "run_finished", "execution": final_snapshot})
                return final_snapshot

            snapshot = self.get_execution(execution_run_id)
            attempt_count = int(snapshot.get("attempt_count") or 0)
            max_attempts = int(snapshot.get("max_attempts") or 1)
            can_retry = attempt_count < max_attempts
            retry_after_seconds = min(30, 2 ** max(1, attempt_count)) if can_retry else 0

            result_payload = {
                **result,
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
                "retry_queued": can_retry,
                "retry_after_seconds": retry_after_seconds,
            }

            if can_retry:
                self._execution_repo.update_state(
                    execution_run_id=execution_run_id,
                    state="queued",
                    stage="phase10_execution_retry_queued",
                    result_payload=result_payload,
                    last_error_code="execution_step_failures_retrying",
                    last_error_message="One or more scripts failed; retry queued",
                )
            else:
                self._execution_repo.update_state(
                    execution_run_id=execution_run_id,
                    state="failed",
                    stage="phase10_execution_failed",
                    result_payload=result_payload,
                    last_error_code="execution_step_failures",
                    last_error_message="One or more scripts failed",
                )

            final_snapshot = self.get_execution(execution_run_id)
            run_started_at = self._parse_dt(str(final_snapshot.get("started_at") or ""))
            run_completed_at = self._parse_dt(str(final_snapshot.get("completed_at") or ""))
            run_duration_ms = None
            if run_started_at and run_completed_at and run_completed_at >= run_started_at:
                run_duration_ms = int((run_completed_at - run_started_at).total_seconds() * 1000)
            self._emit_queue_lifecycle_event(
                stage="queue.run_end",
                status="retry_queued" if can_retry else "failed",
                snapshot=final_snapshot,
                duration_ms=run_duration_ms,
                error_code=str(final_snapshot.get("last_error_code") or "") or None,
                error_message=str(final_snapshot.get("last_error_message") or "") or None,
                metadata={
                    "started_by": started_by,
                    "attempt_count": attempt_count,
                    "max_attempts": max_attempts,
                    "retry_queued": can_retry,
                    "retry_after_seconds": retry_after_seconds,
                    "failed_count": int(result.get("failed_count") or 0),
                },
            )
            await self._emit(on_event, {"type": "run_finished", "execution": final_snapshot})
            return final_snapshot
        except Exception as exc:
            snapshot = self.get_execution(execution_run_id)
            attempt_count = int(snapshot.get("attempt_count") or 0)
            max_attempts = int(snapshot.get("max_attempts") or 1)
            can_retry = attempt_count < max_attempts
            retry_after_seconds = min(30, 2 ** max(1, attempt_count)) if can_retry else 0

            result_payload = {
                "started_by": started_by,
                "error": str(exc),
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
                "retry_queued": can_retry,
                "retry_after_seconds": retry_after_seconds,
            }
            if can_retry:
                self._execution_repo.update_state(
                    execution_run_id=execution_run_id,
                    state="queued",
                    stage="phase10_execution_retry_queued",
                    result_payload=result_payload,
                    last_error_code="execution_failed_retrying",
                    last_error_message=str(exc),
                )
            else:
                self._execution_repo.update_state(
                    execution_run_id=execution_run_id,
                    state="failed",
                    stage="phase10_execution_failed",
                    result_payload=result_payload,
                    last_error_code="execution_failed",
                    last_error_message=str(exc),
                )
            final_snapshot = self.get_execution(execution_run_id)
            run_started_at = self._parse_dt(str(final_snapshot.get("started_at") or ""))
            run_completed_at = self._parse_dt(str(final_snapshot.get("completed_at") or ""))
            run_duration_ms = None
            if run_started_at and run_completed_at and run_completed_at >= run_started_at:
                run_duration_ms = int((run_completed_at - run_started_at).total_seconds() * 1000)
            self._emit_queue_lifecycle_event(
                stage="queue.run_end",
                status="retry_queued" if can_retry else "failed",
                snapshot=final_snapshot,
                duration_ms=run_duration_ms,
                error_code=str(final_snapshot.get("last_error_code") or "") or None,
                error_message=str(final_snapshot.get("last_error_message") or "") or None,
                metadata={
                    "started_by": started_by,
                    "attempt_count": attempt_count,
                    "max_attempts": max_attempts,
                    "retry_queued": can_retry,
                    "retry_after_seconds": retry_after_seconds,
                },
            )
            await self._emit(on_event, {"type": "run_finished", "execution": final_snapshot})
            return final_snapshot

    async def run_execution_stream(
        self,
        execution_run_id: str,
        *,
        started_by: str = "operator",
    ) -> AsyncGenerator[dict, None]:
        queue: asyncio.Queue[dict] = asyncio.Queue()

        async def _on_event(payload: dict) -> None:
            await queue.put(payload)

        task = asyncio.create_task(
            self.process_execution(
                execution_run_id,
                started_by=started_by,
                on_event=_on_event,
            )
        )

        while True:
            if task.done() and queue.empty():
                break
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=0.2)
                yield payload
            except asyncio.TimeoutError:
                continue

        final_snapshot = await task
        yield {"type": "done", "execution": final_snapshot}

    async def dispatch_next_queued_execution(self, *, started_by: str = "dispatcher") -> dict | None:
        claimed = self._execution_repo.claim_next_queued()
        if not claimed:
            return None
        execution_run_id = str(claimed.get("execution_run_id") or "")
        if not execution_run_id:
            return None
        return await self.process_execution(execution_run_id, started_by=started_by)
