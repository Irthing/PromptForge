import ast
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, List, Optional

from .models import PromptTemplate, PromptVersion, TestResult


class Storage:
    def __init__(self, db_path: str = "promptforge.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self._initialize_db()

    def close(self) -> None:
        self.conn.close()

    def _initialize_db(self) -> None:
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                tags TEXT,
                variables TEXT,
                version TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                metadata TEXT
            );
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS versions (
                version_number TEXT,
                template_id INTEGER,
                content TEXT,
                changelog TEXT,
                created_at DATETIME,
                FOREIGN KEY(template_id) REFERENCES templates(id)
            );
            """
        )

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS test_results (
                id INTEGER PRIMARY KEY,
                template_id INTEGER,
                model_name TEXT,
                input_prompt TEXT,
                output_response TEXT,
                score REAL,
                latency_ms INTEGER,
                token_usage INTEGER,
                created_at DATETIME,
                FOREIGN KEY(template_id) REFERENCES templates(id)
            );
            """
        )

        self.cursor.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS templates_fts
            USING fts5(name, content, category, tags, variables, version);
            """
        )

        self.conn.commit()
        self._rebuild_fts()

    def _rebuild_fts(self) -> None:
        self.cursor.execute("DELETE FROM templates_fts;")
        self.cursor.execute(
            """
            INSERT INTO templates_fts(rowid, name, content, category, tags, variables, version)
            SELECT id, name, content, category, tags, variables, version
            FROM templates;
            """
        )
        self.conn.commit()

    @staticmethod
    def _serialize_datetime(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc).isoformat()
        if isinstance(value, str):
            return value
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _deserialize_datetime(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            return datetime.fromtimestamp(value, timezone.utc)
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def _serialize_list(value: Any) -> str:
        if value is None:
            return "[]"
        if isinstance(value, str):
            return json.dumps(
                [item.strip() for item in value.split(",") if item.strip()],
                ensure_ascii=False,
            )
        return json.dumps(list(value), ensure_ascii=False)

    @staticmethod
    def _deserialize_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return [str(item) for item in parsed]
            except json.JSONDecodeError:
                pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return list(value)

    @staticmethod
    def _serialize_metadata(value: Any) -> str:
        if value is None:
            return "{}"
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _deserialize_metadata(value: Any) -> dict:
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return {}
            try:
                parsed = json.loads(stripped)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                pass
            try:
                parsed = ast.literal_eval(stripped)
                return parsed if isinstance(parsed, dict) else {}
            except (ValueError, SyntaxError):
                return {}
        return {}

    @staticmethod
    def _fts_list_text(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return " ".join(str(item) for item in value)

    def _row_to_template(self, row: sqlite3.Row) -> PromptTemplate:
        return PromptTemplate(
            id=row["id"],
            name=row["name"],
            content=row["content"],
            category=row["category"],
            tags=self._deserialize_list(row["tags"]),
            variables=self._deserialize_list(row["variables"]),
            version=row["version"],
            created_at=self._deserialize_datetime(row["created_at"]),
            updated_at=self._deserialize_datetime(row["updated_at"]),
            metadata=self._deserialize_metadata(row["metadata"]),
        )

    def _row_to_version(self, row: sqlite3.Row) -> PromptVersion:
        return PromptVersion(
            version_number=row["version_number"],
            template_id=row["template_id"],
            content=row["content"],
            changelog=row["changelog"],
            created_at=self._deserialize_datetime(row["created_at"]),
        )

    def _row_to_test_result(self, row: sqlite3.Row) -> TestResult:
        return TestResult(
            id=row["id"],
            template_id=row["template_id"],
            model_name=row["model_name"],
            input_prompt=row["input_prompt"],
            output_response=row["output_response"],
            score=row["score"],
            latency_ms=row["latency_ms"],
            token_usage=row["token_usage"],
            created_at=self._deserialize_datetime(row["created_at"]),
        )

    def _sync_template_fts(self, template_id: int, template: PromptTemplate) -> None:
        self.cursor.execute("DELETE FROM templates_fts WHERE rowid = ?;", (template_id,))
        self.cursor.execute(
            """
            INSERT INTO templates_fts(rowid, name, content, category, tags, variables, version)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                template_id,
                template.name,
                template.content,
                template.category,
                self._fts_list_text(template.tags),
                self._fts_list_text(template.variables),
                template.version,
            ),
        )

    def save_template(self, template: PromptTemplate) -> int:
        values = (
            template.name,
            template.content,
            template.category,
            self._serialize_list(template.tags),
            self._serialize_list(template.variables),
            template.version,
            self._serialize_datetime(template.created_at),
            self._serialize_datetime(template.updated_at),
            self._serialize_metadata(template.metadata),
        )

        self.cursor.execute(
            """
            INSERT INTO templates (
                name, content, category, tags, variables, version,
                created_at, updated_at, metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            values,
        )
        template_id = int(self.cursor.lastrowid)
        self._sync_template_fts(template_id, template)
        self.conn.commit()
        return template_id

    def get_template(self, template_id: int) -> Optional[PromptTemplate]:
        self.cursor.execute("SELECT * FROM templates WHERE id = ?;", (template_id,))
        row = self.cursor.fetchone()
        return self._row_to_template(row) if row else None

    def list_templates(self) -> List[PromptTemplate]:
        self.cursor.execute("SELECT * FROM templates ORDER BY id;")
        return [self._row_to_template(row) for row in self.cursor.fetchall()]

    def delete_template(self, template_id: int) -> bool:
        self.cursor.execute("DELETE FROM templates_fts WHERE rowid = ?;", (template_id,))
        self.cursor.execute("DELETE FROM templates WHERE id = ?;", (template_id,))
        deleted = self.cursor.rowcount > 0
        self.conn.commit()
        return deleted

    def search_templates(self, query: str) -> List[PromptTemplate]:
        self.cursor.execute(
            """
            SELECT templates.*
            FROM templates
            JOIN templates_fts ON templates_fts.rowid = templates.id
            WHERE templates_fts MATCH ?
            ORDER BY bm25(templates_fts);
            """,
            (query,),
        )
        return [self._row_to_template(row) for row in self.cursor.fetchall()]

    def save_version(self, version: PromptVersion) -> None:
        self.cursor.execute(
            """
            INSERT INTO versions (
                version_number, template_id, content, changelog, created_at
            )
            VALUES (?, ?, ?, ?, ?);
            """,
            (
                version.version_number,
                version.template_id,
                version.content,
                version.changelog,
                self._serialize_datetime(version.created_at),
            ),
        )
        self.conn.commit()

    def get_versions(self, template_id: int) -> List[PromptVersion]:
        self.cursor.execute(
            "SELECT * FROM versions WHERE template_id = ?;",
            (template_id,),
        )
        return [self._row_to_version(row) for row in self.cursor.fetchall()]

    def save_test_result(self, result: TestResult) -> int:
        self.cursor.execute(
            """
            INSERT INTO test_results (
                template_id, model_name, input_prompt, output_response,
                score, latency_ms, token_usage, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                result.template_id,
                result.model_name,
                result.input_prompt,
                result.output_response,
                result.score,
                result.latency_ms,
                result.token_usage,
                self._serialize_datetime(result.created_at),
            ),
        )
        result_id = int(self.cursor.lastrowid)
        self.conn.commit()
        return result_id

    def get_test_results(self, template_id: int) -> List[TestResult]:
        self.cursor.execute(
            "SELECT * FROM test_results WHERE template_id = ?;",
            (template_id,),
        )
        return [self._row_to_test_result(row) for row in self.cursor.fetchall()]

    def get_analytics(self) -> dict:
        self.cursor.execute("SELECT COUNT(*) FROM templates;")
        templates_count = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM test_results;")
        test_results_count = self.cursor.fetchone()[0]
        return {
            "templates_count": templates_count,
            "test_results_count": test_results_count,
        }
