from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES_DIR = ROOT / "app" / "modules"


FORBIDDEN_DIRECT_STORE = [
    "from app.infrastructure.store import store",
    "from app.infrastructure.store.core import",
]


def _agent_name_from_path(path: Path) -> str | None:
    for part in path.parts:
        if part.startswith("agent"):
            return part
    return None


def _scan() -> list[dict]:
    violations: list[dict] = []

    for path in MODULES_DIR.rglob("*.py"):
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        agent_name = _agent_name_from_path(rel)
        if agent_name is None:
            continue

        in_mcp_package = "/mcp/" in rel.as_posix()

        if not in_mcp_package:
            for marker in FORBIDDEN_DIRECT_STORE:
                if marker in text:
                    violations.append(
                        {
                            "file": rel.as_posix(),
                            "rule": "direct_store_import_outside_mcp",
                            "marker": marker,
                        }
                    )

        for other_agent in ["agent1", "agent2", "agent3"]:
            if other_agent == agent_name:
                continue
            forbidden_cross_repo = f"from app.modules.{other_agent}.db."
            if forbidden_cross_repo in text:
                violations.append(
                    {
                        "file": rel.as_posix(),
                        "rule": "cross_agent_db_import_outside_mcp",
                        "marker": forbidden_cross_repo,
                    }
                )

    return violations


def main() -> int:
    violations = _scan()
    if violations:
        print({"ok": False, "violations": violations})
        return 1

    print({"ok": True, "checked": str(MODULES_DIR)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
