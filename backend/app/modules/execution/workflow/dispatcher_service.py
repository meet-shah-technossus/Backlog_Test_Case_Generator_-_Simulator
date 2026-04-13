from __future__ import annotations

import asyncio

from app.core import config
from app.modules.execution.workflow.lifecycle_service import ExecutionLifecycleService


class ExecutionDispatcherService:
    def __init__(self, lifecycle_service: ExecutionLifecycleService) -> None:
        self._lifecycle = lifecycle_service
        self._stop_event = asyncio.Event()
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._recovered_total = 0
        self._last_recovered_count = 0
        self._expired_total = 0
        self._last_expired_count = 0

    async def start(self) -> None:
        if self._running:
            return

        self._stop_event.clear()
        workers = max(1, config.EXECUTION_DISPATCHER_WORKERS)
        self._tasks = [
            asyncio.create_task(self._worker_loop(index + 1), name=f"execution-dispatcher-{index + 1}")
            for index in range(workers)
        ]
        self._running = True

    async def stop(self) -> None:
        if not self._running:
            return

        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        self._running = False

    async def _worker_loop(self, worker_id: int) -> None:
        poll_seconds = max(0.1, config.EXECUTION_QUEUE_POLL_MS / 1000.0)
        while not self._stop_event.is_set():
            try:
                recovery = self._lifecycle.recover_stale_executions(
                    ttl_seconds=config.EXECUTION_PENDING_TTL_SECONDS,
                )
                recovered_count = int(recovery.get("recovered_count") or 0)
                self._last_recovered_count = recovered_count
                self._recovered_total += recovered_count

                expiration = self._lifecycle.expire_pending_executions(
                    ttl_seconds=config.EXECUTION_PENDING_TTL_SECONDS,
                )
                expired_count = int(expiration.get("expired_count") or 0)
                self._last_expired_count = expired_count
                self._expired_total += expired_count

                processed = await self._lifecycle.dispatch_next_queued_execution(
                    started_by=f"dispatcher-{worker_id}"
                )
                if processed is None:
                    await asyncio.sleep(poll_seconds)
            except asyncio.CancelledError:
                raise
            except Exception:
                await asyncio.sleep(poll_seconds)

    def status(self) -> dict:
        return {
            "running": self._running,
            "configured_workers": max(1, config.EXECUTION_DISPATCHER_WORKERS),
            "active_tasks": len([task for task in self._tasks if not task.done()]),
            "poll_ms": config.EXECUTION_QUEUE_POLL_MS,
            "pending_ttl_seconds": config.EXECUTION_PENDING_TTL_SECONDS,
            "recovered_total": self._recovered_total,
            "last_recovered_count": self._last_recovered_count,
            "expired_total": self._expired_total,
            "last_expired_count": self._last_expired_count,
        }
