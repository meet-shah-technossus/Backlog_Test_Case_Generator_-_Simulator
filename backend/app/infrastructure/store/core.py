from __future__ import annotations

import json
import hashlib
import hmac
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from app.domain.models import (
    AcceptanceCriterion,
    BacklogData,
    Epic,
    Feature,
    GeneratedTestSuite,
    TestCase,
    TestStep,
    UserStory,
)
from app.infrastructure.store.rows import backlog_row_to_dict, obs_event_row_to_dict, safe_json_load
from app.infrastructure.store.schema import SCHEMA_SQL
from app.core.config import AUDIT_SIGNING_SECRET

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "agentflow.db"


class Store:
    def __init__(self, db_path: Path = _DB_PATH):
        self.db_path = db_path
        self._lock = threading.Lock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as conn:
            conn.executescript(SCHEMA_SQL)
            self._ensure_migrations(conn)
            conn.commit()

    def _ensure_migrations(self, conn: sqlite3.Connection) -> None:
        columns = conn.execute("PRAGMA table_info(backlog_items)").fetchall()
        names = {row[1] for row in columns}
        if "target_url" not in names:
            conn.execute("ALTER TABLE backlog_items ADD COLUMN target_url TEXT")

        scraper_columns = conn.execute("PRAGMA table_info(scraper_pages)").fetchall()
        scraper_names = {row[1] for row in scraper_columns}
        if scraper_columns and "page_title" not in scraper_names:
            conn.execute("ALTER TABLE scraper_pages ADD COLUMN page_title TEXT")
        if scraper_columns and "text_excerpt" not in scraper_names:
            conn.execute("ALTER TABLE scraper_pages ADD COLUMN text_excerpt TEXT")

        execution_columns = conn.execute("PRAGMA table_info(execution_runs)").fetchall()
        execution_names = {row[1] for row in execution_columns}
        if execution_columns and "attempt_count" not in execution_names:
            conn.execute("ALTER TABLE execution_runs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
        if execution_columns and "max_attempts" not in execution_names:
            conn.execute("ALTER TABLE execution_runs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 1")

        observability_columns = conn.execute("PRAGMA table_info(observability_events)").fetchall()
        observability_names = {row[1] for row in observability_columns}
        if observability_columns and "prev_signature" not in observability_names:
            conn.execute("ALTER TABLE observability_events ADD COLUMN prev_signature TEXT")
        if observability_columns and "event_signature" not in observability_names:
            conn.execute("ALTER TABLE observability_events ADD COLUMN event_signature TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS operator_security_events (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id              TEXT NOT NULL UNIQUE,
                source                TEXT NOT NULL,
                stage                 TEXT NOT NULL,
                status                TEXT NOT NULL,
                state                 TEXT NOT NULL DEFAULT 'open',
                acked_by              TEXT,
                acked_at              TEXT,
                resolved_by           TEXT,
                resolved_at           TEXT,
                resolution_note       TEXT,
                last_updated_at       TEXT DEFAULT (datetime('now')),
                reason                TEXT,
                failures_recent       INTEGER,
                lockout_until         TEXT,
                metadata_json         TEXT,
                created_at            TEXT DEFAULT (datetime('now'))
            )
            """
        )
        operator_security_columns = conn.execute("PRAGMA table_info(operator_security_events)").fetchall()
        operator_security_names = {row[1] for row in operator_security_columns}
        if operator_security_columns and "state" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN state TEXT NOT NULL DEFAULT 'open'")
        if operator_security_columns and "acked_by" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN acked_by TEXT")
        if operator_security_columns and "acked_at" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN acked_at TEXT")
        if operator_security_columns and "resolved_by" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN resolved_by TEXT")
        if operator_security_columns and "resolved_at" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN resolved_at TEXT")
        if operator_security_columns and "resolution_note" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN resolution_note TEXT")
        if operator_security_columns and "last_updated_at" not in operator_security_names:
            conn.execute("ALTER TABLE operator_security_events ADD COLUMN last_updated_at TEXT")
        conn.execute(
            """
            UPDATE operator_security_events
            SET state = 'open'
            WHERE state IS NULL OR trim(state) = ''
            """
        )
        conn.execute(
            """
            UPDATE operator_security_events
            SET last_updated_at = datetime('now')
            WHERE last_updated_at IS NULL OR trim(last_updated_at) = ''
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_operator_security_events_created
            ON operator_security_events(created_at DESC, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_operator_security_events_stage
            ON operator_security_events(stage, created_at DESC, id DESC)
            """
        )

        # Ensure normalized evidence table exists for phase 10.5+.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS execution_evidence (
                id                    INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_run_id      TEXT NOT NULL,
                script_path           TEXT,
                step_index            INTEGER,
                status                TEXT,
                duration_ms           INTEGER,
                started_at            TEXT,
                finished_at           TEXT,
                error_code            TEXT,
                error_message         TEXT,
                stack_trace           TEXT,
                screenshot_path       TEXT,
                trace_path            TEXT,
                video_path            TEXT,
                metadata_json         TEXT,
                created_at            TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_execution_evidence_run
            ON execution_evidence(execution_run_id, step_index ASC, id ASC)
            """
        )

        # Ensure Agent5 persistence tables exist for A5.2.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent5_runs (
                id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent5_run_id              TEXT NOT NULL UNIQUE,
                source_agent4_run_id       TEXT NOT NULL,
                source_execution_run_id     TEXT,
                backlog_item_id            TEXT,
                trace_id                   TEXT NOT NULL,
                state                      TEXT NOT NULL,
                stage                      TEXT NOT NULL,
                request_json               TEXT,
                execution_summary_json     TEXT,
                step_evidence_refs_json    TEXT,
                stage7_analysis_json       TEXT,
                gate7_decision_json        TEXT,
                stage8_writeback_json      TEXT,
                gate8_decision_json        TEXT,
                last_error_code            TEXT,
                last_error_message         TEXT,
                created_at                 TEXT DEFAULT (datetime('now')),
                updated_at                 TEXT DEFAULT (datetime('now')),
                completed_at               TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent5_artifacts (
                id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent5_run_id              TEXT NOT NULL,
                artifact_version           INTEGER NOT NULL,
                artifact_type              TEXT NOT NULL,
                artifact_json              TEXT NOT NULL,
                created_at                 TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS agent5_timeline (
                id                         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent5_run_id              TEXT NOT NULL,
                stage                      TEXT NOT NULL,
                action                     TEXT NOT NULL,
                actor                      TEXT NOT NULL,
                metadata_json              TEXT,
                created_at                 TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent5_runs_agent4
            ON agent5_runs(source_agent4_run_id, updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent5_runs_execution
            ON agent5_runs(source_execution_run_id, updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent5_runs_state
            ON agent5_runs(state, updated_at DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent5_artifacts_run
            ON agent5_artifacts(agent5_run_id, artifact_version DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_agent5_timeline_run
            ON agent5_timeline(agent5_run_id, created_at DESC, id DESC)
            """
        )

        self._ensure_business_id_columns(conn)
        self._ensure_retry_governance_tables(conn)
        self._ensure_active_artifact_revisions(conn)
        self._backfill_business_ids(conn)

    def _ensure_business_id_columns(self, conn: sqlite3.Connection) -> None:
        for table in (
            "agent1_runs",
            "agent2_runs",
            "agent3_runs",
            "agent4_runs",
            "execution_runs",
            "agent5_runs",
            "agent1_artifacts",
            "agent2_artifacts",
            "agent3_artifacts",
            "agent4_artifacts",
            "agent5_artifacts",
            "execution_evidence",
        ):
            columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
            names = {row[1] for row in columns}
            if "business_id" not in names:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN business_id TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS business_id_sequences (
                namespace      TEXT PRIMARY KEY,
                next_value     INTEGER NOT NULL
            )
            """
        )

        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent1_runs_business_id ON agent1_runs(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent2_runs_business_id ON agent2_runs(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent3_runs_business_id ON agent3_runs(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent4_runs_business_id ON agent4_runs(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_runs_business_id ON execution_runs(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent5_runs_business_id ON agent5_runs(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent1_artifacts_business_id ON agent1_artifacts(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent2_artifacts_business_id ON agent2_artifacts(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent3_artifacts_business_id ON agent3_artifacts(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent4_artifacts_business_id ON agent4_artifacts(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_agent5_artifacts_business_id ON agent5_artifacts(business_id)")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_execution_evidence_business_id ON execution_evidence(business_id)")

    def _ensure_retry_governance_tables(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS retry_governance_requests (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id         TEXT NOT NULL UNIQUE,
                run_scope          TEXT NOT NULL,
                run_id             TEXT NOT NULL,
                requested_by       TEXT NOT NULL,
                reason_code        TEXT,
                reason_text        TEXT,
                status             TEXT NOT NULL,
                assigned_reviewer_id TEXT,
                assignment_mode    TEXT,
                assigned_by        TEXT,
                assignment_reason  TEXT,
                assigned_at        TEXT,
                escalation_status  TEXT,
                reviewer_id        TEXT,
                reviewer_decision  TEXT,
                reviewer_comment   TEXT,
                reviewed_at        TEXT,
                created_at         TEXT DEFAULT (datetime('now')),
                updated_at         TEXT DEFAULT (datetime('now'))
            )
            """
        )

        columns = conn.execute("PRAGMA table_info(retry_governance_requests)").fetchall()
        names = {row[1] for row in columns}
        if "assigned_reviewer_id" not in names:
            conn.execute("ALTER TABLE retry_governance_requests ADD COLUMN assigned_reviewer_id TEXT")
        if "assignment_mode" not in names:
            conn.execute("ALTER TABLE retry_governance_requests ADD COLUMN assignment_mode TEXT")
        if "assigned_by" not in names:
            conn.execute("ALTER TABLE retry_governance_requests ADD COLUMN assigned_by TEXT")
        if "assignment_reason" not in names:
            conn.execute("ALTER TABLE retry_governance_requests ADD COLUMN assignment_reason TEXT")
        if "assigned_at" not in names:
            conn.execute("ALTER TABLE retry_governance_requests ADD COLUMN assigned_at TEXT")
        if "escalation_status" not in names:
            conn.execute("ALTER TABLE retry_governance_requests ADD COLUMN escalation_status TEXT")

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS retry_governance_audit_events (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                request_id         TEXT NOT NULL,
                action             TEXT NOT NULL,
                actor              TEXT NOT NULL,
                metadata_json      TEXT,
                created_at         TEXT DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_retry_governance_scope_run
            ON retry_governance_requests(run_scope, run_id, created_at DESC, id DESC)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_retry_governance_audit_request
            ON retry_governance_audit_events(request_id, created_at DESC, id DESC)
            """
        )

    def _ensure_active_artifact_revisions(self, conn: sqlite3.Connection) -> None:
        targets = [
            ("agent1_artifacts", "run_id"),
            ("agent2_artifacts", "run_id"),
            ("agent3_artifacts", "run_id"),
            ("agent4_artifacts", "run_id"),
            ("agent5_artifacts", "agent5_run_id"),
        ]

        for table, run_column in targets:
            columns = conn.execute(f"PRAGMA table_info({table})").fetchall()
            if not columns:
                continue
            names = {row[1] for row in columns}
            if "is_active" not in names:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN is_active INTEGER NOT NULL DEFAULT 0")

            conn.execute(
                f"CREATE INDEX IF NOT EXISTS idx_{table}_active ON {table}({run_column}, is_active DESC, artifact_version DESC, id DESC)"
            )

            run_ids = conn.execute(f"SELECT DISTINCT {run_column} AS run_id FROM {table}").fetchall()
            for row in run_ids:
                run_id = str(row["run_id"] or "")
                if not run_id:
                    continue
                active_row = conn.execute(
                    f"SELECT id FROM {table} WHERE {run_column} = ? AND is_active = 1 LIMIT 1",
                    (run_id,),
                ).fetchone()
                if active_row is not None:
                    continue
                latest = conn.execute(
                    f"""
                    SELECT id
                    FROM {table}
                    WHERE {run_column} = ?
                    ORDER BY artifact_version DESC, id DESC
                    LIMIT 1
                    """,
                    (run_id,),
                ).fetchone()
                if latest is None:
                    continue
                conn.execute(
                    f"UPDATE {table} SET is_active = CASE WHEN id = ? THEN 1 ELSE 0 END WHERE {run_column} = ?",
                    (int(latest["id"]), run_id),
                )

    @staticmethod
    def _set_active_artifact_revision(
        conn: sqlite3.Connection,
        *,
        table: str,
        run_column: str,
        run_id: str,
        artifact_version: int,
    ) -> bool:
        target = conn.execute(
            f"SELECT id FROM {table} WHERE {run_column} = ? AND artifact_version = ? ORDER BY id DESC LIMIT 1",
            (run_id, artifact_version),
        ).fetchone()
        if target is None:
            return False

        conn.execute(
            f"UPDATE {table} SET is_active = CASE WHEN id = ? THEN 1 ELSE 0 END WHERE {run_column} = ?",
            (int(target["id"]), run_id),
        )
        return True

    def _backfill_business_ids(self, conn: sqlite3.Connection) -> None:
        self._backfill_table_business_ids(conn, table="agent1_runs", key_column="run_id", namespace="agent1_run", prefix="AG1-RUN-")
        self._backfill_table_business_ids(conn, table="agent2_runs", key_column="run_id", namespace="agent2_run", prefix="AG2-RUN-")
        self._backfill_table_business_ids(conn, table="agent3_runs", key_column="run_id", namespace="agent3_run", prefix="AG3-RUN-")
        self._backfill_table_business_ids(conn, table="agent4_runs", key_column="run_id", namespace="agent4_run", prefix="AG4-RUN-")
        self._backfill_table_business_ids(conn, table="execution_runs", key_column="execution_run_id", namespace="execution_run", prefix="EXE-RUN-")
        self._backfill_table_business_ids(conn, table="agent5_runs", key_column="agent5_run_id", namespace="agent5_run", prefix="AG5-RUN-")
        self._backfill_table_business_ids(conn, table="agent1_artifacts", key_column="id", namespace="agent1_test_case", prefix="TC-")
        self._backfill_table_business_ids(conn, table="agent2_artifacts", key_column="id", namespace="agent2_step", prefix="STEP-")
        self._backfill_table_business_ids(conn, table="agent3_artifacts", key_column="id", namespace="agent3_reasoning", prefix="RZN-")
        self._backfill_table_business_ids(conn, table="agent4_artifacts", key_column="id", namespace="agent4_script", prefix="SCR-")
        self._backfill_table_business_ids(conn, table="agent5_artifacts", key_column="id", namespace="agent5_artifact", prefix="AG5-ART-")
        self._backfill_table_business_ids(conn, table="execution_evidence", key_column="id", namespace="execution_evidence", prefix="EVD-")

    def _next_business_id(self, conn: sqlite3.Connection, *, namespace: str, prefix: str) -> str:
        row = conn.execute(
            "SELECT next_value FROM business_id_sequences WHERE namespace = ?",
            (namespace,),
        ).fetchone()
        next_value = int(row["next_value"] if row else 1)
        conn.execute(
            "INSERT INTO business_id_sequences(namespace, next_value) VALUES (?, ?) ON CONFLICT(namespace) DO UPDATE SET next_value = excluded.next_value",
            (namespace, next_value + 1),
        )
        return f"{prefix}{next_value:04d}"

    def _backfill_table_business_ids(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        key_column: str,
        namespace: str,
        prefix: str,
    ) -> None:
        rows = conn.execute(
            f"SELECT {key_column} FROM {table} WHERE business_id IS NULL ORDER BY created_at ASC, {key_column} ASC"
        ).fetchall()
        for row in rows:
            key_value = str(row[key_column] or "")
            if not key_value:
                continue
            business_id = self._next_business_id(conn, namespace=namespace, prefix=prefix)
            conn.execute(
                f"UPDATE {table} SET business_id = ? WHERE {key_column} = ?",
                (business_id, key_value),
            )

    def _get_or_create_business_id(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        key_column: str,
        key_value: str,
        namespace: str,
        prefix: str,
    ) -> str:
        row = conn.execute(
            f"SELECT business_id FROM {table} WHERE {key_column} = ?",
            (key_value,),
        ).fetchone()
        existing = str(row["business_id"] or "") if row is not None else ""
        if existing:
            return existing
        return self._next_business_id(conn, namespace=namespace, prefix=prefix)

    def _assign_row_business_id(
        self,
        conn: sqlite3.Connection,
        *,
        table: str,
        key_column: str,
        key_value: int,
        namespace: str,
        prefix: str,
    ) -> str:
        business_id = self._next_business_id(conn, namespace=namespace, prefix=prefix)
        conn.execute(
            f"UPDATE {table} SET business_id = ? WHERE {key_column} = ?",
            (business_id, int(key_value)),
        )
        return business_id

    def _replace_execution_evidence(self, conn: sqlite3.Connection, execution_run_id: str, items: list[dict]) -> None:
        conn.execute("DELETE FROM execution_evidence WHERE execution_run_id = ?", (execution_run_id,))
        for item in items:
            if not isinstance(item, dict):
                continue
            evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
            cursor = conn.execute(
                """
                INSERT INTO execution_evidence(
                    execution_run_id, script_path, step_index, status,
                    duration_ms, started_at, finished_at,
                    error_code, error_message, stack_trace,
                    screenshot_path, trace_path, video_path, metadata_json, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_run_id,
                    str(item.get("script_path") or ""),
                    int(item.get("step_index") or 0),
                    str(item.get("status") or ""),
                    int(item.get("duration_ms") or 0),
                    str(item.get("started_at") or "") or None,
                    str(item.get("finished_at") or "") or None,
                    str(item.get("error_code") or "") or None,
                    str(item.get("error_message") or "") or None,
                    str(item.get("stack_trace") or "") or None,
                    str(evidence.get("screenshot_path") or "") or None,
                    str(evidence.get("trace_path") or "") or None,
                    str(evidence.get("video_path") or "") or None,
                    json.dumps(item.get("metadata") if isinstance(item.get("metadata"), dict) else {}),
                    None,
                ),
            )
            self._assign_row_business_id(
                conn,
                table="execution_evidence",
                key_column="id",
                key_value=int(cursor.lastrowid),
                namespace="execution_evidence",
                prefix="EVD-",
            )

    def get_execution_evidence(self, execution_run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM execution_evidence
                WHERE execution_run_id = ?
                ORDER BY step_index ASC, id ASC
                """,
                (execution_run_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "business_id": row["business_id"],
                    "execution_run_id": row["execution_run_id"],
                    "script_path": row["script_path"],
                    "step_index": row["step_index"],
                    "status": row["status"],
                    "duration_ms": row["duration_ms"],
                    "started_at": row["started_at"],
                    "finished_at": row["finished_at"],
                    "error_code": row["error_code"],
                    "error_message": row["error_message"],
                    "stack_trace": row["stack_trace"],
                    "evidence": {
                        "screenshot_path": row["screenshot_path"],
                        "trace_path": row["trace_path"],
                        "video_path": row["video_path"],
                    },
                    "metadata": safe_json_load(row["metadata_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def resolve_business_id(self, business_id: str) -> dict | None:
        needle = str(business_id or "").strip()
        if not needle:
            return None

        checks: list[tuple[str, str, str, str]] = [
            ("agent1_runs", "run", "agent1", "run_id"),
            ("agent2_runs", "run", "agent2", "run_id"),
            ("agent3_runs", "run", "agent3", "run_id"),
            ("agent4_runs", "run", "agent4", "run_id"),
            ("execution_runs", "run", "execution", "execution_run_id"),
            ("agent5_runs", "run", "agent5", "agent5_run_id"),
            ("agent1_artifacts", "artifact", "agent1", "id"),
            ("agent2_artifacts", "artifact", "agent2", "id"),
            ("agent3_artifacts", "artifact", "agent3", "id"),
            ("agent4_artifacts", "artifact", "agent4", "id"),
            ("agent5_artifacts", "artifact", "agent5", "id"),
            ("execution_evidence", "evidence", "execution", "id"),
        ]

        with self._conn() as conn:
            for table, entity_type, scope, key_column in checks:
                row = conn.execute(
                    f"SELECT * FROM {table} WHERE business_id = ? LIMIT 1",
                    (needle,),
                ).fetchone()
                if row is None:
                    continue
                payload = {k: row[k] for k in row.keys()}
                return {
                    "business_id": needle,
                    "entity_type": entity_type,
                    "scope": scope,
                    "table": table,
                    "key_column": key_column,
                    "key_value": payload.get(key_column),
                    "record": payload,
                }
        return None

    def get_business_id_migration_status(self) -> dict:
        table_specs: list[tuple[str, str, str]] = [
            ("agent1_runs", "run", "run_id"),
            ("agent2_runs", "run", "run_id"),
            ("agent3_runs", "run", "run_id"),
            ("agent4_runs", "run", "run_id"),
            ("execution_runs", "run", "execution_run_id"),
            ("agent5_runs", "run", "agent5_run_id"),
            ("agent1_artifacts", "artifact", "id"),
            ("agent2_artifacts", "artifact", "id"),
            ("agent3_artifacts", "artifact", "id"),
            ("agent4_artifacts", "artifact", "id"),
            ("agent5_artifacts", "artifact", "id"),
            ("execution_evidence", "evidence", "id"),
        ]

        link_specs: list[tuple[str, str, str, str, str]] = [
            ("agent2_runs_to_agent1_runs", "agent2_runs", "source_agent1_run_id", "agent1_runs", "run_id"),
            ("agent2_artifacts_to_agent2_runs", "agent2_artifacts", "run_id", "agent2_runs", "run_id"),
            ("agent3_runs_to_agent2_runs", "agent3_runs", "source_agent2_run_id", "agent2_runs", "run_id"),
            ("agent3_artifacts_to_agent3_runs", "agent3_artifacts", "run_id", "agent3_runs", "run_id"),
            ("agent4_runs_to_agent3_runs", "agent4_runs", "source_agent3_run_id", "agent3_runs", "run_id"),
            ("agent4_artifacts_to_agent4_runs", "agent4_artifacts", "run_id", "agent4_runs", "run_id"),
            ("execution_runs_to_agent4_runs", "execution_runs", "source_agent4_run_id", "agent4_runs", "run_id"),
            ("execution_evidence_to_execution_runs", "execution_evidence", "execution_run_id", "execution_runs", "execution_run_id"),
            ("agent5_runs_to_agent4_runs", "agent5_runs", "source_agent4_run_id", "agent4_runs", "run_id"),
            ("agent5_runs_to_execution_runs", "agent5_runs", "source_execution_run_id", "execution_runs", "execution_run_id"),
            ("agent5_artifacts_to_agent5_runs", "agent5_artifacts", "agent5_run_id", "agent5_runs", "agent5_run_id"),
        ]

        with self._conn() as conn:
            table_status: list[dict] = []
            total_rows = 0
            total_missing = 0
            total_duplicate_groups = 0

            for table, entity_type, key_column in table_specs:
                total = int(conn.execute(f"SELECT COUNT(*) AS cnt FROM {table}").fetchone()["cnt"])
                with_business_id = int(
                    conn.execute(
                        f"SELECT COUNT(*) AS cnt FROM {table} WHERE business_id IS NOT NULL AND TRIM(business_id) != ''"
                    ).fetchone()["cnt"]
                )
                missing = max(total - with_business_id, 0)
                duplicate_groups = int(
                    conn.execute(
                        f"""
                        SELECT COUNT(*) AS cnt
                        FROM (
                            SELECT business_id
                            FROM {table}
                            WHERE business_id IS NOT NULL AND TRIM(business_id) != ''
                            GROUP BY business_id
                            HAVING COUNT(*) > 1
                        ) dup
                        """
                    ).fetchone()["cnt"]
                )
                sample_rows = conn.execute(
                    f"""
                    SELECT {key_column}
                    FROM {table}
                    WHERE business_id IS NULL OR TRIM(business_id) = ''
                    ORDER BY created_at ASC, {key_column} ASC
                    LIMIT 3
                    """
                ).fetchall()
                sample_missing_keys = [str(r[key_column]) for r in sample_rows if r[key_column] is not None]

                table_status.append(
                    {
                        "table": table,
                        "entity_type": entity_type,
                        "key_column": key_column,
                        "total_rows": total,
                        "rows_with_business_id": with_business_id,
                        "rows_missing_business_id": missing,
                        "duplicate_business_id_groups": duplicate_groups,
                        "sample_missing_keys": sample_missing_keys,
                    }
                )

                total_rows += total
                total_missing += missing
                total_duplicate_groups += duplicate_groups

            link_status: list[dict] = []
            total_orphan_links = 0
            for name, from_table, from_column, to_table, to_column in link_specs:
                orphan_count = int(
                    conn.execute(
                        f"""
                        SELECT COUNT(*) AS cnt
                        FROM {from_table} src
                        LEFT JOIN {to_table} dst ON src.{from_column} = dst.{to_column}
                        WHERE src.{from_column} IS NOT NULL
                          AND TRIM(CAST(src.{from_column} AS TEXT)) != ''
                          AND dst.{to_column} IS NULL
                        """
                    ).fetchone()["cnt"]
                )
                total_orphan_links += orphan_count
                link_status.append(
                    {
                        "name": name,
                        "from_table": from_table,
                        "from_column": from_column,
                        "to_table": to_table,
                        "to_column": to_column,
                        "orphan_count": orphan_count,
                        "status": "ok" if orphan_count == 0 else "orphaned",
                    }
                )

            db_file_exists = self.db_path.exists()
            summary_ok = total_missing == 0 and total_duplicate_groups == 0 and total_orphan_links == 0

            return {
                "generated_at": conn.execute("SELECT datetime('now') AS ts").fetchone()["ts"],
                "summary": {
                    "total_rows_checked": total_rows,
                    "rows_missing_business_id": total_missing,
                    "duplicate_business_id_groups": total_duplicate_groups,
                    "orphan_link_count": total_orphan_links,
                    "status": "ok" if summary_ok else "attention_required",
                },
                "tables": table_status,
                "links": link_status,
                "rollback": {
                    "strategy": "restore sqlite db file from backup snapshot",
                    "database_path": str(self.db_path),
                    "rollback_ready": db_file_exists,
                },
            }

    def repair_business_id_links(self, *, actor: str = "operator") -> dict:
        # Only perform safe automatic repairs on child tables and optional foreign references.
        delete_specs: list[tuple[str, str, str, str, str]] = [
            ("agent2_artifacts_to_agent2_runs", "agent2_artifacts", "run_id", "agent2_runs", "run_id"),
            ("agent3_artifacts_to_agent3_runs", "agent3_artifacts", "run_id", "agent3_runs", "run_id"),
            ("agent4_artifacts_to_agent4_runs", "agent4_artifacts", "run_id", "agent4_runs", "run_id"),
            ("execution_evidence_to_execution_runs", "execution_evidence", "execution_run_id", "execution_runs", "execution_run_id"),
            ("agent5_artifacts_to_agent5_runs", "agent5_artifacts", "agent5_run_id", "agent5_runs", "agent5_run_id"),
        ]

        with self._lock, self._conn() as conn:
            deleted: list[dict] = []
            total_deleted = 0

            for name, from_table, from_column, to_table, to_column in delete_specs:
                orphan_count = int(
                    conn.execute(
                        f"""
                        SELECT COUNT(*) AS cnt
                        FROM {from_table} src
                        LEFT JOIN {to_table} dst ON src.{from_column} = dst.{to_column}
                        WHERE src.{from_column} IS NOT NULL
                          AND TRIM(CAST(src.{from_column} AS TEXT)) != ''
                          AND dst.{to_column} IS NULL
                        """
                    ).fetchone()["cnt"]
                )
                if orphan_count > 0:
                    conn.execute(
                        f"""
                        DELETE FROM {from_table}
                        WHERE {from_column} IS NOT NULL
                          AND TRIM(CAST({from_column} AS TEXT)) != ''
                          AND {from_column} NOT IN (
                              SELECT {to_column}
                              FROM {to_table}
                          )
                        """
                    )
                deleted.append(
                    {
                        "name": name,
                        "strategy": "delete_orphan_children",
                        "repaired_count": orphan_count,
                    }
                )
                total_deleted += orphan_count

            nullified_count = int(
                conn.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM agent5_runs src
                    LEFT JOIN execution_runs dst ON src.source_execution_run_id = dst.execution_run_id
                    WHERE src.source_execution_run_id IS NOT NULL
                      AND TRIM(src.source_execution_run_id) != ''
                      AND dst.execution_run_id IS NULL
                    """
                ).fetchone()["cnt"]
            )
            if nullified_count > 0:
                conn.execute(
                    """
                    UPDATE agent5_runs
                    SET source_execution_run_id = NULL,
                        updated_at = datetime('now')
                    WHERE source_execution_run_id IS NOT NULL
                      AND TRIM(source_execution_run_id) != ''
                      AND source_execution_run_id NOT IN (
                          SELECT execution_run_id
                          FROM execution_runs
                      )
                    """
                )

            repaired_at = conn.execute("SELECT datetime('now') AS ts").fetchone()["ts"]
            conn.commit()

        status = self.get_business_id_migration_status()
        return {
            "actor": actor,
            "repaired_at": repaired_at,
            "total_repaired": total_deleted + nullified_count,
            "deleted_orphan_rows": deleted,
            "nullified_optional_links": [
                {
                    "name": "agent5_runs_to_execution_runs",
                    "strategy": "nullify_missing_optional_reference",
                    "repaired_count": nullified_count,
                }
            ],
            "status_after": status,
        }

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save_suite(self, suite: GeneratedTestSuite) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO test_suites(story_id, story_title, feature_title, epic_title, model_used, test_cases_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(story_id) DO UPDATE SET
                    story_title=excluded.story_title,
                    feature_title=excluded.feature_title,
                    epic_title=excluded.epic_title,
                    model_used=excluded.model_used,
                    test_cases_json=excluded.test_cases_json,
                    created_at=datetime('now')
                """,
                (
                    suite.story_id,
                    suite.story_title,
                    suite.feature_title,
                    suite.epic_title,
                    suite.model_used,
                    json.dumps([tc.model_dump() for tc in suite.test_cases]),
                ),
            )
            conn.commit()

    def get_suite(self, story_id: str) -> Optional[GeneratedTestSuite]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM test_suites WHERE story_id = ?", (story_id,)).fetchone()
            if row is None:
                return None
            raw_cases = safe_json_load(row["test_cases_json"], [])
            test_cases = []
            for tc in raw_cases:
                steps = [TestStep(**s) for s in tc.get("steps", [])]
                test_cases.append(
                    TestCase(
                        id=tc.get("id", ""),
                        title=tc.get("title", ""),
                        criterion_id=tc.get("criterion_id", ""),
                        story_id=tc.get("story_id", story_id),
                        preconditions=tc.get("preconditions", []),
                        steps=steps,
                        expected_result=tc.get("expected_result", ""),
                        test_type=tc.get("test_type", "functional"),
                    )
                )
            return GeneratedTestSuite(
                story_id=row["story_id"],
                story_title=row["story_title"],
                feature_title=row["feature_title"],
                epic_title=row["epic_title"],
                model_used=row["model_used"],
                test_cases=test_cases,
            )

    def upsert_backlog_items(
        self,
        *,
        backlog: BacklogData,
        source_type: str,
        source_ref: str | None = None,
        target_url: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            for epic in backlog.epics:
                for feature in epic.features:
                    for story in feature.user_stories:
                        acceptance = [ac.text for ac in story.acceptance_criteria]
                        conn.execute(
                            """
                            INSERT INTO backlog_items(
                                backlog_item_id, story_title, story_description, acceptance_json,
                                target_url, epic_id, epic_title, feature_id, feature_title, source_type, source_ref
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(backlog_item_id) DO UPDATE SET
                                story_title=excluded.story_title,
                                story_description=excluded.story_description,
                                acceptance_json=excluded.acceptance_json,
                                target_url=COALESCE(excluded.target_url, backlog_items.target_url),
                                epic_id=excluded.epic_id,
                                epic_title=excluded.epic_title,
                                feature_id=excluded.feature_id,
                                feature_title=excluded.feature_title,
                                source_type=excluded.source_type,
                                source_ref=excluded.source_ref,
                                updated_at=datetime('now')
                            """,
                            (
                                story.id,
                                story.title,
                                story.description,
                                json.dumps(acceptance),
                                target_url,
                                epic.id,
                                epic.title,
                                feature.id,
                                feature.title,
                                source_type,
                                source_ref,
                            ),
                        )
            conn.commit()

    def get_backlog_items(self, *, source_type: str | None = None, limit: int = 500) -> list[dict]:
        with self._conn() as conn:
            if source_type:
                rows = conn.execute(
                    """
                    SELECT * FROM backlog_items
                    WHERE source_type = ?
                    ORDER BY updated_at DESC
                    LIMIT ?
                    """,
                    (source_type, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM backlog_items ORDER BY updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [backlog_row_to_dict(r) for r in rows]

    def get_backlog_item(self, backlog_item_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM backlog_items WHERE backlog_item_id = ?",
                (backlog_item_id,),
            ).fetchone()
            return backlog_row_to_dict(row) if row else None

    def get_backlog_data_by_source(self, source_type: str) -> BacklogData:
        items = self.get_backlog_items(source_type=source_type, limit=5000)
        epic_map: dict[str, dict] = {}
        for item in items:
            epic_id = item.get("epic_id") or "epic_unknown"
            feature_id = item.get("feature_id") or "feature_unknown"

            if epic_id not in epic_map:
                epic_map[epic_id] = {
                    "id": epic_id,
                    "title": item.get("epic_title") or "Untitled Epic",
                    "description": "",
                    "features": {},
                }

            epic_entry = epic_map[epic_id]
            if feature_id not in epic_entry["features"]:
                epic_entry["features"][feature_id] = {
                    "id": feature_id,
                    "title": item.get("feature_title") or "Untitled Feature",
                    "description": "",
                    "stories": [],
                }

            story_id = item["backlog_item_id"]
            criteria = [
                AcceptanceCriterion(id=f"{story_id}_ac_{i+1}", text=text, original_text=text)
                for i, text in enumerate(item.get("acceptance_criteria") or [])
            ]
            epic_entry["features"][feature_id]["stories"].append(
                UserStory(
                    id=story_id,
                    title=item.get("story_title") or story_id,
                    description=item.get("story_description") or "",
                    acceptance_criteria=criteria,
                )
            )

        epics: list[Epic] = []
        for epic in epic_map.values():
            features = [
                Feature(
                    id=f["id"],
                    title=f["title"],
                    description=f["description"],
                    user_stories=f["stories"],
                )
                for f in epic["features"].values()
            ]
            epics.append(Epic(id=epic["id"], title=epic["title"], description=epic["description"], features=features))

        backlog = BacklogData(epics=epics)
        backlog.compute_totals()
        return backlog

    def upsert_agent1_run(
        self,
        *,
        run_id: str,
        backlog_item_id: str,
        trace_id: str,
        state: str,
        source_type: str | None,
        source_ref: str | None,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            business_id = self._get_or_create_business_id(
                conn,
                table="agent1_runs",
                key_column="run_id",
                key_value=run_id,
                namespace="agent1_run",
                prefix="AG1-RUN-",
            )
            conn.execute(
                """
                INSERT INTO agent1_runs(
                    run_id, backlog_item_id, trace_id, state, source_type, source_ref,
                    last_error_code, last_error_message, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    backlog_item_id=excluded.backlog_item_id,
                    trace_id=excluded.trace_id,
                    state=excluded.state,
                    source_type=excluded.source_type,
                    source_ref=excluded.source_ref,
                    last_error_code=excluded.last_error_code,
                    last_error_message=excluded.last_error_message,
                    business_id=COALESCE(agent1_runs.business_id, excluded.business_id),
                    updated_at=datetime('now')
                """,
                (
                    run_id,
                    backlog_item_id,
                    trace_id,
                    state,
                    source_type,
                    source_ref,
                    last_error_code,
                    last_error_message,
                    business_id,
                ),
            )
            conn.commit()

    def add_agent1_artifact(
        self,
        *,
        run_id: str,
        backlog_item_id: str,
        artifact_version: int,
        artifact: dict,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE agent1_artifacts SET is_active = 0 WHERE run_id = ?",
                (run_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO agent1_artifacts(run_id, backlog_item_id, artifact_version, artifact_json, is_active, business_id)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (run_id, backlog_item_id, artifact_version, json.dumps(artifact), None),
            )
            self._assign_row_business_id(
                conn,
                table="agent1_artifacts",
                key_column="id",
                key_value=int(cursor.lastrowid),
                namespace="agent1_test_case",
                prefix="TC-",
            )
            conn.commit()

    def add_agent1_review(
        self,
        *,
        run_id: str,
        stage: str,
        decision: str,
        reason_code: str | None,
        reviewer_id: str,
        edited_payload: dict | None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent1_reviews(run_id, stage, decision, reason_code, reviewer_id, edited_payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, stage, decision, reason_code, reviewer_id, json.dumps(edited_payload) if edited_payload else None),
            )
            conn.commit()

    def add_agent1_handoff(
        self,
        *,
        run_id: str,
        message_id: str,
        from_agent: str,
        to_agent: str,
        task_type: str,
        contract_version: str,
        payload: dict,
        delivery_status: str,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent1_handoffs(
                    run_id, message_id, from_agent, to_agent, task_type,
                    contract_version, payload_json, delivery_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (run_id, message_id, from_agent, to_agent, task_type, contract_version, json.dumps(payload), delivery_status),
            )
            conn.commit()

    def add_agent1_audit_event(
        self,
        *,
        run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent1_audit_events(run_id, stage, action, actor, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, stage, action, actor, json.dumps(metadata) if metadata else None),
            )
            conn.commit()

    def get_agent1_run(self, run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM agent1_runs WHERE run_id = ?", (run_id,)).fetchone()
            return dict(row) if row else None

    def list_agent1_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM agent1_runs
                WHERE backlog_item_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (backlog_item_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_agent1_artifacts(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, business_id, run_id, backlog_item_id, artifact_version, artifact_json, is_active, created_at
                FROM agent1_artifacts
                WHERE run_id = ?
                ORDER BY is_active DESC, artifact_version DESC, id DESC
                """,
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "business_id": r["business_id"],
                    "run_id": r["run_id"],
                    "backlog_item_id": r["backlog_item_id"],
                    "artifact_version": r["artifact_version"],
                    "is_active": bool(r["is_active"]),
                    "artifact": safe_json_load(r["artifact_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent1_latest_artifact(self, run_id: str) -> dict | None:
        artifacts = self.get_agent1_artifacts(run_id)
        return artifacts[0] if artifacts else None

    def get_agent1_next_artifact_version(self, run_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(artifact_version), 0) AS max_version FROM agent1_artifacts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return int((row["max_version"] if row is not None else 0) or 0) + 1

    def set_agent1_active_artifact_version(self, *, run_id: str, artifact_version: int) -> dict | None:
        with self._lock, self._conn() as conn:
            changed = self._set_active_artifact_revision(
                conn,
                table="agent1_artifacts",
                run_column="run_id",
                run_id=run_id,
                artifact_version=artifact_version,
            )
            if not changed:
                return None
            conn.commit()
        return self.get_agent1_latest_artifact(run_id)

    def get_agent1_reviews(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent1_reviews WHERE run_id = ? ORDER BY created_at DESC",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "stage": r["stage"],
                    "decision": r["decision"],
                    "reason_code": r["reason_code"],
                    "reviewer_id": r["reviewer_id"],
                    "edited_payload": safe_json_load(r["edited_payload_json"], None),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent1_handoffs(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent1_handoffs WHERE run_id = ? ORDER BY created_at DESC",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "message_id": r["message_id"],
                    "from_agent": r["from_agent"],
                    "to_agent": r["to_agent"],
                    "task_type": r["task_type"],
                    "contract_version": r["contract_version"],
                    "payload": safe_json_load(r["payload_json"], {}),
                    "delivery_status": r["delivery_status"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent1_audit_events(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent1_audit_events WHERE run_id = ? ORDER BY created_at DESC",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "stage": r["stage"],
                    "action": r["action"],
                    "actor": r["actor"],
                    "metadata": safe_json_load(r["metadata_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def upsert_agent2_inbox(
        self,
        *,
        message_id: str,
        source_agent1_run_id: str,
        trace_id: str,
        contract_version: str,
        task_type: str,
        payload: dict,
        intake_status: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent2_inbox WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if existing:
                return self.get_agent2_inbox(message_id) or {}, False

            conn.execute(
                """
                INSERT INTO agent2_inbox(
                    message_id, source_agent1_run_id, trace_id,
                    contract_version, task_type, payload_json, intake_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    source_agent1_run_id,
                    trace_id,
                    contract_version,
                    task_type,
                    json.dumps(payload),
                    intake_status,
                ),
            )
            conn.commit()
            return self.get_agent2_inbox(message_id) or {}, True

    def get_agent2_inbox(self, message_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent2_inbox WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "message_id": row["message_id"],
                "source_agent1_run_id": row["source_agent1_run_id"],
                "trace_id": row["trace_id"],
                "contract_version": row["contract_version"],
                "task_type": row["task_type"],
                "payload": safe_json_load(row["payload_json"], {}),
                "intake_status": row["intake_status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def create_agent2_run_from_inbox(
        self,
        *,
        run_id: str,
        inbox_message_id: str,
        source_agent1_run_id: str,
        trace_id: str,
        state: str,
        stage: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent2_runs WHERE inbox_message_id = ?",
                (inbox_message_id,),
            ).fetchone()
            if existing:
                return self.get_agent2_run(existing["run_id"]) or {}, False

            business_id = self._get_or_create_business_id(
                conn,
                table="agent2_runs",
                key_column="run_id",
                key_value=run_id,
                namespace="agent2_run",
                prefix="AG2-RUN-",
            )
            conn.execute(
                """
                INSERT INTO agent2_runs(
                    run_id, inbox_message_id, source_agent1_run_id,
                    trace_id, state, stage, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    inbox_message_id,
                    source_agent1_run_id,
                    trace_id,
                    state,
                    stage,
                    business_id,
                ),
            )
            conn.execute(
                "UPDATE agent2_inbox SET intake_status = ?, updated_at = datetime('now') WHERE message_id = ?",
                ("run_created", inbox_message_id),
            )
            conn.commit()
            return self.get_agent2_run(run_id) or {}, True

    def upsert_agent2_run_state(
        self,
        *,
        run_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE agent2_runs
                SET state = ?,
                    stage = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    updated_at = datetime('now')
                WHERE run_id = ?
                """,
                (state, stage, last_error_code, last_error_message, run_id),
            )
            conn.commit()

    def add_agent2_artifact(
        self,
        *,
        run_id: str,
        source_agent1_run_id: str,
        artifact_version: int,
        artifact: dict,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE agent2_artifacts SET is_active = 0 WHERE run_id = ?",
                (run_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO agent2_artifacts(run_id, source_agent1_run_id, artifact_version, artifact_json, is_active, business_id)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (run_id, source_agent1_run_id, artifact_version, json.dumps(artifact), None),
            )
            self._assign_row_business_id(
                conn,
                table="agent2_artifacts",
                key_column="id",
                key_value=int(cursor.lastrowid),
                namespace="agent2_step",
                prefix="STEP-",
            )
            conn.commit()

    def add_agent2_review(
        self,
        *,
        run_id: str,
        stage: str,
        decision: str,
        reason_code: str | None,
        reviewer_id: str,
        edited_payload: dict | None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent2_reviews(run_id, stage, decision, reason_code, reviewer_id, edited_payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (run_id, stage, decision, reason_code, reviewer_id, json.dumps(edited_payload) if edited_payload else None),
            )
            conn.commit()

    def create_agent2_handoff(
        self,
        *,
        run_id: str,
        message_id: str,
        from_agent: str,
        to_agent: str,
        task_type: str,
        contract_version: str,
        payload: dict,
        delivery_status: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent2_handoffs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if existing:
                rows = self.get_agent2_handoffs(run_id)
                return (rows[0] if rows else {}), False

            conn.execute(
                """
                INSERT INTO agent2_handoffs(
                    run_id, message_id, from_agent, to_agent, task_type,
                    contract_version, payload_json, delivery_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    message_id,
                    from_agent,
                    to_agent,
                    task_type,
                    contract_version,
                    json.dumps(payload),
                    delivery_status,
                ),
            )
            conn.commit()
            rows = self.get_agent2_handoffs(run_id)
            return (rows[0] if rows else {}), True

    def get_agent2_artifacts(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, business_id, run_id, source_agent1_run_id, artifact_version, artifact_json, is_active, created_at
                FROM agent2_artifacts
                WHERE run_id = ?
                ORDER BY is_active DESC, artifact_version DESC, id DESC
                """,
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "business_id": r["business_id"],
                    "run_id": r["run_id"],
                    "source_agent1_run_id": r["source_agent1_run_id"],
                    "artifact_version": r["artifact_version"],
                    "is_active": bool(r["is_active"]),
                    "artifact": safe_json_load(r["artifact_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent2_latest_artifact(self, run_id: str) -> dict | None:
        artifacts = self.get_agent2_artifacts(run_id)
        return artifacts[0] if artifacts else None

    def get_agent2_reviews(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent2_reviews WHERE run_id = ? ORDER BY created_at DESC",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "stage": r["stage"],
                    "decision": r["decision"],
                    "reason_code": r["reason_code"],
                    "reviewer_id": r["reviewer_id"],
                    "edited_payload": safe_json_load(r["edited_payload_json"], None),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent2_handoffs(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM agent2_handoffs WHERE run_id = ? ORDER BY created_at DESC",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "message_id": r["message_id"],
                    "from_agent": r["from_agent"],
                    "to_agent": r["to_agent"],
                    "task_type": r["task_type"],
                    "contract_version": r["contract_version"],
                    "payload": safe_json_load(r["payload_json"], {}),
                    "delivery_status": r["delivery_status"],
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent2_next_artifact_version(self, run_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(artifact_version), 0) AS max_version FROM agent2_artifacts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return int((row["max_version"] if row is not None else 0) or 0) + 1

    def set_agent2_active_artifact_version(self, *, run_id: str, artifact_version: int) -> dict | None:
        with self._lock, self._conn() as conn:
            changed = self._set_active_artifact_revision(
                conn,
                table="agent2_artifacts",
                run_column="run_id",
                run_id=run_id,
                artifact_version=artifact_version,
            )
            if not changed:
                return None
            conn.commit()
        return self.get_agent2_latest_artifact(run_id)

    def get_agent2_run(self, run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent2_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_agent2_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT r.*
                FROM agent2_runs r
                JOIN agent1_runs a1 ON a1.run_id = r.source_agent1_run_id
                WHERE a1.backlog_item_id = ?
                ORDER BY r.updated_at DESC
                LIMIT ?
                """,
                (backlog_item_id, limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_agent2_observability_counters(self, backlog_item_id: str | None = None) -> dict:
        with self._conn() as conn:
            run_filter = ""
            params: list[object] = []
            if backlog_item_id:
                run_filter = "WHERE source_agent1_run_id IN (SELECT run_id FROM agent1_runs WHERE backlog_item_id = ?)"
                params.append(backlog_item_id)

            total_runs = conn.execute(
                f"SELECT COUNT(*) AS n FROM agent2_runs {run_filter}",
                tuple(params),
            ).fetchone()["n"]
            success_runs = conn.execute(
                f"SELECT COUNT(*) AS n FROM agent2_runs {run_filter} {'AND' if run_filter else 'WHERE'} state = ?",
                tuple(params + ['handoff_emitted']),
            ).fetchone()["n"]
            failed_runs = conn.execute(
                f"SELECT COUNT(*) AS n FROM agent2_runs {run_filter} {'AND' if run_filter else 'WHERE'} state = ?",
                tuple(params + ['failed']),
            ).fetchone()["n"]

            review_filter = ""
            review_params: list[object] = []
            if backlog_item_id:
                review_filter = (
                    "WHERE run_id IN ("
                    "SELECT r.run_id FROM agent2_runs r "
                    "JOIN agent1_runs a1 ON a1.run_id = r.source_agent1_run_id "
                    "WHERE a1.backlog_item_id = ?"
                    ")"
                )
                review_params.append(backlog_item_id)

            retry_reviews = conn.execute(
                f"SELECT COUNT(*) AS n FROM agent2_reviews {review_filter} {'AND' if review_filter else 'WHERE'} decision = ?",
                tuple(review_params + ['retry']),
            ).fetchone()["n"]
            rejection_reviews = conn.execute(
                f"SELECT COUNT(*) AS n FROM agent2_reviews {review_filter} {'AND' if review_filter else 'WHERE'} decision = ?",
                tuple(review_params + ['reject']),
            ).fetchone()["n"]

            return {
                "total_runs": total_runs,
                "success_count": success_runs,
                "retry_count": retry_reviews,
                "rejection_count": rejection_reviews,
                "failure_count": failed_runs,
            }

    def add_agent2_audit_event(
        self,
        *,
        run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent2_audit_events(run_id, stage, action, actor, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, stage, action, actor, json.dumps(metadata) if metadata else None),
            )
            conn.commit()

    def get_agent2_audit_events(self, run_id: str, *, ascending: bool = False) -> list[dict]:
        order = "ASC" if ascending else "DESC"
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent2_audit_events WHERE run_id = ? ORDER BY created_at {order}, id {order}",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "stage": r["stage"],
                    "action": r["action"],
                    "actor": r["actor"],
                    "metadata": safe_json_load(r["metadata_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def upsert_agent3_inbox(
        self,
        *,
        message_id: str,
        source_agent2_run_id: str,
        trace_id: str,
        contract_version: str,
        task_type: str,
        payload: dict,
        intake_status: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent3_inbox WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if existing:
                return self.get_agent3_inbox(message_id) or {}, False

            conn.execute(
                """
                INSERT INTO agent3_inbox(
                    message_id, source_agent2_run_id, trace_id,
                    contract_version, task_type, payload_json, intake_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    source_agent2_run_id,
                    trace_id,
                    contract_version,
                    task_type,
                    json.dumps(payload),
                    intake_status,
                ),
            )
            conn.commit()
            return self.get_agent3_inbox(message_id) or {}, True

    def get_agent3_inbox(self, message_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent3_inbox WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "message_id": row["message_id"],
                "source_agent2_run_id": row["source_agent2_run_id"],
                "trace_id": row["trace_id"],
                "contract_version": row["contract_version"],
                "task_type": row["task_type"],
                "payload": safe_json_load(row["payload_json"], {}),
                "intake_status": row["intake_status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def create_agent3_run_from_inbox(
        self,
        *,
        run_id: str,
        inbox_message_id: str,
        source_agent2_run_id: str,
        trace_id: str,
        state: str,
        stage: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent3_runs WHERE inbox_message_id = ?",
                (inbox_message_id,),
            ).fetchone()
            if existing:
                return self.get_agent3_run(existing["run_id"]) or {}, False

            business_id = self._get_or_create_business_id(
                conn,
                table="agent3_runs",
                key_column="run_id",
                key_value=run_id,
                namespace="agent3_run",
                prefix="AG3-RUN-",
            )
            conn.execute(
                """
                INSERT INTO agent3_runs(
                    run_id, inbox_message_id, source_agent2_run_id,
                    trace_id, state, stage, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    inbox_message_id,
                    source_agent2_run_id,
                    trace_id,
                    state,
                    stage,
                    business_id,
                ),
            )
            conn.execute(
                "UPDATE agent3_inbox SET intake_status = ?, updated_at = datetime('now') WHERE message_id = ?",
                ("run_created", inbox_message_id),
            )
            conn.commit()
            return self.get_agent3_run(run_id) or {}, True

    def upsert_agent3_run_state(
        self,
        *,
        run_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE agent3_runs
                SET state = ?,
                    stage = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    updated_at = datetime('now')
                WHERE run_id = ?
                """,
                (state, stage, last_error_code, last_error_message, run_id),
            )
            conn.commit()

    def get_agent3_run(self, run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent3_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_agent3_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT r.*,
                       i.payload_json AS inbox_payload_json,
                       i.updated_at AS inbox_updated_at
                FROM agent3_runs r
                JOIN agent3_inbox i ON i.message_id = r.inbox_message_id
                ORDER BY r.updated_at DESC
                LIMIT ?
                """,
                (max(limit * 5, limit),),
            ).fetchall()

        filtered: list[dict] = []
        for row in rows:
            payload = safe_json_load(row["inbox_payload_json"], {})
            payload_story_id = str(payload.get("story_id") or payload.get("backlog_item_id") or "")
            if payload_story_id != backlog_item_id:
                continue

            filtered.append(
                {
                    "run_id": row["run_id"],
                    "business_id": row["business_id"],
                    "inbox_message_id": row["inbox_message_id"],
                    "source_agent2_run_id": row["source_agent2_run_id"],
                    "trace_id": row["trace_id"],
                    "state": row["state"],
                    "stage": row["stage"],
                    "last_error_code": row["last_error_code"],
                    "last_error_message": row["last_error_message"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "story_id": payload_story_id,
                }
            )
            if len(filtered) >= limit:
                break

        return filtered

    def add_agent3_artifact(
        self,
        *,
        run_id: str,
        artifact_version: int,
        artifact: dict,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE agent3_artifacts SET is_active = 0 WHERE run_id = ?",
                (run_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO agent3_artifacts(run_id, artifact_version, artifact_json, is_active, business_id)
                VALUES (?, ?, ?, 1, ?)
                """,
                (run_id, artifact_version, json.dumps(artifact), None),
            )
            self._assign_row_business_id(
                conn,
                table="agent3_artifacts",
                key_column="id",
                key_value=int(cursor.lastrowid),
                namespace="agent3_reasoning",
                prefix="RZN-",
            )
            conn.commit()

    def get_agent3_artifacts(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, business_id, run_id, artifact_version, artifact_json, is_active, created_at
                FROM agent3_artifacts
                WHERE run_id = ?
                ORDER BY is_active DESC, artifact_version DESC, id DESC
                """,
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "business_id": r["business_id"],
                    "run_id": r["run_id"],
                    "artifact_version": r["artifact_version"],
                    "is_active": bool(r["is_active"]),
                    "artifact": safe_json_load(r["artifact_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent3_latest_artifact(self, run_id: str) -> dict | None:
        artifacts = self.get_agent3_artifacts(run_id)
        return artifacts[0] if artifacts else None

    def get_agent3_next_artifact_version(self, run_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(artifact_version), 0) AS max_version FROM agent3_artifacts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return int((row["max_version"] if row is not None else 0) or 0) + 1

    def set_agent3_active_artifact_version(self, *, run_id: str, artifact_version: int) -> dict | None:
        with self._lock, self._conn() as conn:
            changed = self._set_active_artifact_revision(
                conn,
                table="agent3_artifacts",
                run_column="run_id",
                run_id=run_id,
                artifact_version=artifact_version,
            )
            if not changed:
                return None
            conn.commit()
        return self.get_agent3_latest_artifact(run_id)

    def add_agent3_audit_event(
        self,
        *,
        run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent3_audit_events(run_id, stage, action, actor, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, stage, action, actor, json.dumps(metadata) if metadata else None),
            )
            conn.commit()

    def get_agent3_audit_events(self, run_id: str, *, ascending: bool = False) -> list[dict]:
        order = "ASC" if ascending else "DESC"
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent3_audit_events WHERE run_id = ? ORDER BY created_at {order}, id {order}",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "stage": r["stage"],
                    "action": r["action"],
                    "actor": r["actor"],
                    "metadata": safe_json_load(r["metadata_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def upsert_agent4_inbox(
        self,
        *,
        message_id: str,
        source_agent3_run_id: str,
        trace_id: str,
        contract_version: str,
        task_type: str,
        payload: dict,
        intake_status: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent4_inbox WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if existing:
                return self.get_agent4_inbox(message_id) or {}, False

            conn.execute(
                """
                INSERT INTO agent4_inbox(
                    message_id, source_agent3_run_id, trace_id,
                    contract_version, task_type, payload_json, intake_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    source_agent3_run_id,
                    trace_id,
                    contract_version,
                    task_type,
                    json.dumps(payload),
                    intake_status,
                ),
            )
            conn.commit()
            return self.get_agent4_inbox(message_id) or {}, True

    def get_agent4_inbox(self, message_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent4_inbox WHERE message_id = ?",
                (message_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "message_id": row["message_id"],
                "source_agent3_run_id": row["source_agent3_run_id"],
                "trace_id": row["trace_id"],
                "contract_version": row["contract_version"],
                "task_type": row["task_type"],
                "payload": safe_json_load(row["payload_json"], {}),
                "intake_status": row["intake_status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def create_agent4_run_from_inbox(
        self,
        *,
        run_id: str,
        inbox_message_id: str,
        source_agent3_run_id: str,
        trace_id: str,
        state: str,
        stage: str,
    ) -> tuple[dict, bool]:
        with self._lock, self._conn() as conn:
            existing = conn.execute(
                "SELECT * FROM agent4_runs WHERE inbox_message_id = ?",
                (inbox_message_id,),
            ).fetchone()
            if existing:
                return self.get_agent4_run(existing["run_id"]) or {}, False

            business_id = self._get_or_create_business_id(
                conn,
                table="agent4_runs",
                key_column="run_id",
                key_value=run_id,
                namespace="agent4_run",
                prefix="AG4-RUN-",
            )
            conn.execute(
                """
                INSERT INTO agent4_runs(
                    run_id, inbox_message_id, source_agent3_run_id,
                    trace_id, state, stage, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    inbox_message_id,
                    source_agent3_run_id,
                    trace_id,
                    state,
                    stage,
                    business_id,
                ),
            )
            conn.execute(
                "UPDATE agent4_inbox SET intake_status = ?, updated_at = datetime('now') WHERE message_id = ?",
                ("run_created", inbox_message_id),
            )
            conn.commit()
            return self.get_agent4_run(run_id) or {}, True

    def upsert_agent4_run_state(
        self,
        *,
        run_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE agent4_runs
                SET state = ?,
                    stage = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    updated_at = datetime('now')
                WHERE run_id = ?
                """,
                (state, stage, last_error_code, last_error_message, run_id),
            )
            conn.commit()

    def get_agent4_run(self, run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent4_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None

    def list_agent4_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT r.*,
                       i.payload_json AS inbox_payload_json
                FROM agent4_runs r
                JOIN agent4_inbox i ON i.message_id = r.inbox_message_id
                ORDER BY r.updated_at DESC
                LIMIT ?
                """,
                (max(limit * 5, limit),),
            ).fetchall()

        filtered: list[dict] = []
        for row in rows:
            payload = safe_json_load(row["inbox_payload_json"], {})
            payload_story_id = str(payload.get("story_id") or payload.get("backlog_item_id") or "")
            if payload_story_id != backlog_item_id:
                continue

            filtered.append(
                {
                    "run_id": row["run_id"],
                    "business_id": row["business_id"],
                    "inbox_message_id": row["inbox_message_id"],
                    "source_agent3_run_id": row["source_agent3_run_id"],
                    "trace_id": row["trace_id"],
                    "state": row["state"],
                    "stage": row["stage"],
                    "last_error_code": row["last_error_code"],
                    "last_error_message": row["last_error_message"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "story_id": payload_story_id,
                }
            )
            if len(filtered) >= limit:
                break

        return filtered

    def add_agent4_artifact(
        self,
        *,
        run_id: str,
        artifact_version: int,
        artifact: dict,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE agent4_artifacts SET is_active = 0 WHERE run_id = ?",
                (run_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO agent4_artifacts(run_id, artifact_version, artifact_json, is_active, business_id)
                VALUES (?, ?, ?, 1, ?)
                """,
                (run_id, artifact_version, json.dumps(artifact), None),
            )
            self._assign_row_business_id(
                conn,
                table="agent4_artifacts",
                key_column="id",
                key_value=int(cursor.lastrowid),
                namespace="agent4_script",
                prefix="SCR-",
            )
            conn.commit()

    def get_agent4_artifacts(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, business_id, run_id, artifact_version, artifact_json, is_active, created_at
                FROM agent4_artifacts
                WHERE run_id = ?
                ORDER BY is_active DESC, artifact_version DESC, id DESC
                """,
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "business_id": r["business_id"],
                    "run_id": r["run_id"],
                    "artifact_version": r["artifact_version"],
                    "is_active": bool(r["is_active"]),
                    "artifact": safe_json_load(r["artifact_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def get_agent4_latest_artifact(self, run_id: str) -> dict | None:
        artifacts = self.get_agent4_artifacts(run_id)
        return artifacts[0] if artifacts else None

    def get_agent4_next_artifact_version(self, run_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(artifact_version), 0) AS max_version FROM agent4_artifacts WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            return int((row["max_version"] if row is not None else 0) or 0) + 1

    def set_agent4_active_artifact_version(self, *, run_id: str, artifact_version: int) -> dict | None:
        with self._lock, self._conn() as conn:
            changed = self._set_active_artifact_revision(
                conn,
                table="agent4_artifacts",
                run_column="run_id",
                run_id=run_id,
                artifact_version=artifact_version,
            )
            if not changed:
                return None
            conn.commit()
        return self.get_agent4_latest_artifact(run_id)

    def add_agent4_audit_event(
        self,
        *,
        run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent4_audit_events(run_id, stage, action, actor, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (run_id, stage, action, actor, json.dumps(metadata) if metadata else None),
            )
            conn.commit()

    def get_agent4_audit_events(self, run_id: str, *, ascending: bool = False) -> list[dict]:
        order = "ASC" if ascending else "DESC"
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent4_audit_events WHERE run_id = ? ORDER BY created_at {order}, id {order}",
                (run_id,),
            ).fetchall()
            return [
                {
                    "id": r["id"],
                    "run_id": r["run_id"],
                    "stage": r["stage"],
                    "action": r["action"],
                    "actor": r["actor"],
                    "metadata": safe_json_load(r["metadata_json"], {}),
                    "created_at": r["created_at"],
                }
                for r in rows
            ]

    def create_execution_run(
        self,
        *,
        execution_run_id: str,
        source_agent4_run_id: str,
        backlog_item_id: str | None,
        trace_id: str,
        state: str,
        stage: str,
        request_payload: dict | None = None,
        runtime_policy: dict | None = None,
        max_attempts: int = 1,
    ) -> dict:
        with self._lock, self._conn() as conn:
            business_id = self._get_or_create_business_id(
                conn,
                table="execution_runs",
                key_column="execution_run_id",
                key_value=execution_run_id,
                namespace="execution_run",
                prefix="EXE-RUN-",
            )
            conn.execute(
                """
                INSERT INTO execution_runs(
                    execution_run_id, source_agent4_run_id, backlog_item_id,
                    trace_id, state, stage, request_json, runtime_policy_json,
                    attempt_count, max_attempts, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    execution_run_id,
                    source_agent4_run_id,
                    backlog_item_id,
                    trace_id,
                    state,
                    stage,
                    json.dumps(request_payload) if request_payload is not None else None,
                    json.dumps(runtime_policy) if runtime_policy is not None else None,
                    0,
                    max(1, int(max_attempts)),
                    business_id,
                ),
            )
            conn.commit()
        return self.get_execution_run(execution_run_id) or {}

    def mark_execution_run_running(self, *, execution_run_id: str, stage: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE execution_runs
                SET state = 'running',
                    stage = ?,
                    attempt_count = attempt_count + 1,
                    started_at = COALESCE(started_at, datetime('now')),
                    updated_at = datetime('now')
                WHERE execution_run_id = ?
                """,
                (stage, execution_run_id),
            )
            conn.commit()

    def update_execution_run_state(
        self,
        *,
        execution_run_id: str,
        state: str,
        stage: str,
        result_payload: dict | None = None,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE execution_runs
                SET state = ?,
                    stage = ?,
                    result_json = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    started_at = CASE
                        WHEN ? = 'running' THEN COALESCE(started_at, datetime('now'))
                        ELSE started_at
                    END,
                    completed_at = CASE
                        WHEN ? IN ('completed', 'failed', 'canceled') THEN COALESCE(completed_at, datetime('now'))
                        ELSE completed_at
                    END,
                    canceled_at = CASE
                        WHEN ? = 'canceled' THEN COALESCE(canceled_at, datetime('now'))
                        ELSE canceled_at
                    END,
                    updated_at = datetime('now')
                WHERE execution_run_id = ?
                """,
                (
                    state,
                    stage,
                    json.dumps(result_payload) if result_payload is not None else None,
                    last_error_code,
                    last_error_message,
                    state,
                    state,
                    state,
                    execution_run_id,
                ),
            )

            step_results = []
            if isinstance(result_payload, dict):
                raw_steps = result_payload.get("step_results")
                if isinstance(raw_steps, list):
                    step_results = [item for item in raw_steps if isinstance(item, dict)]
            if step_results:
                self._replace_execution_evidence(conn, execution_run_id, step_results)

            conn.commit()

    def get_execution_run(self, execution_run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM execution_runs WHERE execution_run_id = ?",
                (execution_run_id,),
            ).fetchone()
            if row is None:
                return None

            queue_position = None
            if row["state"] == "queued":
                queue_position = conn.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM execution_runs
                    WHERE state = 'queued'
                      AND (
                        created_at < ?
                        OR (created_at = ? AND id <= ?)
                      )
                    """,
                    (row["created_at"], row["created_at"], row["id"]),
                ).fetchone()["cnt"]

            return {
                "execution_run_id": row["execution_run_id"],
                "business_id": row["business_id"],
                "source_agent4_run_id": row["source_agent4_run_id"],
                "backlog_item_id": row["backlog_item_id"],
                "trace_id": row["trace_id"],
                "state": row["state"],
                "stage": row["stage"],
                "attempt_count": int(row["attempt_count"] or 0),
                "max_attempts": int(row["max_attempts"] or 1),
                "request": safe_json_load(row["request_json"], {}),
                "runtime_policy": safe_json_load(row["runtime_policy_json"], {}),
                "result": safe_json_load(row["result_json"], {}),
                "evidence": self.get_execution_evidence(row["execution_run_id"]),
                "last_error_code": row["last_error_code"],
                "last_error_message": row["last_error_message"],
                "queue_position": queue_position,
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "started_at": row["started_at"],
                "completed_at": row["completed_at"],
                "canceled_at": row["canceled_at"],
            }

    def claim_next_queued_execution_run(self) -> dict | None:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                """
                SELECT execution_run_id
                FROM execution_runs
                WHERE state = 'queued'
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """,
            ).fetchone()
            if row is None:
                return None

            execution_run_id = row["execution_run_id"]
            conn.execute(
                """
                UPDATE execution_runs
                SET state = 'running',
                    stage = 'phase10_execution_running',
                    attempt_count = attempt_count + 1,
                    started_at = COALESCE(started_at, datetime('now')),
                    updated_at = datetime('now')
                WHERE execution_run_id = ?
                """,
                (execution_run_id,),
            )
            conn.commit()

        return self.get_execution_run(execution_run_id)

    def recover_stale_execution_runs(self, *, ttl_seconds: int) -> list[str]:
        ttl = max(1, int(ttl_seconds))
        modifier = f"-{ttl} seconds"

        with self._lock, self._conn() as conn:
            rows = conn.execute(
                """
                SELECT execution_run_id
                FROM execution_runs
                WHERE state = 'running'
                  AND updated_at <= datetime('now', ?)
                ORDER BY updated_at ASC, id ASC
                """,
                (modifier,),
            ).fetchall()

            recovered_ids = [str(row["execution_run_id"]) for row in rows]
            if not recovered_ids:
                return []

            conn.executemany(
                """
                UPDATE execution_runs
                SET state = 'queued',
                    stage = 'phase10_execution_recovered',
                    last_error_code = 'stale_recovered',
                    last_error_message = 'Recovered stale running execution by dispatcher TTL sweep',
                    updated_at = datetime('now')
                WHERE execution_run_id = ?
                """,
                [(execution_run_id,) for execution_run_id in recovered_ids],
            )
            conn.commit()

        return recovered_ids

    def expire_pending_execution_runs(self, *, ttl_seconds: int) -> list[str]:
        ttl = max(1, int(ttl_seconds))
        modifier = f"-{ttl} seconds"

        with self._lock, self._conn() as conn:
            rows = conn.execute(
                """
                SELECT execution_run_id
                FROM execution_runs
                WHERE state = 'queued'
                  AND created_at <= datetime('now', ?)
                ORDER BY created_at ASC, id ASC
                """,
                (modifier,),
            ).fetchall()

            expired_ids = [str(row["execution_run_id"]) for row in rows]
            if not expired_ids:
                return []

            conn.executemany(
                """
                UPDATE execution_runs
                SET state = 'canceled',
                    stage = 'phase12_queue_expired',
                    last_error_code = 'pending_ttl_expired',
                    last_error_message = 'Expired in queue (pending TTL exceeded)',
                    result_json = json_object(
                        'expired', 1,
                        'reason', 'pending_ttl_exceeded',
                        'ttl_seconds', ?,
                        'expired_at', datetime('now')
                    ),
                    canceled_at = COALESCE(canceled_at, datetime('now')),
                    completed_at = COALESCE(completed_at, datetime('now')),
                    updated_at = datetime('now')
                WHERE execution_run_id = ?
                  AND state = 'queued'
                """,
                [(ttl, execution_run_id) for execution_run_id in expired_ids],
            )
            conn.commit()

        return expired_ids

    def list_execution_runs_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT execution_run_id
                FROM execution_runs
                WHERE source_agent4_run_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (source_agent4_run_id, limit),
            ).fetchall()
        items: list[dict] = []
        for row in rows:
            snapshot = self.get_execution_run(row["execution_run_id"])
            if snapshot:
                items.append(snapshot)
        return items

    def list_execution_runs(self, *, backlog_item_id: str | None = None, limit: int = 100) -> list[dict]:
        clamped_limit = max(1, min(int(limit), 1000))
        with self._conn() as conn:
            if backlog_item_id:
                rows = conn.execute(
                    """
                    SELECT execution_run_id
                    FROM execution_runs
                    WHERE backlog_item_id = ?
                    ORDER BY updated_at DESC, id DESC
                    LIMIT ?
                    """,
                    (backlog_item_id, clamped_limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT execution_run_id
                    FROM execution_runs
                    ORDER BY updated_at DESC, id DESC
                    LIMIT ?
                    """,
                    (clamped_limit,),
                ).fetchall()

        items: list[dict] = []
        for row in rows:
            snapshot = self.get_execution_run(str(row["execution_run_id"] or ""))
            if snapshot:
                items.append(snapshot)
        return items

    def log_event(
        self,
        *,
        trace_id: str,
        stage: str,
        status: str,
        run_id: str | None = None,
        story_id: str | None = None,
        model_provider: str | None = None,
        model_name: str | None = None,
        prompt_template: str | None = None,
        prompt_chars: int | None = None,
        response_chars: int | None = None,
        duration_ms: int | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            metadata_json = json.dumps(metadata) if metadata else None
            prev_signature = None
            event_signature = None

            if AUDIT_SIGNING_SECRET:
                prev_row = conn.execute(
                    """
                    SELECT event_signature
                    FROM observability_events
                    ORDER BY event_id DESC
                    LIMIT 1
                    """
                ).fetchone()
                prev_signature = str(prev_row["event_signature"] or "") if prev_row else ""

                canonical_payload = {
                    "trace_id": trace_id,
                    "run_id": run_id,
                    "story_id": story_id,
                    "stage": stage,
                    "status": status,
                    "model_provider": model_provider,
                    "model_name": model_name,
                    "prompt_template": prompt_template,
                    "prompt_chars": prompt_chars,
                    "response_chars": response_chars,
                    "duration_ms": duration_ms,
                    "error_code": error_code,
                    "error_message": error_message,
                    "metadata_json": metadata_json,
                }
                canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
                signing_input = f"{prev_signature}|{canonical}".encode("utf-8")
                event_signature = hmac.new(
                    AUDIT_SIGNING_SECRET.encode("utf-8"),
                    signing_input,
                    hashlib.sha256,
                ).hexdigest()

            conn.execute(
                """
                INSERT INTO observability_events(
                    trace_id, run_id, story_id, stage, status,
                    model_provider, model_name, prompt_template,
                    prompt_chars, response_chars, duration_ms,
                    error_code, error_message, metadata_json,
                    prev_signature, event_signature
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace_id,
                    run_id,
                    story_id,
                    stage,
                    status,
                    model_provider,
                    model_name,
                    prompt_template,
                    prompt_chars,
                    response_chars,
                    duration_ms,
                    error_code,
                    error_message,
                    metadata_json,
                    prev_signature,
                    event_signature,
                ),
            )
            conn.commit()

    def get_events_by_trace(self, trace_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM observability_events WHERE trace_id = ? ORDER BY event_id ASC",
                (trace_id,),
            ).fetchall()
            return [obs_event_row_to_dict(r) for r in rows]

    def get_events_by_run(self, run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM observability_events WHERE run_id = ? ORDER BY event_id ASC",
                (run_id,),
            ).fetchall()
            return [obs_event_row_to_dict(r) for r in rows]

    def get_events_by_story(self, story_id: str, limit: int = 5000) -> list[dict]:
        clamped_limit = max(1, min(int(limit), 20000))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM observability_events
                WHERE story_id = ?
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (story_id, clamped_limit),
            ).fetchall()
            normalized = [obs_event_row_to_dict(r) for r in rows]
            normalized.reverse()
            return normalized

    def get_recent_events(self, limit: int = 200) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM observability_events ORDER BY event_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [obs_event_row_to_dict(r) for r in rows]

    def get_queue_events(
        self,
        *,
        limit: int = 200,
        stage: str | None = None,
        status: str | None = None,
        story_id: str | None = None,
    ) -> list[dict]:
        clamped_limit = max(1, min(int(limit), 1000))
        clauses = ["stage LIKE 'queue.%'"]
        params: list[object] = []

        normalized_stage = str(stage or "").strip()
        if normalized_stage:
            clauses.append("stage = ?")
            params.append(normalized_stage)

        normalized_story_id = str(story_id or "").strip()
        if normalized_story_id:
            clauses.append("story_id = ?")
            params.append(normalized_story_id)

        normalized_status = str(status or "").strip().lower()
        if normalized_status == "ok":
            clauses.append("lower(status) IN ('queued', 'started', 'completed', 'retry_queued', 'canceled', 'expired')")
        elif normalized_status == "error":
            clauses.append("lower(status) IN ('failed', 'error', 'invalid', 'denied')")

        where_sql = " AND ".join(clauses)

        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM observability_events
                WHERE {where_sql}
                ORDER BY event_id DESC
                LIMIT ?
                """,
                (*params, clamped_limit),
            ).fetchall()
            normalized = [obs_event_row_to_dict(r) for r in rows]
            normalized.reverse()
            return normalized

    def log_operator_security_event(
        self,
        *,
        event_id: str,
        source: str,
        stage: str,
        status: str,
        reason: str | None = None,
        failures_recent: int | None = None,
        lockout_until: str | None = None,
        metadata: dict | None = None,
        created_at: str | None = None,
    ) -> None:
        normalized_event_id = str(event_id or "").strip()
        if not normalized_event_id:
            return

        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO operator_security_events(
                    event_id, source, stage, status, state, reason,
                    failures_recent, lockout_until, metadata_json, created_at, last_updated_at
                ) VALUES (?, ?, ?, ?, 'open', ?, ?, ?, ?, COALESCE(?, datetime('now')), datetime('now'))
                ON CONFLICT(event_id) DO NOTHING
                """,
                (
                    normalized_event_id,
                    str(source or "unknown").strip() or "unknown",
                    str(stage or "operator.auth").strip() or "operator.auth",
                    str(status or "n/a").strip() or "n/a",
                    str(reason).strip() if reason is not None else None,
                    int(failures_recent) if failures_recent is not None else None,
                    str(lockout_until).strip() if lockout_until is not None else None,
                    json.dumps(metadata) if metadata else None,
                    str(created_at).strip() if created_at else None,
                ),
            )
            conn.commit()

    def get_recent_operator_security_events(self, limit: int = 100) -> list[dict]:
        clamped_limit = max(1, min(int(limit), 500))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM operator_security_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (clamped_limit,),
            ).fetchall()

            events: list[dict] = []
            for row in rows:
                events.append(
                    {
                        "event_id": row["event_id"],
                        "source": row["source"],
                        "stage": row["stage"],
                        "status": row["status"],
                        "state": row["state"],
                        "acked_by": row["acked_by"],
                        "acked_at": row["acked_at"],
                        "resolved_by": row["resolved_by"],
                        "resolved_at": row["resolved_at"],
                        "resolution_note": row["resolution_note"],
                        "last_updated_at": row["last_updated_at"],
                        "reason": row["reason"],
                        "failures_recent": row["failures_recent"],
                        "lockout_until": row["lockout_until"],
                        "metadata": safe_json_load(row["metadata_json"], {}),
                        "created_at": row["created_at"],
                    }
                )

            events.reverse()
            return events

    def get_operator_security_summary(self, window_limit: int = 1000) -> dict:
        clamped_limit = max(1, min(int(window_limit), 5000))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM operator_security_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (clamped_limit,),
            ).fetchall()

        denied_count = 0
        lockout_count = 0
        sources: set[str] = set()
        by_stage: dict[str, int] = {}
        by_status: dict[str, int] = {}
        by_state: dict[str, int] = {}

        for row in rows:
            stage = str(row["stage"] or "")
            status = str(row["status"] or "")
            source = str(row["source"] or "").strip()

            by_stage[stage] = int(by_stage.get(stage, 0)) + 1
            by_status[status] = int(by_status.get(status, 0)) + 1
            state = str(row["state"] or "open")
            by_state[state] = int(by_state.get(state, 0)) + 1
            if source:
                sources.add(source)

            if stage == "operator.auth_denied":
                denied_count += 1
            if stage == "operator.auth_lockout":
                lockout_count += 1

        return {
            "window_limit": clamped_limit,
            "events_count": len(rows),
            "denied_count": denied_count,
            "lockout_count": lockout_count,
            "unique_sources": len(sources),
            "by_stage": by_stage,
            "by_status": by_status,
            "by_state": by_state,
        }

    def get_open_operator_security_incidents(self, limit: int = 200) -> list[dict]:
        clamped_limit = max(1, min(int(limit), 500))
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM operator_security_events
                WHERE lower(state) IN ('open', 'acknowledged')
                ORDER BY id DESC
                LIMIT ?
                """,
                (clamped_limit,),
            ).fetchall()

        incidents: list[dict] = []
        for row in rows:
            incidents.append(
                {
                    "event_id": row["event_id"],
                    "source": row["source"],
                    "stage": row["stage"],
                    "status": row["status"],
                    "state": row["state"],
                    "acked_by": row["acked_by"],
                    "acked_at": row["acked_at"],
                    "resolved_by": row["resolved_by"],
                    "resolved_at": row["resolved_at"],
                    "resolution_note": row["resolution_note"],
                    "reason": row["reason"],
                    "failures_recent": row["failures_recent"],
                    "lockout_until": row["lockout_until"],
                    "metadata": safe_json_load(row["metadata_json"], {}),
                    "last_updated_at": row["last_updated_at"],
                    "created_at": row["created_at"],
                }
            )

        incidents.reverse()
        return incidents

    def acknowledge_operator_security_incident(self, event_id: str, acked_by: str) -> dict | None:
        normalized_event_id = str(event_id or "").strip()
        if not normalized_event_id:
            return None

        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE operator_security_events
                SET state = 'acknowledged',
                    acked_by = ?,
                    acked_at = datetime('now'),
                    last_updated_at = datetime('now')
                WHERE event_id = ? AND lower(state) != 'resolved'
                """,
                (str(acked_by or "operator").strip() or "operator", normalized_event_id),
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM operator_security_events WHERE event_id = ? LIMIT 1",
                (normalized_event_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "event_id": row["event_id"],
                "state": row["state"],
                "acked_by": row["acked_by"],
                "acked_at": row["acked_at"],
                "resolved_by": row["resolved_by"],
                "resolved_at": row["resolved_at"],
                "resolution_note": row["resolution_note"],
                "last_updated_at": row["last_updated_at"],
            }

    def resolve_operator_security_incident(
        self,
        event_id: str,
        *,
        resolved_by: str,
        resolution_note: str | None = None,
    ) -> dict | None:
        normalized_event_id = str(event_id or "").strip()
        if not normalized_event_id:
            return None

        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE operator_security_events
                SET state = 'resolved',
                    resolved_by = ?,
                    resolved_at = datetime('now'),
                    resolution_note = ?,
                    last_updated_at = datetime('now')
                WHERE event_id = ?
                """,
                (
                    str(resolved_by or "operator").strip() or "operator",
                    str(resolution_note).strip() if resolution_note is not None else None,
                    normalized_event_id,
                ),
            )
            conn.commit()

            row = conn.execute(
                "SELECT * FROM operator_security_events WHERE event_id = ? LIMIT 1",
                (normalized_event_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "event_id": row["event_id"],
                "state": row["state"],
                "acked_by": row["acked_by"],
                "acked_at": row["acked_at"],
                "resolved_by": row["resolved_by"],
                "resolved_at": row["resolved_at"],
                "resolution_note": row["resolution_note"],
                "last_updated_at": row["last_updated_at"],
            }

    def export_operator_security_events(
        self,
        *,
        limit: int = 500,
        state: str | None = None,
    ) -> dict:
        clamped_limit = max(1, min(int(limit), 5000))
        normalized_state = str(state or "").strip().lower()
        allowed_states = {"open", "acknowledged", "resolved"}

        where_clause = ""
        params: list[object] = [clamped_limit]
        if normalized_state in allowed_states:
            where_clause = "WHERE lower(state) = ?"
            params = [normalized_state, clamped_limit]

        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT *
                FROM operator_security_events
                {where_clause}
                ORDER BY id DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()

        incidents: list[dict] = []
        by_state: dict[str, int] = {}
        by_stage: dict[str, int] = {}
        by_status: dict[str, int] = {}

        for row in rows:
            state_value = str(row["state"] or "open")
            stage_value = str(row["stage"] or "")
            status_value = str(row["status"] or "")
            by_state[state_value] = int(by_state.get(state_value, 0)) + 1
            by_stage[stage_value] = int(by_stage.get(stage_value, 0)) + 1
            by_status[status_value] = int(by_status.get(status_value, 0)) + 1

            incidents.append(
                {
                    "event_id": row["event_id"],
                    "source": row["source"],
                    "stage": row["stage"],
                    "status": row["status"],
                    "state": row["state"],
                    "acked_by": row["acked_by"],
                    "acked_at": row["acked_at"],
                    "resolved_by": row["resolved_by"],
                    "resolved_at": row["resolved_at"],
                    "resolution_note": row["resolution_note"],
                    "reason": row["reason"],
                    "failures_recent": row["failures_recent"],
                    "lockout_until": row["lockout_until"],
                    "metadata": safe_json_load(row["metadata_json"], {}),
                    "last_updated_at": row["last_updated_at"],
                    "created_at": row["created_at"],
                }
            )

        incidents.reverse()
        return {
            "summary": {
                "limit": clamped_limit,
                "state_filter": normalized_state if normalized_state in allowed_states else None,
                "count": len(incidents),
                "by_state": by_state,
                "by_stage": by_stage,
                "by_status": by_status,
            },
            "incidents": incidents,
        }

    def upsert_story_runtime_context(
        self,
        *,
        story_id: str,
        target_url: str,
        context_bundle: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO story_runtime_context(story_id, target_url, last_context_bundle_json)
                VALUES (?, ?, ?)
                ON CONFLICT(story_id) DO UPDATE SET
                    target_url=excluded.target_url,
                    last_context_bundle_json=excluded.last_context_bundle_json,
                    updated_at=datetime('now')
                """,
                (story_id, target_url, json.dumps(context_bundle) if context_bundle else None),
            )
            conn.commit()

    def get_story_runtime_context(self, story_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM story_runtime_context WHERE story_id = ?",
                (story_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "story_id": row["story_id"],
                "target_url": row["target_url"],
                "last_context_bundle_json": row["last_context_bundle_json"],
                "updated_at": row["updated_at"],
            }

    def update_scraper_job_state(
        self,
        *,
        job_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> dict | None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE scraper_jobs
                SET state = ?,
                    stage = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    updated_at = datetime('now')
                WHERE job_id = ?
                """,
                (state, stage, last_error_code, last_error_message, job_id),
            )
            conn.commit()
            return self.get_scraper_job(job_id)

    def create_scraper_job(
        self,
        *,
        job_id: str,
        backlog_item_id: str,
        target_url: str,
        state: str,
        stage: str,
        config: dict,
    ) -> dict:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO scraper_jobs(
                    job_id, backlog_item_id, target_url, state, stage, config_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, backlog_item_id, target_url, state, stage, json.dumps(config)),
            )
            conn.commit()
            return self.get_scraper_job(job_id) or {}

    def get_scraper_job(self, job_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM scraper_jobs WHERE job_id = ?",
                (job_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "job_id": row["job_id"],
                "backlog_item_id": row["backlog_item_id"],
                "target_url": row["target_url"],
                "state": row["state"],
                "stage": row["stage"],
                "config": safe_json_load(row["config_json"], {}),
                "last_error_code": row["last_error_code"],
                "last_error_message": row["last_error_message"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }

    def list_scraper_jobs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM scraper_jobs
                WHERE backlog_item_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (backlog_item_id, limit),
            ).fetchall()
            return [
                {
                    "job_id": row["job_id"],
                    "backlog_item_id": row["backlog_item_id"],
                    "target_url": row["target_url"],
                    "state": row["state"],
                    "stage": row["stage"],
                    "config": safe_json_load(row["config_json"], {}),
                    "last_error_code": row["last_error_code"],
                    "last_error_message": row["last_error_message"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                }
                for row in rows
            ]

    def create_agent5_run(
        self,
        *,
        agent5_run_id: str,
        source_agent4_run_id: str,
        source_execution_run_id: str | None,
        backlog_item_id: str | None,
        trace_id: str,
        state: str,
        stage: str,
        request_payload: dict | None = None,
    ) -> dict:
        with self._lock, self._conn() as conn:
            business_id = self._get_or_create_business_id(
                conn,
                table="agent5_runs",
                key_column="agent5_run_id",
                key_value=agent5_run_id,
                namespace="agent5_run",
                prefix="AG5-RUN-",
            )
            conn.execute(
                """
                INSERT INTO agent5_runs(
                    agent5_run_id, source_agent4_run_id, source_execution_run_id,
                    backlog_item_id, trace_id, state, stage, request_json, business_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent5_run_id,
                    source_agent4_run_id,
                    source_execution_run_id,
                    backlog_item_id,
                    trace_id,
                    state,
                    stage,
                    json.dumps(request_payload) if request_payload is not None else None,
                    business_id,
                ),
            )
            conn.commit()
        return self.get_agent5_run(agent5_run_id) or {}

    def update_agent5_run_state(
        self,
        *,
        agent5_run_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE agent5_runs
                SET state = ?,
                    stage = ?,
                    last_error_code = ?,
                    last_error_message = ?,
                    completed_at = CASE
                        WHEN ? IN ('completed', 'failed', 'canceled') THEN COALESCE(completed_at, datetime('now'))
                        ELSE completed_at
                    END,
                    updated_at = datetime('now')
                WHERE agent5_run_id = ?
                """,
                (
                    state,
                    stage,
                    last_error_code,
                    last_error_message,
                    state,
                    agent5_run_id,
                ),
            )
            conn.commit()

    def set_agent5_run_payloads(
        self,
        *,
        agent5_run_id: str,
        execution_summary: dict | None = None,
        step_evidence_refs: list[dict] | None = None,
        stage7_analysis: dict | None = None,
        gate7_decision: dict | None = None,
        stage8_writeback: dict | None = None,
        gate8_decision: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            current = conn.execute(
                "SELECT * FROM agent5_runs WHERE agent5_run_id = ?",
                (agent5_run_id,),
            ).fetchone()
            if current is None:
                return

            next_execution_summary = (
                json.dumps(execution_summary)
                if execution_summary is not None
                else current["execution_summary_json"]
            )
            next_step_evidence_refs = (
                json.dumps(step_evidence_refs)
                if step_evidence_refs is not None
                else current["step_evidence_refs_json"]
            )
            next_stage7_analysis = (
                json.dumps(stage7_analysis)
                if stage7_analysis is not None
                else current["stage7_analysis_json"]
            )
            next_gate7_decision = (
                json.dumps(gate7_decision)
                if gate7_decision is not None
                else current["gate7_decision_json"]
            )
            next_stage8_writeback = (
                json.dumps(stage8_writeback)
                if stage8_writeback is not None
                else current["stage8_writeback_json"]
            )
            next_gate8_decision = (
                json.dumps(gate8_decision)
                if gate8_decision is not None
                else current["gate8_decision_json"]
            )

            conn.execute(
                """
                UPDATE agent5_runs
                SET execution_summary_json = ?,
                    step_evidence_refs_json = ?,
                    stage7_analysis_json = ?,
                    gate7_decision_json = ?,
                    stage8_writeback_json = ?,
                    gate8_decision_json = ?,
                    updated_at = datetime('now')
                WHERE agent5_run_id = ?
                """,
                (
                    next_execution_summary,
                    next_step_evidence_refs,
                    next_stage7_analysis,
                    next_gate7_decision,
                    next_stage8_writeback,
                    next_gate8_decision,
                    agent5_run_id,
                ),
            )
            conn.commit()

    def get_agent5_run(self, agent5_run_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM agent5_runs WHERE agent5_run_id = ?",
                (agent5_run_id,),
            ).fetchone()
            if row is None:
                return None
            return {
                "agent5_run_id": row["agent5_run_id"],
                "business_id": row["business_id"],
                "source_agent4_run_id": row["source_agent4_run_id"],
                "source_execution_run_id": row["source_execution_run_id"],
                "backlog_item_id": row["backlog_item_id"],
                "trace_id": row["trace_id"],
                "state": row["state"],
                "stage": row["stage"],
                "request": safe_json_load(row["request_json"], {}),
                "execution_summary": safe_json_load(row["execution_summary_json"], {}),
                "step_evidence_refs": safe_json_load(row["step_evidence_refs_json"], []),
                "stage7_analysis": safe_json_load(row["stage7_analysis_json"], {}),
                "gate7_decision": safe_json_load(row["gate7_decision_json"], {}),
                "stage8_writeback": safe_json_load(row["stage8_writeback_json"], {}),
                "gate8_decision": safe_json_load(row["gate8_decision_json"], {}),
                "last_error_code": row["last_error_code"],
                "last_error_message": row["last_error_message"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "completed_at": row["completed_at"],
            }

    def list_agent5_runs_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT agent5_run_id
                FROM agent5_runs
                WHERE source_agent4_run_id = ?
                ORDER BY updated_at DESC, id DESC
                LIMIT ?
                """,
                (source_agent4_run_id, max(1, int(limit))),
            ).fetchall()
            return [
                self.get_agent5_run(str(row["agent5_run_id"])) or {}
                for row in rows
            ]

    def list_agent5_runs_by_states(
        self,
        *,
        states: list[str],
        older_than_seconds: int,
        limit: int = 100,
    ) -> list[dict]:
        normalized_states = [str(state or "").strip() for state in states if str(state or "").strip()]
        if not normalized_states:
            return []

        placeholders = ",".join(["?"] * len(normalized_states))
        age_clause = f"-{max(1, int(older_than_seconds))} seconds"
        with self._conn() as conn:
            rows = conn.execute(
                f"""
                SELECT agent5_run_id
                FROM agent5_runs
                WHERE state IN ({placeholders})
                  AND updated_at <= datetime('now', ?)
                ORDER BY updated_at ASC, id ASC
                LIMIT ?
                """,
                (*normalized_states, age_clause, max(1, int(limit))),
            ).fetchall()
            return [
                self.get_agent5_run(str(row["agent5_run_id"])) or {}
                for row in rows
            ]

    def add_agent5_artifact(
        self,
        *,
        agent5_run_id: str,
        artifact_version: int,
        artifact_type: str,
        artifact: dict,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "UPDATE agent5_artifacts SET is_active = 0 WHERE agent5_run_id = ?",
                (agent5_run_id,),
            )
            cursor = conn.execute(
                """
                INSERT INTO agent5_artifacts(agent5_run_id, artifact_version, artifact_type, artifact_json, is_active, business_id)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (
                    agent5_run_id,
                    artifact_version,
                    artifact_type,
                    json.dumps(artifact),
                    None,
                ),
            )
            self._assign_row_business_id(
                conn,
                table="agent5_artifacts",
                key_column="id",
                key_value=int(cursor.lastrowid),
                namespace="agent5_artifact",
                prefix="AG5-ART-",
            )
            conn.commit()

    def get_agent5_artifacts(self, agent5_run_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, business_id, agent5_run_id, artifact_version, artifact_type, artifact_json, is_active, created_at
                FROM agent5_artifacts
                WHERE agent5_run_id = ?
                ORDER BY is_active DESC, artifact_version DESC, id DESC
                """,
                (agent5_run_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "business_id": row["business_id"],
                    "agent5_run_id": row["agent5_run_id"],
                    "artifact_version": row["artifact_version"],
                    "artifact_type": row["artifact_type"],
                    "is_active": bool(row["is_active"]),
                    "artifact": safe_json_load(row["artifact_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_agent5_next_artifact_version(self, agent5_run_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(artifact_version), 0) AS max_version FROM agent5_artifacts WHERE agent5_run_id = ?",
                (agent5_run_id,),
            ).fetchone()
            return int((row["max_version"] if row is not None else 0) or 0) + 1

    def set_agent5_active_artifact_version(self, *, agent5_run_id: str, artifact_version: int) -> dict | None:
        with self._lock, self._conn() as conn:
            changed = self._set_active_artifact_revision(
                conn,
                table="agent5_artifacts",
                run_column="agent5_run_id",
                run_id=agent5_run_id,
                artifact_version=artifact_version,
            )
            if not changed:
                return None
            conn.commit()
        artifacts = self.get_agent5_artifacts(agent5_run_id)
        return artifacts[0] if artifacts else None

    def add_agent5_timeline_event(
        self,
        *,
        agent5_run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO agent5_timeline(agent5_run_id, stage, action, actor, metadata_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    agent5_run_id,
                    stage,
                    action,
                    actor,
                    json.dumps(metadata) if metadata is not None else None,
                ),
            )
            conn.commit()

    def get_agent5_timeline_events(self, agent5_run_id: str, *, ascending: bool = True) -> list[dict]:
        order = "ASC" if ascending else "DESC"
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM agent5_timeline WHERE agent5_run_id = ? ORDER BY created_at {order}, id {order}",
                (agent5_run_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "agent5_run_id": row["agent5_run_id"],
                    "stage": row["stage"],
                    "action": row["action"],
                    "actor": row["actor"],
                    "metadata": safe_json_load(row["metadata_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def add_retry_governance_request(
        self,
        *,
        request_id: str,
        run_scope: str,
        run_id: str,
        requested_by: str,
        reason_code: str | None = None,
        reason_text: str | None = None,
        status: str = "retry_review_pending",
    ) -> dict:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO retry_governance_requests(
                    request_id, run_scope, run_id, requested_by,
                    reason_code, reason_text, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request_id,
                    run_scope,
                    run_id,
                    requested_by,
                    reason_code,
                    reason_text,
                    status,
                ),
            )
            conn.execute(
                """
                INSERT INTO retry_governance_audit_events(request_id, action, actor, metadata_json)
                VALUES (?, 'retry_requested', ?, ?)
                """,
                (
                    request_id,
                    requested_by,
                    json.dumps({
                        "run_scope": run_scope,
                        "run_id": run_id,
                        "reason_code": reason_code,
                    }),
                ),
            )
            conn.commit()
        return self.get_retry_governance_request(request_id) or {}

    def assign_retry_governance_reviewer(
        self,
        *,
        request_id: str,
        assigned_reviewer_id: str,
        assignment_mode: str,
        assigned_by: str,
        assignment_reason: str | None = None,
        escalation_status: str | None = None,
    ) -> dict | None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE retry_governance_requests
                SET assigned_reviewer_id = ?,
                    assignment_mode = ?,
                    assigned_by = ?,
                    assignment_reason = ?,
                    assigned_at = datetime('now'),
                    escalation_status = ?,
                    updated_at = datetime('now')
                WHERE request_id = ?
                """,
                (
                    assigned_reviewer_id,
                    assignment_mode,
                    assigned_by,
                    assignment_reason,
                    escalation_status,
                    request_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO retry_governance_audit_events(request_id, action, actor, metadata_json)
                VALUES (?, 'reviewer_assigned', ?, ?)
                """,
                (
                    request_id,
                    assigned_by,
                    json.dumps({
                        "assigned_reviewer_id": assigned_reviewer_id,
                        "assignment_mode": assignment_mode,
                        "assignment_reason": assignment_reason,
                        "escalation_status": escalation_status,
                    }),
                ),
            )
            conn.commit()
        return self.get_retry_governance_request(request_id)

    def review_retry_governance_request(
        self,
        *,
        request_id: str,
        reviewer_id: str,
        reviewer_decision: str,
        reviewer_comment: str | None = None,
    ) -> dict | None:
        normalized = str(reviewer_decision or "").strip().lower()
        next_status = "retry_approved" if normalized == "approve" else "retry_rejected"
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE retry_governance_requests
                SET reviewer_id = ?,
                    reviewer_decision = ?,
                    reviewer_comment = ?,
                    status = ?,
                    reviewed_at = datetime('now'),
                    updated_at = datetime('now')
                WHERE request_id = ?
                """,
                (
                    reviewer_id,
                    normalized,
                    reviewer_comment,
                    next_status,
                    request_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO retry_governance_audit_events(request_id, action, actor, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    request_id,
                    f"review_{normalized}",
                    reviewer_id,
                    json.dumps({
                        "decision": normalized,
                        "comment": reviewer_comment,
                    }),
                ),
            )
            conn.commit()
        return self.get_retry_governance_request(request_id)

    def update_retry_governance_status(
        self,
        *,
        request_id: str,
        status: str,
        actor: str,
        action: str,
        metadata: dict | None = None,
    ) -> dict | None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                UPDATE retry_governance_requests
                SET status = ?,
                    updated_at = datetime('now')
                WHERE request_id = ?
                """,
                (
                    status,
                    request_id,
                ),
            )
            conn.execute(
                """
                INSERT INTO retry_governance_audit_events(request_id, action, actor, metadata_json)
                VALUES (?, ?, ?, ?)
                """,
                (
                    request_id,
                    action,
                    actor,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
        return self.get_retry_governance_request(request_id)

    def list_retry_governance_audit_events(self, *, request_id: str) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM retry_governance_audit_events
                WHERE request_id = ?
                ORDER BY created_at DESC, id DESC
                """,
                (request_id,),
            ).fetchall()
            return [
                {
                    "id": row["id"],
                    "request_id": row["request_id"],
                    "action": row["action"],
                    "actor": row["actor"],
                    "metadata": safe_json_load(row["metadata_json"], {}),
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    def get_retry_governance_request(self, request_id: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM retry_governance_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
            return self._retry_governance_row_to_dict(row)

    def list_retry_governance_requests(self, *, run_scope: str, run_id: str, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT *
                FROM retry_governance_requests
                WHERE run_scope = ? AND run_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (run_scope, run_id, max(1, int(limit))),
            ).fetchall()
            return [self._retry_governance_row_to_dict(row) for row in rows if row is not None]

    def get_latest_retry_governance_request(self, *, run_scope: str, run_id: str) -> dict | None:
        rows = self.list_retry_governance_requests(run_scope=run_scope, run_id=run_id, limit=1)
        return rows[0] if rows else None

    @staticmethod
    def _retry_governance_row_to_dict(row: sqlite3.Row | None) -> dict | None:
        if row is None:
            return None
        return {
            "request_id": row["request_id"],
            "run_scope": row["run_scope"],
            "run_id": row["run_id"],
            "requested_by": row["requested_by"],
            "reason_code": row["reason_code"],
            "reason_text": row["reason_text"],
            "status": row["status"],
            "assigned_reviewer_id": row["assigned_reviewer_id"],
            "assignment_mode": row["assignment_mode"],
            "assigned_by": row["assigned_by"],
            "assignment_reason": row["assignment_reason"],
            "assigned_at": row["assigned_at"],
            "escalation_status": row["escalation_status"],
            "reviewer_id": row["reviewer_id"],
            "reviewer_decision": row["reviewer_decision"],
            "reviewer_comment": row["reviewer_comment"],
            "reviewed_at": row["reviewed_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def upsert_scraper_page(
        self,
        *,
        job_id: str,
        url: str,
        depth: int,
        parent_url: str | None,
        page_title: str | None,
        text_excerpt: str | None,
        source: str | None,
        status_code: int | None,
        content_type: str | None,
        links: list[str],
        errors: list[str],
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                """
                INSERT INTO scraper_pages(
                    job_id, url, depth, parent_url, page_title, text_excerpt,
                    source, status_code, content_type, links_json, error_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id, url) DO UPDATE SET
                    depth=excluded.depth,
                    parent_url=excluded.parent_url,
                    page_title=excluded.page_title,
                    text_excerpt=excluded.text_excerpt,
                    source=excluded.source,
                    status_code=excluded.status_code,
                    content_type=excluded.content_type,
                    links_json=excluded.links_json,
                    error_json=excluded.error_json,
                    fetched_at=datetime('now')
                """,
                (
                    job_id,
                    url,
                    depth,
                    parent_url,
                    page_title,
                    text_excerpt,
                    source,
                    status_code,
                    content_type,
                    json.dumps(links),
                    json.dumps(errors),
                ),
            )
            conn.commit()

    def list_scraper_pages(self, job_id: str, limit: int = 500) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT * FROM scraper_pages
                WHERE job_id = ?
                ORDER BY depth ASC, fetched_at ASC
                LIMIT ?
                """,
                (job_id, limit),
            ).fetchall()
            return [
                {
                    "job_id": row["job_id"],
                    "url": row["url"],
                    "depth": row["depth"],
                    "parent_url": row["parent_url"],
                    "page_title": row["page_title"],
                    "text_excerpt": row["text_excerpt"],
                    "source": row["source"],
                    "status_code": row["status_code"],
                    "content_type": row["content_type"],
                    "links": safe_json_load(row["links_json"], []),
                    "errors": safe_json_load(row["error_json"], []),
                    "fetched_at": row["fetched_at"],
                }
                for row in rows
            ]

    def delete_scraper_pages_for_job(self, job_id: str) -> int:
        with self._lock, self._conn() as conn:
            cursor = conn.execute(
                "DELETE FROM scraper_pages WHERE job_id = ?",
                (job_id,),
            )
            conn.commit()
            return int(cursor.rowcount or 0)


store = Store()
