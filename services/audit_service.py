import os
import json
from datetime import datetime

AUDIT_LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'audit_logs.jsonl')

class AuditService:
    def _ensure_dir(self):
        os.makedirs(os.path.dirname(AUDIT_LOG_FILE), exist_ok=True)

    def log_change(self, username: str, category: str, change_value: float, rows_modified: int) -> bool:
        """Append an audit record as a JSON line to a log file.

        This replaces the previous SQLite-based audit. The file is created under `data/audit_logs.jsonl`.
        """
        try:
            self._ensure_dir()
            entry = {
                "username": username,
                "category": category,
                "change_value": change_value,
                "rows_modified": rows_modified,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            return True
        except Exception as e:
            print(f"Failed to write audit log: {e}")
            return False
