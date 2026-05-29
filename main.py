import customtkinter as ctk
from ui.login_window import LoginWindow
from ui.dashboard_window import DashboardWindow
from ui.register_window import RegisterWindow
from services.auth_service import AuthService

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class PizzaPricingApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialize services and seed admin user
        self.auth_service = AuthService()
        self.auth_service.seed_admin()

        self.title("Pizza Pricing Tool")
        self.geometry("900x650")
        self.minsize(600, 500)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Initialize Views
        self.login_window = LoginWindow(self, self.auth_service, self.show_dashboard, self.show_register)
        self.register_window = RegisterWindow(self, self.auth_service, self.show_login, self.show_login)
        self.dashboard_window = None

        self.current_window = None
        self.show_login()

    def show_dashboard(self):
        if self.current_window:
            self.current_window.grid_forget()
            
        self.geometry("1100x680")
        self.dashboard_window = DashboardWindow(self, self.auth_service, self.show_login)
        self.dashboard_window.grid(row=0, column=0, sticky="nsew")
        self.current_window = self.dashboard_window
        
        self.login_window.username_input.delete(0, 'end')
        self.login_window.password_input.delete(0, 'end')

    def show_login(self):
        if self.current_window:
            self.current_window.grid_forget()
            if self.current_window == self.dashboard_window:
                self.dashboard_window.destroy()
                self.dashboard_window = None
                
        self.geometry("500x450")
        self.login_window.grid(row=0, column=0, sticky="nsew")
        self.current_window = self.login_window
        
        self.register_window.username_input.delete(0, 'end')
        self.register_window.password_input.delete(0, 'end')
        self.register_window.confirm_password_input.delete(0, 'end')

    def show_register(self):
        if self.current_window:
            self.current_window.grid_forget()
            
        self.geometry("500x450")
        self.register_window.grid(row=0, column=0, sticky="nsew")
        self.current_window = self.register_window

    def run(self):
        self.mainloop()

if __name__ == '__main__':
    app = PizzaPricingApp()
    app.run()
