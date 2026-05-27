from db.database import get_connection

class AuditService:
    def log_change(self, username: str, category: str, change_value: float, rows_modified: int) -> bool:
        """Logs a price modification to the audit database."""
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO audit_logs (username, category, change_value, rows_modified)
                VALUES (?, ?, ?, ?)
            ''', (username, category, change_value, rows_modified))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Failed to log audit: {e}")
            return False
