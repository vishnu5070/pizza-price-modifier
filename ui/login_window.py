import customtkinter as ctk
from tkinter import messagebox
from services.auth_service import AuthService

class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, auth_service: AuthService, on_login_success, on_go_to_register):
        super().__init__(master)
        self.auth_service = auth_service
        self.on_login_success = on_login_success
        self.on_go_to_register = on_go_to_register
        self.init_ui()

    def init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        main_frame = ctk.CTkFrame(self, corner_radius=15)
        main_frame.grid(row=0, column=0, padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        
        header = ctk.CTkLabel(main_frame, text="Pizza Pricing Tool", font=("Segoe UI", 24, "bold"))
        header.grid(row=0, column=0, pady=(30, 20), padx=40)

        self.username_input = ctk.CTkEntry(main_frame, placeholder_text="Username", width=250, height=35)
        self.username_input.grid(row=1, column=0, pady=(0, 10), padx=40)

        self.password_input = ctk.CTkEntry(main_frame, placeholder_text="Password", width=250, height=35, show="*")
        self.password_input.grid(row=2, column=0, pady=(0, 20), padx=40)

        self.login_btn = ctk.CTkButton(main_frame, text="Sign In", command=self.handle_login, width=250, height=35, font=("Segoe UI", 14, "bold"))
        self.login_btn.grid(row=3, column=0, pady=(0, 10), padx=40)

        self.register_btn = ctk.CTkButton(main_frame, text="Create Account", command=self.on_go_to_register, width=250, height=35, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
        self.register_btn.grid(row=4, column=0, pady=(0, 30), padx=40)

    def handle_login(self):
        username = self.username_input.get().strip()
        password = self.password_input.get().strip()

        if not username or not password:
            messagebox.showwarning("Validation Error", "Please enter both username and password.")
            return

        if self.auth_service.login(username, password):
            self.on_login_success()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")
