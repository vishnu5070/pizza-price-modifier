import customtkinter as ctk
import tkinter as tk
import os
import json
from tkinter import filedialog, messagebox, simpledialog
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
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
        self._progress_value = 0
        self._is_processing = False
        
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
        self.grid_rowconfigure(2, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        welcome_label = ctk.CTkLabel(header_frame, text=f"Dashboard - Welcome, {self.auth_service.get_current_user()}", font=("Segoe UI", 24, "bold"))
        welcome_label.grid(row=0, column=0, sticky="w")
        
        logout_btn = ctk.CTkButton(header_frame, text="Logout", command=self.handle_logout, width=100, fg_color="transparent", border_width=1, text_color=("gray10", "gray90"))
        logout_btn.grid(row=0, column=1, sticky="e")

        # Controls Container (File + Filters)
        controls_container = ctk.CTkFrame(self)
        controls_container.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        controls_container.grid_columnconfigure(1, weight=1)

        # File Selection
        file_frame = ctk.CTkFrame(controls_container, fg_color="transparent")
        file_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=15)
        
        browse_btn = ctk.CTkButton(file_frame, text="Browse Excel File", command=self.browse_file, width=140)
        browse_btn.pack(side="left", padx=(0, 15))
        
        self.file_label = ctk.CTkLabel(file_frame, text="Selected File: None", text_color="gray")
        self.file_label.pack(side="left")

        # Filters
        filter_frame = ctk.CTkFrame(controls_container, fg_color="transparent")
        filter_frame.grid(row=0, column=1, sticky="e", padx=15, pady=15)
        
        ctk.CTkLabel(filter_frame, text="Category:").pack(side="left", padx=(0, 5))
        self.category_cb = ctk.CTkOptionMenu(filter_frame, values=["- Select -"], width=130)
        self.category_cb.pack(side="left", padx=(0, 15))
        
        ctk.CTkLabel(filter_frame, text="Unit Price:").pack(side="left", padx=(0, 5))
        self.price_input = ctk.CTkEntry(filter_frame, placeholder_text="e.g. +5 or -2.5", width=110)
        self.price_input.pack(side="left", padx=(0, 15))
        
        preview_btn = ctk.CTkButton(filter_frame, text="Preview", command=self.generate_preview, width=100)
        preview_btn.pack(side="left")

        # Preview Table 
        table_container = ctk.CTkFrame(self)
        table_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        table_container.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(1, weight=1)
        
        table_lbl = ctk.CTkLabel(table_container, text="Unit Price Preview", font=("Segoe UI", 16, "bold"))
        table_lbl.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))
        
        # Configure treeview style matching customtkinter
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#2b2b2b" if is_dark else "#dbdbdb"
        text_color = "white" if is_dark else "black"
        selected_color = "#1f538d"
        
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview",
                        background=bg_color,
                        foreground=text_color,
                        rowheight=30,
                        fieldbackground=bg_color,
                        bordercolor=bg_color,
                        borderwidth=0,
                        font=("Segoe UI", 10))
        style.map('Treeview', background=[('selected', selected_color)])
        style.configure("Treeview.Heading",
                        background=selected_color,
                        foreground="white",
                        relief="flat",
                        font=("Segoe UI", 10, "bold"),
                        padding=5)
        style.map("Treeview.Heading",
                  background=[('active', '#14375e')])

        table_frame = ctk.CTkFrame(table_container, fg_color="transparent")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
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

        # Actions and Status
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        bottom_frame.grid_columnconfigure(2, weight=1)
        
        self.apply_btn = ctk.CTkButton(bottom_frame, text="Apply Unit Price & Save", command=self.apply_changes, state="disabled", fg_color="#28a745", hover_color="#218838")
        self.apply_btn.grid(row=0, column=0, padx=(0, 10))
        
        self.upload_btn = ctk.CTkButton(bottom_frame, text="Upload To S3", command=self.upload_to_s3, state="disabled")
        self.upload_btn.grid(row=0, column=1, sticky="w")
        
        self.progress_container = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        self.progress_container.grid(row=0, column=2, sticky="e", padx=(0, 15))
        self.progress_container.grid_remove() # hide initially
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_container, width=150, mode="determinate")
        self.progress_bar.pack(side="left", padx=(0, 5))
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(self.progress_container, text="0%", width=40)
        self.progress_label.pack(side="left")
        
        self.status_label = ctk.CTkLabel(bottom_frame, text="Status: Ready", text_color="gray")
        self.status_label.grid(row=0, column=3, sticky="e")

    def _start_progress(self, status_text):
        self.progress_container.grid()
        self.status_label.configure(text=f"Status: {status_text}")
        self._progress_value = 0
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self._is_processing = True
        self._animate_progress()

    def _animate_progress(self):
        if self._is_processing and self._progress_value < 90:
            # Simulate real loading percentage jump
            self._progress_value += 3  
            if self._progress_value > 90:
                self._progress_value = 90
            self.progress_bar.set(self._progress_value / 100.0)
            self.progress_label.configure(text=f"{self._progress_value}%")
            self.after(50, self._animate_progress)

    def _complete_progress(self):
        self._is_processing = False
        self._progress_value = 100
        self.progress_bar.set(1.0)
        self.progress_label.configure(text="100%")
        self.master.update()
        self.after(1500, self.progress_container.grid_remove)

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
            self._start_progress("Loading file...")
            self.apply_btn.configure(state="disabled")
            
            # Start actual work in a thread so UI doesn't freeze
            threading.Thread(target=self._threaded_load_file, args=(file_path,), daemon=True).start()

    def _threaded_load_file(self, file_path):
        success = self.excel_service.load_file(file_path)
        self.after(0, self._process_file_load_complete, file_path, success)

    def _process_file_load_complete(self, file_path, success):
        self._complete_progress()
        if success:
            self.file_label.configure(text=f"Selected File: {file_path.split('/')[-1]}")
            self.populate_categories()
            self.status_label.configure(text="Status: File loaded successfully.")
            self.current_updated_file = None
            self.upload_btn.configure(state="disabled")
            self.clear_table()
        else:
            messagebox.showerror("Error", "Failed to load Excel file.")
            self.status_label.configure(text="Status: Error loading file.")

    def populate_categories(self):
        categories = self.excel_service.get_categories()
        if categories:
            self.category_cb.configure(values=categories)
            self.category_cb.set(categories[0])
        else:
            self.category_cb.configure(values=["- Select -"])
            self.category_cb.set("- Select -")

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
        if not category or category == "- Select -":
            messagebox.showwarning("Warning", "Please select a category.")
            return
            
        price_change = self.get_price_change()
        if price_change is None:
            messagebox.showwarning("Validation Error", "Please enter a valid numeric unit price (e.g. 5, -2).")
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
            self._start_progress("Applying unit price...")
            self.apply_btn.configure(state="disabled")
            
            # Start actual work in a thread so UI doesn't freeze
            threading.Thread(target=self._threaded_apply_changes, args=(category, price_change), daemon=True).start()

    def _threaded_apply_changes(self, category, price_change):
        success, rows_modified, new_path = self.excel_service.apply_and_save(category, price_change)
        self.after(0, self._process_apply_changes_complete, category, price_change, success, rows_modified, new_path)

    def _process_apply_changes_complete(self, category, price_change, success, rows_modified, new_path):
        self._complete_progress()
        if success:
            self.current_updated_file = new_path
            self.audit_service.log_change(
                self.auth_service.get_current_user(),
                category,
                price_change,
                rows_modified
            )
            self.status_label.configure(text="Status: Changes applied")
            messagebox.showinfo("Success", f"Successfully updated {rows_modified} records.")
            self.upload_btn.configure(state="normal")
            self.clear_table()
        else:
            messagebox.showerror("Error", f"Failed to apply changes: {new_path}")
            self.status_label.configure(text="Status: Error saving changes.")
            self.apply_btn.configure(state="normal")

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
            
        dialog = ctk.CTkInputDialog(text="Enter S3 Bucket Name:", title="S3 Upload")
        bucket_name = dialog.get_input()
        if bucket_name:
            self.status_label.configure(text="Status: Uploading to S3...")
            self.master.update()
            success = self.s3_service.upload_file(self.current_updated_file, bucket_name)
            if success:
                self.status_label.configure(text="Status: Successfully uploaded to S3.")
                messagebox.showinfo("Success", "File uploaded to S3 successfully.")
            else:
                self.status_label.configure(text="Status: S3 upload failed.")
                messagebox.showerror("Error", f"Failed to upload to S3. Details: {message}")

    def handle_logout(self):
        self.auth_service.logout()
        self.on_logout()
