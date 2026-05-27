import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
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
        
        self.progress_bar = ctk.CTkProgressBar(bottom_frame, width=150, mode="indeterminate")
        self.progress_bar.grid(row=0, column=2, sticky="e", padx=(0, 15))
        self.progress_bar.grid_remove() # hide initially
        
        self.status_label = ctk.CTkLabel(bottom_frame, text="Status: Ready", text_color="gray")
        self.status_label.grid(row=0, column=3, sticky="e")

    def browse_file(self):
        file_path = filedialog.askopenfilename(title="Select Excel File", filetypes=[("Excel Files", "*.xlsx")])
        if file_path:
            self.progress_bar.grid()
            self.progress_bar.start()
            self.status_label.configure(text="Status: Loading file...")
            self.apply_btn.configure(state="disabled")
            self.master.update()
            
            # defer execution so the UI refreshes and shows the progress bar animation
            self.after(500, self._process_file_load, file_path)

    def _process_file_load(self, file_path):
        if self.excel_service.load_file(file_path):
            self.file_label.configure(text=f"Selected File: {file_path.split('/')[-1]}")
            self.populate_categories()
            self.status_label.configure(text="Status: File loaded successfully.")
            self.current_updated_file = None
            self.upload_btn.configure(state="disabled")
            self.clear_table()
        else:
            messagebox.showerror("Error", "Failed to load Excel file.")
            self.status_label.configure(text="Status: Error loading file.")
            
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

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
            self.progress_bar.grid()
            self.progress_bar.start()
            self.status_label.configure(text="Status: Applying unit price...")
            self.apply_btn.configure(state="disabled")
            self.master.update()
            
            # defer execution so the UI refreshes and shows the progress bar animation
            self.after(500, self._process_apply_changes, category, price_change)

    def _process_apply_changes(self, category, price_change):
        success, rows_modified, new_path = self.excel_service.apply_and_save(category, price_change)
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
            
        self.progress_bar.stop()
        self.progress_bar.grid_remove()

    def upload_to_s3(self):
        if not self.current_updated_file:
            return
            
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
                messagebox.showerror("Error", "Failed to upload to S3. Check credentials and bucket name.")

    def handle_logout(self):
        self.auth_service.logout()
        self.on_logout()
