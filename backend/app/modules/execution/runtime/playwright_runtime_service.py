from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path

from app.core import config
from app.modules.execution.contracts.models import (
    ExecutionPolicy,
    RuntimeCapabilities,
    RuntimeCheckResult,
)


class PlaywrightRuntimeService:
    def __init__(self) -> None:
        headed = not config.PLAYWRIGHT_HEADLESS
        self._policy = ExecutionPolicy(
            mode="visual" if headed else "headless",
            browser="chromium",
            slow_mo_ms=max(0, config.EXECUTION_VISUAL_SLOW_MO_MS),
            headed=headed,
            max_parallel_workers=max(1, config.EXECUTION_MAX_PARALLEL_WORKERS),
        )

    def get_execution_policy(self) -> ExecutionPolicy:
        return self._policy

    async def check_runtime(self, *, launch_probe: bool = False) -> RuntimeCheckResult:
        diagnostics: list[str] = []

        try:
            pw_version = package_version("playwright")
            playwright_installed = True
        except PackageNotFoundError:
            pw_version = None
            playwright_installed = False
            diagnostics.append("Playwright package is not installed in the backend environment.")

        browser_types: list[str] = []
        browser_installations: dict[str, bool] = {}
        launch_probe_ok = False

        if playwright_installed:
            from playwright.async_api import async_playwright

            async with async_playwright() as pw:
                for name in ("chromium", "firefox", "webkit"):
                    browser_type = getattr(pw, name, None)
                    if browser_type is not None:
                        browser_types.append(name)
                        executable = ""
                        try:
                            executable = str(browser_type.executable_path or "")
                        except Exception:
                            executable = ""
                        browser_installations[name] = bool(executable and Path(executable).exists())

                if launch_probe:
                    try:
                        browser = await pw.chromium.launch(
                            headless=not self._policy.headed,
                            slow_mo=self._policy.slow_mo_ms,
                        )
                        await browser.close()
                        launch_probe_ok = True
                    except Exception as exc:
                        diagnostics.append(f"Chromium launch probe failed: {exc}")

        if playwright_installed and browser_types and not any(browser_installations.values()):
            diagnostics.append(
                "Playwright browsers are not installed for this environment. "
                "Run: python -m playwright install chromium"
            )

        if self._policy.max_parallel_workers != 1:
            diagnostics.append("Phase 10 policy expects sequential execution (max_parallel_workers=1).")

        ready = playwright_installed and bool(browser_types) and any(browser_installations.values())
        if launch_probe:
            ready = ready and launch_probe_ok

        return RuntimeCheckResult(
            ready=ready,
            policy=self._policy,
            capabilities=RuntimeCapabilities(
                playwright_installed=playwright_installed,
                playwright_version=pw_version,
                browser_types=browser_types,
                browser_installations=browser_installations,
            ),
            launch_probe_attempted=launch_probe,
            launch_probe_ok=launch_probe_ok,
            diagnostics=diagnostics,
        )
