import sqlite3
from typing import List
from .models import PromptTemplate, PromptVersion, TestResult
from datetime import datetime


class Storage:

    def __init__(self, db_path: str = "promptforge.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._initialize_db()

    def _initialize_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                id INTEGER PRIMARY KEY,
                name TEXT,
                content TEXT,
                category TEXT,
                tags TEXT,
                variables TEXT,
                version TEXT,
                created_at DATETIME,
                updated_at DATETIME,
                metadata TEXT
            );
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS versions (
                version_number TEXT,
                template_id INTEGER,
                content TEXT,
                changelog TEXT,
                created_at DATETIME,
                FOREIGN KEY(template_id) REFERENCES templates(id)
            );
        """)
        self.cursor.execute("""
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
        """)
        self.cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS templates_fts USING fts5(name, content, category, tags, variables, version);
        """)
        self.conn.commit()

    def save_template(self, template: PromptTemplate):
        self.cursor.execute("""
            INSERT INTO templates (name, content, category, tags, variables, version, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (template.name, template.content, template.category, ",".join(template.tags), ",".join(template.variables),
              template.version, template.created_at, template.updated_at, str(template.metadata)))
        self.conn.commit()

    def get_template(self, template_id: int) -> PromptTemplate:
        self.cursor.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        row = self.cursor.fetchone()
        return PromptTemplate(*row) if row else None

    def list_templates(self) -> List[PromptTemplate]:
        self.cursor.execute("SELECT * FROM templates")
        rows = self.cursor.fetchall()
        return [PromptTemplate(*row) for row in rows]

    def delete_template(self, template_id: int):
        self.cursor.execute("DELETE FROM templates WHERE id = ?", (template_id,))
        self.conn.commit()

    def search_templates(self, query: str) -> List[PromptTemplate]:
        self.cursor.execute("SELECT * FROM templates_fts WHERE templates_fts MATCH ?", (query,))
        rows = self.cursor.fetchall()
        return [PromptTemplate(*row) for row in rows]

    def save_version(self, version: PromptVersion):
        self.cursor.execute("""
            INSERT INTO versions (version_number, template_id, content, changelog, created_at)
            VALUES (?, ?, ?, ?, ?);
        """, (version.version_number, version.template_id, version.content, version.changelog, version.created_at))
        self.conn.commit()

    def get_versions(self, template_id: int) -> List[PromptVersion]:
        self.cursor.execute("SELECT * FROM versions WHERE template_id = ?", (template_id,))
        rows = self.cursor.fetchall()
        return [PromptVersion(*row) for row in rows]

    def save_test_result(self, result: TestResult):
        self.cursor.execute("""
            INSERT INTO test_results (template_id, model_name, input_prompt, output_response, score, latency_ms, token_usage, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (result.template_id, result.model_name, result.input_prompt, result.output_response, result.score,
              result.latency_ms, result.token_usage, result.created_at))
        self.conn.commit()

    def get_test_results(self, template_id: int) -> List[TestResult]:
        self.cursor.execute("SELECT * FROM test_results WHERE template_id = ?", (template_id,))
        rows = self.cursor.fetchall()
        return [TestResult(*row) for row in rows]

    def get_analytics(self) -> dict:
        self.cursor.execute("SELECT COUNT(*) FROM templates")
        templates_count = self.cursor.fetchone()[0]
        self.cursor.execute("SELECT COUNT(*) FROM test_results")
        test_results_count = self.cursor.fetchone()[0]
        return {"templates_count": templates_count, "test_results_count": test_results_count}
