from __future__ import annotations

from pydantic import BaseModel, Field


class ExecutionPolicy(BaseModel):
    mode: str = Field(default="visual", description="visual|headless")
    browser: str = Field(default="chromium")
    slow_mo_ms: int = Field(default=1000, ge=0)
    headed: bool = True
    max_parallel_workers: int = Field(default=1, ge=1)


class Phase10Scope(BaseModel):
    version: str = "phase10.0"
    objective: str = "Execution contract and runtime policy hardening"
    guarantees: list[str] = Field(default_factory=list)
    non_goals: list[str] = Field(default_factory=list)


class RuntimeCapabilities(BaseModel):
    playwright_installed: bool = False
    playwright_version: str | None = None
    browser_types: list[str] = Field(default_factory=list)
    browser_installations: dict[str, bool] = Field(default_factory=dict)


class RuntimeCheckResult(BaseModel):
    version: str = "phase10.1"
    ready: bool = False
    policy: ExecutionPolicy
    capabilities: RuntimeCapabilities
    launch_probe_attempted: bool = False
    launch_probe_ok: bool = False
    diagnostics: list[str] = Field(default_factory=list)
