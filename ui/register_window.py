import customtkinter as ctk
from tkinter import messagebox
from services.auth_service import AuthService

class RegisterWindow(ctk.CTkFrame):
    def __init__(self, master, auth_service: AuthService, on_register_success, on_back_to_login):
        super().__init__(master)
        self.auth_service = auth_service
        self.on_register_success = on_register_success
        self.on_back_to_login = on_back_to_login
        self.init_ui()

    def init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkLabel(self, text="Create Account", font=("Segoe UI", 24, "bold"))
        header.grid(row=0, column=0, pady=(40, 20))

        self.username_input = ctk.CTkEntry(self, placeholder_text="Username", width=250)
        self.username_input.grid(row=1, column=0, pady=10)

        self.password_input = ctk.CTkEntry(self, placeholder_text="Password", width=250, show="*")
        self.password_input.grid(row=2, column=0, pady=10)

        self.confirm_password_input = ctk.CTkEntry(self, placeholder_text="Confirm Password", width=250, show="*")
        self.confirm_password_input.grid(row=3, column=0, pady=10)

        self.register_btn = ctk.CTkButton(self, text="Register", command=self.handle_register, width=250)
        self.register_btn.grid(row=4, column=0, pady=(20, 10))

        self.back_btn = ctk.CTkButton(self, text="Back to Login", command=self.on_back_to_login, width=250, fg_color="transparent", border_width=1, text_color=("black", "white"))
        self.back_btn.grid(row=5, column=0, pady=10)

    def handle_register(self):
        username = self.username_input.get().strip()
        password = self.password_input.get().strip()
        confirm_password = self.confirm_password_input.get().strip()

        if not username or not password or not confirm_password:
            messagebox.showwarning("Validation Error", "Please fill in all fields.")
            return

        if password != confirm_password:
            messagebox.showwarning("Validation Error", "Passwords do not match.")
            return

        success, message = self.auth_service.create_account(username, password)
        if success:
            messagebox.showinfo("Success", message)
            self.on_register_success()
        else:
            messagebox.showerror("Error", message)
