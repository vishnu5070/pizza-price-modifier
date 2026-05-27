import bcrypt
from db.database import get_connection

class AuthService:
    def __init__(self):
        self.current_user = None

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def seed_admin(self):
        """Creates an admin user if none exists."""
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = 'admin'")
        if cursor.fetchone()[0] == 0:
            hashed = self.hash_password('admin123')
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", ('admin', hashed))
            conn.commit()
        conn.close()

    def login(self, username, password) -> bool:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            if self.check_password(password, row['password_hash']):
                self.current_user = username
                return True
        return False

    def create_account(self, username, password) -> tuple[bool, str]:
        """Creates a new user account if the username doesn't already exist."""
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
        if cursor.fetchone()[0] > 0:
            conn.close()
            return False, "Username already exists."
        
        hashed = self.hash_password(password)
        try:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hashed))
            conn.commit()
            conn.close()
            return True, "Account created successfully."
        except Exception as e:
            conn.close()
            return False, str(e)

    def logout(self):
        self.current_user = None

    def get_current_user(self):
        return self.current_user
