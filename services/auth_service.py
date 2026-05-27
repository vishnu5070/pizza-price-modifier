import json
import os

import bcrypt


AUTH_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'credentials.json')

class AuthService:
    def __init__(self):
        self.current_user = None

    def _ensure_storage_dir(self):
        os.makedirs(os.path.dirname(AUTH_FILE), exist_ok=True)

    def _load_users(self) -> dict:
        self._ensure_storage_dir()
        if not os.path.exists(AUTH_FILE):
            return {}

        try:
            with open(AUTH_FILE, 'r', encoding='utf-8') as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError):
            return {}

        if isinstance(data, dict):
            return {str(username): str(password_hash) for username, password_hash in data.items()}

        return {}

    def _save_users(self, users: dict):
        self._ensure_storage_dir()
        with open(AUTH_FILE, 'w', encoding='utf-8') as file:
            json.dump(users, file, indent=2)

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def seed_admin(self):
        """Creates an admin user in the local credentials file if none exists."""
        users = self._load_users()
        if 'admin' not in users:
            users['admin'] = self.hash_password('admin123')
            self._save_users(users)

    def login(self, username, password) -> bool:
        users = self._load_users()
        password_hash = users.get(username)

        if password_hash and self.check_password(password, password_hash):
            self.current_user = username
            return True
        return False

    def create_account(self, username, password) -> tuple[bool, str]:
        """Creates a new user account in the local credentials file."""
        users = self._load_users()

        if username in users:
            return False, "Username already exists."

        hashed = self.hash_password(password)
        try:
            users[username] = hashed
            self._save_users(users)
            return True, "Account created successfully."
        except Exception as e:
            return False, str(e)

    def logout(self):
        self.current_user = None

    def get_current_user(self):
        return self.current_user
