import customtkinter as ctk
import tkinter as tk
import os
import json
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
from services.excel_service import ExcelService
from services.audit_service import AuditService
from services.s3_service import S3Service
from services.auth_service import AuthService

class DashboardWindow(ctk.CTkFrame):
    def __init__(self, master, auth_service: AuthService, on_logout):
        super().__init__(master)
        self.auth_service = auth_service
        self.on_logout = on_logout
        
        self.excel_service = ExcelService()
        self.audit_service = AuditService()
        self.s3_service = S3Service()
        
        self.current_updated_file = None
        
        self.init_ui()

    def _get_presign_api_url(self):
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'config.json')
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as cf:
                    cfg = json.load(cf)
                endpoint = cfg.get('presign_api_url')
                if endpoint:
                    endpoint = endpoint.strip()
                    if endpoint and 'your-api-gateway-endpoint-here' not in endpoint and 'example' not in endpoint.lower():
                        return endpoint
        except Exception:
            pass
        return None

    def init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        header_frame.grid_columnconfigure(0, weight=1)
        
        welcome_label = ctk.CTkLabel(header_frame, text=f"Welcome, {self.auth_service.get_current_user()}", font=("Segoe UI", 18, "bold"))
        welcome_label.grid(row=0, column=0, sticky="w")
        
        logout_btn = ctk.CTkButton(header_frame, text="Logout", command=self.handle_logout, width=100)
        logout_btn.grid(row=0, column=1, sticky="e")

        # File Selection
        file_frame = ctk.CTkFrame(self, fg_color="transparent")
        file_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        browse_btn = ctk.CTkButton(file_frame, text="Browse File", command=self.browse_file, width=120)
        browse_btn.pack(side="left", padx=(0, 10))
        
        self.file_label = ctk.CTkLabel(file_frame, text="Selected File: None")
        self.file_label.pack(side="left")

        # Controls
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        ctk.CTkLabel(controls_frame, text="Pizza Category:").pack(side="left", padx=(0, 5))
        self.category_cb = ctk.CTkOptionMenu(controls_frame, values=[], width=150)
        self.category_cb.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(controls_frame, text="Price Change:").pack(side="left", padx=(0, 5))
        self.price_input = ctk.CTkEntry(controls_frame, placeholder_text="e.g. +5 or -2.5", width=120)
        self.price_input.pack(side="left", padx=(0, 20))
        
        preview_btn = ctk.CTkButton(controls_frame, text="Preview", command=self.generate_preview, width=100)
        preview_btn.pack(side="left")

        # Preview Table (using ttk.Treeview as customtkinter doesn't have a table widget yet)
        table_frame = ctk.CTkFrame(self)
        table_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 20))
        table_frame.grid_columnconfigure(0, weight=1)
        table_frame.grid_rowconfigure(0, weight=1)
        
        columns = ("Pizza Name", "Old Price", "New Price", "Difference")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=150, anchor="center")
            
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        # Actions
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.apply_btn = ctk.CTkButton(actions_frame, text="Apply Changes & Save", command=self.apply_changes, state="disabled")
        self.apply_btn.pack(side="left", padx=(0, 10))
        
        self.upload_btn = ctk.CTkButton(actions_frame, text="Upload To S3", command=self.upload_to_s3, state="disabled")
        self.upload_btn.pack(side="left")

        # Status
        self.status_label = ctk.CTkLabel(self, text="Status: Ready")
        self.status_label.grid(row=5, column=0, sticky="w", padx=20, pady=(0, 20))

    def browse_file(self):
        file_path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel Files", "*.xlsx")])
        if file_path:
            if self.excel_service.load_file(file_path):
                self.file_label.configure(text=f"Selected File: {os.path.basename(file_path)}")
                self.populate_categories()
                self.status_label.configure(text="Status: File loaded successfully.")
                self.current_updated_file = None
                self.upload_btn.configure(state="disabled")
                self.clear_table()
                self.apply_btn.configure(state="disabled")
            else:
                messagebox.showerror("Error", "Failed to load Excel file.")
                self.status_label.configure(text="Status: Error loading file.")

    def populate_categories(self):
        categories = self.excel_service.get_categories()
        if categories:
            self.category_cb.configure(values=categories)
            self.category_cb.set(categories[0])
        else:
            self.category_cb.configure(values=[])
            self.category_cb.set("")

    def get_price_change(self) -> float:
        try:
            val = float(self.price_input.get().strip())
            return val
        except ValueError:
            return None

    def clear_table(self):
        for item in self.table.get_children():
            self.table.delete(item)

    def generate_preview(self):
        category = self.category_cb.get()
        if not category:
            messagebox.showwarning("Warning", "Please select a category.")
            return
            
        price_change = self.get_price_change()
        if price_change is None:
            messagebox.showwarning("Validation Error", "Please enter a valid numeric price change (e.g. 5, -2).")
            return

        preview_data = self.excel_service.preview_changes(category, price_change)
        
        self.clear_table()
        if not preview_data:
            messagebox.showinfo("Info", "No pizzas found for this category.")
            self.apply_btn.configure(state="disabled")
            return

        for data in preview_data:
            diff_str = f"+{data['difference']}" if data['difference'] > 0 else str(data['difference'])
            self.table.insert("", "end", values=(
                str(data['pizza_name']),
                f"{data['old_price']:.2f}",
                f"{data['new_price']:.2f}",
                diff_str
            ))

        self.apply_btn.configure(state="normal")
        self.status_label.configure(text="Status: Preview generated. Ready to apply.")

    def apply_changes(self):
        category = self.category_cb.get()
        price_change = self.get_price_change()
        
        if not category or price_change is None:
            return

        reply = messagebox.askyesno('Confirm', f"Apply {price_change} to all '{category}' pizzas?")
        
        if reply:
            success, rows_modified, new_path = self.excel_service.apply_and_save(category, price_change)
            if success:
                self.current_updated_file = new_path
                self.audit_service.log_change(
                    self.auth_service.get_current_user(),
                    category,
                    price_change,
                    rows_modified
                )
                self.status_label.configure(text=f"Status: Changes saved to {os.path.basename(new_path)}")
                messagebox.showinfo("Success", f"Successfully updated {rows_modified} records.")
                self.upload_btn.configure(state="normal")
                self.apply_btn.configure(state="disabled")
                self.clear_table()
            else:
                messagebox.showerror("Error", f"Failed to apply changes: {new_path}")
                self.status_label.configure(text="Status: Error saving changes.")

    def upload_to_s3(self):
        if not self.current_updated_file:
            return
        # Ask whether to upload via fresh presigned URL from backend or direct bucket
        use_presign = messagebox.askyesno(
            "Upload Method",
            "Use backend presigned-URL flow? (Yes = backend URL -> fresh presigned URL -> S3, No = direct bucket upload)",
        )

        self.status_label.configure(text="Status: Uploading to S3...")
        self.master.update()

        if use_presign:
            presign_api_url = self._get_presign_api_url()
            if not presign_api_url:
                presign_api_url = simpledialog.askstring(
                    "Presign API",
                    "Enter backend endpoint that returns a fresh presigned URL (POST):"
                )
                if not presign_api_url:
                    self.status_label.configure(text="Status: Upload cancelled.")
                    return

            success, message = self.s3_service.upload_file(
                self.current_updated_file,
                presign_api_url=presign_api_url,
            )
            if success:
                self.status_label.configure(text="Status: Successfully uploaded to S3.")
                messagebox.showinfo("Success", "File uploaded to S3 successfully via backend-generated presigned URL.")
            else:
                self.status_label.configure(text="Status: S3 upload failed.")
                messagebox.showerror("Error", f"Failed to upload via backend-generated presigned URL.\nDetails: {message}")

            return

        bucket_name = simpledialog.askstring("S3 Upload", "Enter S3 Bucket Name:")
        if bucket_name:
            success, message = self.s3_service.upload_file(self.current_updated_file, bucket_name=bucket_name.strip())
            if success:
                self.status_label.configure(text="Status: Successfully uploaded to S3.")
                messagebox.showinfo("Success", "File uploaded to S3 successfully.")
            else:
                self.status_label.configure(text="Status: S3 upload failed.")
                messagebox.showerror("Error", f"Failed to upload to S3. Details: {message}")

    def handle_logout(self):
        self.auth_service.logout()
        self.on_logout()
