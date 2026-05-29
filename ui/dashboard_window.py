import customtkinter as ctk
import tkinter as tk
import os
from tkinter import filedialog, messagebox
from tkinter import ttk
import threading
from services.excel_service import ExcelService
from services.audit_service import AuditService
from services.s3_service import S3Service
from services.auth_service import AuthService

# ─── Per-file state container ───────────────────────────────────────────────
class FileEntry:
    """Holds all state for one loaded Excel file."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.name = os.path.basename(file_path)
        self.excel_service = ExcelService()
        self.loaded = False
        self.category = None
        self.price_change = None
        self.preview_data = []          # list of dicts from excel_service
        self.applied = False            # True after apply_and_save succeeded
        self.updated_file_path = None   # path to the _updated.xlsx
        self.uploaded = False           # True after S3 upload


# ─── Main Dashboard ──────────────────────────────────────────────────────────
class DashboardWindow(ctk.CTkFrame):
    def __init__(self, master, auth_service: AuthService, on_logout):
        super().__init__(master)
        self.auth_service = auth_service
        self.on_logout = on_logout

        self.audit_service = AuditService()
        self.s3_service = S3Service()

        self._progress_value = 0
        self._is_processing = False

        # file_entries: ordered list of FileEntry objects
        self.file_entries: list[FileEntry] = []
        # currently selected FileEntry
        self.selected_entry: FileEntry | None = None

        # Bulk upload tracking
        self._bulk_total = 0
        self._bulk_done = 0
        self._bulk_failed = 0

        self.init_ui()

    # ── Layout ────────────────────────────────────────────────────────────────
    def init_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 8))
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text=f"Dashboard — Welcome, {self.auth_service.get_current_user()}",
            font=("Segoe UI", 22, "bold"),
        ).grid(row=0, column=0, sticky="w")

        btn_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_frame.grid(row=0, column=1, sticky="e")

        # Bulk upload status badge (hidden until a bulk upload runs)
        self.bulk_status_lbl = ctk.CTkLabel(
            btn_frame, text="", font=("Segoe UI", 11, "bold"),
            text_color="#1f83d4",
        )
        self.bulk_status_lbl.pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame, text="＋ Add Files", command=self.browse_files,
            width=110, font=("Segoe UI", 13, "bold"),
        ).pack(side="left", padx=(0, 8))

        self.upload_all_btn = ctk.CTkButton(
            btn_frame, text="⬆ Upload All to S3", command=self.bulk_upload_all_to_s3,
            width=145, fg_color="#1f538d", hover_color="#14375e",
            font=("Segoe UI", 12, "bold"),
        )
        self.upload_all_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Refresh", command=self.refresh,
            width=80, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_frame, text="Logout", command=self.handle_logout,
            width=80, fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).pack(side="left")

        # ── Body: left file list + right detail pane ──────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 16))
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # Left sidebar — file list
        self._build_file_list_panel(body)

        # Right detail pane
        self._build_detail_panel(body)

    # ── Left sidebar ──────────────────────────────────────────────────────────
    def _build_file_list_panel(self, parent):
        sidebar = ctk.CTkFrame(parent, width=220, corner_radius=10)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(1, weight=1)
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            sidebar, text="Uploaded Files",
            font=("Segoe UI", 13, "bold"),
        ).grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))

        # Scrollable area for file cards
        self.file_list_scroll = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent", corner_radius=0
        )
        self.file_list_scroll.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        self.file_list_scroll.grid_columnconfigure(0, weight=1)

        # Placeholder when no files
        self.no_files_label = ctk.CTkLabel(
            self.file_list_scroll,
            text="No files yet.\nClick '＋ Add Files'.",
            text_color="gray", font=("Segoe UI", 11),
            wraplength=180, justify="center",
        )
        self.no_files_label.grid(row=0, column=0, pady=20)

    # ── Right detail panel ─────────────────────────────────────────────────────
    def _build_detail_panel(self, parent):
        self.detail_panel = ctk.CTkFrame(parent, corner_radius=10)
        self.detail_panel.grid(row=0, column=1, sticky="nsew")
        self.detail_panel.grid_columnconfigure(0, weight=1)
        self.detail_panel.grid_rowconfigure(2, weight=1)

        # Placeholder shown when nothing selected
        self.detail_placeholder = ctk.CTkLabel(
            self.detail_panel,
            text="← Select a file from the list to preview",
            font=("Segoe UI", 14),
            text_color="gray",
        )
        self.detail_placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # ── Detail: file name header ───────────────────────────────────────────
        self.detail_header = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        self.detail_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        self.detail_header.grid_columnconfigure(0, weight=1)

        self.detail_filename_lbl = ctk.CTkLabel(
            self.detail_header, text="", font=("Segoe UI", 15, "bold")
        )
        self.detail_filename_lbl.grid(row=0, column=0, sticky="w")

        self.detail_status_badge = ctk.CTkLabel(
            self.detail_header, text="", font=("Segoe UI", 11, "bold"),
            width=90, corner_radius=8,
        )
        self.detail_status_badge.grid(row=0, column=1, sticky="e")

        # ── Detail: controls (category + price + preview btn) ──────────────────
        self.detail_controls = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        self.detail_controls.grid(row=1, column=0, sticky="ew", padx=16, pady=6)

        ctk.CTkLabel(self.detail_controls, text="Category:").pack(side="left", padx=(0, 4))
        self.detail_category_cb = ctk.CTkOptionMenu(
            self.detail_controls, values=["- Select -"], width=140,
            command=self._on_category_change,
        )
        self.detail_category_cb.pack(side="left", padx=(0, 14))

        ctk.CTkLabel(self.detail_controls, text="Unit Price Δ:").pack(side="left", padx=(0, 4))
        self.detail_price_input = ctk.CTkEntry(
            self.detail_controls, placeholder_text="e.g. +5 or -2.5", width=110
        )
        self.detail_price_input.pack(side="left", padx=(0, 14))

        self.detail_preview_btn = ctk.CTkButton(
            self.detail_controls, text="Preview", command=self.generate_preview, width=90
        )
        self.detail_preview_btn.pack(side="left")

        # ── Detail: preview table ──────────────────────────────────────────────
        table_container = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        table_container.grid(row=2, column=0, sticky="nsew", padx=16, pady=(4, 8))
        table_container.grid_columnconfigure(0, weight=1)
        table_container.grid_rowconfigure(1, weight=1)

        # Operation summary label (shown after applying)
        self.op_summary_lbl = ctk.CTkLabel(
            table_container, text="", font=("Segoe UI", 11, "italic"), text_color="#1f83d4"
        )
        self.op_summary_lbl.grid(row=0, column=0, sticky="w", pady=(0, 4))

        self._build_treeview(table_container)

        # ── Detail: bottom actions ─────────────────────────────────────────────
        bottom = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=16, pady=(0, 14))
        bottom.grid_columnconfigure(3, weight=1)

        self.detail_apply_btn = ctk.CTkButton(
            bottom, text="Apply & Save", command=self.apply_changes,
            state="disabled", fg_color="#28a745", hover_color="#218838", width=120,
        )
        self.detail_apply_btn.grid(row=0, column=0, padx=(0, 10))

        self.detail_upload_btn = ctk.CTkButton(
            bottom, text="Upload To S3", command=self.upload_to_s3,
            state="disabled", width=120,
        )
        self.detail_upload_btn.grid(row=0, column=1)

        # Progress bar
        self.progress_container = ctk.CTkFrame(bottom, fg_color="transparent")
        self.progress_container.grid(row=0, column=2, padx=(16, 0))
        self.progress_container.grid_remove()

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_container, width=140, mode="determinate"
        )
        self.progress_bar.pack(side="left", padx=(0, 5))
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(self.progress_container, text="0%", width=40)
        self.progress_label.pack(side="left")

        self.detail_status_lbl = ctk.CTkLabel(
            bottom, text="Status: Ready", text_color="gray"
        )
        self.detail_status_lbl.grid(row=0, column=3, sticky="e")

        # Hide detail content until a file is selected
        self._hide_detail_content()

    def _build_treeview(self, parent):
        is_dark = ctk.get_appearance_mode() == "Dark"
        bg_color = "#2b2b2b" if is_dark else "#dbdbdb"
        text_color = "white" if is_dark else "black"
        selected_color = "#1f538d"

        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Treeview",
            background=bg_color, foreground=text_color,
            rowheight=28, fieldbackground=bg_color,
            bordercolor=bg_color, borderwidth=0,
            font=("Segoe UI", 10),
        )
        style.map("Treeview", background=[("selected", selected_color)])
        style.configure(
            "Treeview.Heading",
            background=selected_color, foreground="white",
            relief="flat", font=("Segoe UI", 10, "bold"), padding=4,
        )
        style.map("Treeview.Heading", background=[("active", "#14375e")])

        tree_frame = ctk.CTkFrame(parent, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)

        columns = ("Pizza Name", "Old Price", "New Price", "Difference")
        self.table = ttk.Treeview(tree_frame, columns=columns, show="headings")
        for col in columns:
            self.table.heading(col, text=col)
            self.table.column(col, width=150, anchor="center")

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

    # ── File list card builder ─────────────────────────────────────────────────
    def _rebuild_file_list(self):
        """Rebuild the left sidebar cards from self.file_entries."""
        for widget in self.file_list_scroll.winfo_children():
            widget.destroy()

        if not self.file_entries:
            self.no_files_label = ctk.CTkLabel(
                self.file_list_scroll,
                text="No files yet.\nClick '＋ Add Files'.",
                text_color="gray", font=("Segoe UI", 11),
                wraplength=180, justify="center",
            )
            self.no_files_label.grid(row=0, column=0, pady=20)
            return

        for idx, entry in enumerate(self.file_entries):
            self._create_file_card(idx, entry)

    def _create_file_card(self, idx: int, entry: FileEntry):
        is_selected = entry is self.selected_entry

        # Card frame
        card_bg = ("#1f538d" if is_selected else ("gray85", "gray25"))
        card = ctk.CTkFrame(
            self.file_list_scroll,
            fg_color=card_bg, corner_radius=8,
            cursor="hand2",
        )
        card.grid(row=idx, column=0, sticky="ew", pady=(0, 6))
        card.grid_columnconfigure(0, weight=1)

        # File icon + name
        name_lbl = ctk.CTkLabel(
            card,
            text=f"{entry.name}",
            font=("Segoe UI", 11, "bold" if is_selected else "normal"),
            text_color=("white" if is_selected else ("gray10", "gray90")),
            anchor="w", wraplength=170, justify="left",
        )
        name_lbl.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 2))

        # Status badge
        if entry.uploaded:
            badge_text, badge_color = "Uploaded", "#fcfcfc"
        elif entry.applied:
            badge_text, badge_color = "Applied", "#17a2b8"
        elif entry.loaded:
            badge_text, badge_color = "Loaded", "#fefefe"
        else:
            badge_text, badge_color = "⏳ Loading…", "gray"

        badge_lbl = ctk.CTkLabel(
            card, text=badge_text,
            font=("Segoe UI", 9, "bold"),
            text_color=badge_color,
            anchor="w",
        )
        badge_lbl.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 8))

        # Bind click on every sub-widget
        for widget in (card, name_lbl, badge_lbl):
            widget.bind("<Button-1>", lambda e, en=entry: self._select_file(en))

    # ── File selection ─────────────────────────────────────────────────────────
    def _select_file(self, entry: FileEntry):
        self.selected_entry = entry
        self._rebuild_file_list()
        self._show_detail_for(entry)

    def _show_detail_for(self, entry: FileEntry):
        """Populate the right detail panel with data from the given FileEntry."""
        self._show_detail_content()

        # Header
        self.detail_filename_lbl.configure(text=entry.name)
        self._update_status_badge(entry)

        # Categories
        if entry.loaded:
            cats = entry.excel_service.get_categories()
            if cats:
                self.detail_category_cb.configure(values=cats)
                if entry.category and entry.category in cats:
                    self.detail_category_cb.set(entry.category)
                else:
                    self.detail_category_cb.set(cats[0])
            else:
                self.detail_category_cb.configure(values=["- Select -"])
                self.detail_category_cb.set("- Select -")
        else:
            self.detail_category_cb.configure(values=["- Select -"])
            self.detail_category_cb.set("- Select -")

        # Price input
        self.detail_price_input.delete(0, "end")
        if entry.price_change is not None:
            self.detail_price_input.insert(0, str(entry.price_change))

        # Operation summary
        self._update_op_summary(entry)

        # Table
        self._populate_table(entry.preview_data)

        # Buttons
        if entry.applied:
            self.detail_apply_btn.configure(state="disabled")
            self.detail_upload_btn.configure(
                state="normal" if not entry.uploaded else "disabled"
            )
        else:
            self.detail_apply_btn.configure(
                state="normal" if entry.preview_data else "disabled"
            )
            self.detail_upload_btn.configure(state="disabled")

        self.detail_status_lbl.configure(text="Status: Ready")

    def _update_status_badge(self, entry: FileEntry):
        if entry.uploaded:
            self.detail_status_badge.configure(
                text="Uploaded ✔", fg_color="#28a745", text_color="white"
            )
        elif entry.applied:
            self.detail_status_badge.configure(
                text="Applied ✔", fg_color="#17a2b8", text_color="white"
            )
        elif entry.loaded:
            self.detail_status_badge.configure(
                text="Loaded", fg_color="#ffc107", text_color="black"
            )
        else:
            self.detail_status_badge.configure(
                text="Loading…", fg_color="gray", text_color="white"
            )

    def _update_op_summary(self, entry: FileEntry):
        if entry.applied and entry.category and entry.price_change is not None:
            sign = "+" if entry.price_change >= 0 else ""
            self.op_summary_lbl.configure(
                text=f"Operation applied — Category: {entry.category}  |  "
                     f"Price Change: {sign}{entry.price_change}  |  "
                     f"Rows: {len(entry.preview_data)}"
            )
        elif entry.preview_data and entry.category and entry.price_change is not None:
            sign = "+" if entry.price_change >= 0 else ""
            self.op_summary_lbl.configure(
                text=f"Preview — Category: {entry.category}  |  "
                     f"Price Change: {sign}{entry.price_change}  |  "
                     f"Rows: {len(entry.preview_data)}"
            )
        else:
            self.op_summary_lbl.configure(text="")

    def _show_detail_content(self):
        self.detail_placeholder.place_forget()
        self.detail_header.grid()
        self.detail_controls.grid()

    def _hide_detail_content(self):
        self.detail_placeholder.place(relx=0.5, rely=0.5, anchor="center")
        self.detail_header.grid_remove()
        self.detail_controls.grid_remove()
        self.op_summary_lbl.configure(text="")

    # ── Browse & Load ──────────────────────────────────────────────────────────
    def browse_files(self):
        paths = filedialog.askopenfilenames(
            title="Select Excel Files",
            filetypes=[("Excel Files", "*.xlsx")],
        )
        if not paths:
            return

        new_paths = [p for p in paths if not any(e.file_path == p for e in self.file_entries)]
        if not new_paths:
            messagebox.showinfo("Info", "All selected files are already in the list.")
            return

        for path in new_paths:
            entry = FileEntry(path)
            self.file_entries.append(entry)

        self._rebuild_file_list()

        # Load files in background
        for entry in [e for e in self.file_entries if not e.loaded and e.file_path in new_paths]:
            threading.Thread(
                target=self._threaded_load_file, args=(entry,), daemon=True
            ).start()

    def _threaded_load_file(self, entry: FileEntry):
        success = entry.excel_service.load_file(entry.file_path)
        self.after(0, self._on_file_loaded, entry, success)

    def _on_file_loaded(self, entry: FileEntry, success: bool):
        if success:
            entry.loaded = True
        else:
            messagebox.showerror("Error", f"Failed to load: {entry.name}")
        self._rebuild_file_list()
        # Refresh detail panel if this file is currently selected
        if self.selected_entry is entry:
            self._show_detail_for(entry)

    # ── Category change ────────────────────────────────────────────────────────
    def _on_category_change(self, value):
        """When user picks a different category, clear stale preview."""
        if self.selected_entry:
            self.selected_entry.category = value
            # Only clear preview if category differs from what was used
            self.selected_entry.preview_data = []
            self._populate_table([])
            self.detail_apply_btn.configure(state="disabled")
            self.op_summary_lbl.configure(text="")

    # ── Preview ────────────────────────────────────────────────────────────────
    def generate_preview(self):
        entry = self.selected_entry
        if not entry:
            return
        if not entry.loaded:
            messagebox.showwarning("Warning", "File is still loading.")
            return

        category = self.detail_category_cb.get()
        if not category or category == "- Select -":
            messagebox.showwarning("Warning", "Please select a category.")
            return

        price_change = self._parse_price(self.detail_price_input.get())
        if price_change is None:
            messagebox.showwarning("Validation Error", "Enter a valid number (e.g. 5, -2.5).")
            return

        preview_data = entry.excel_service.preview_changes(category, price_change)

        entry.category = category
        entry.price_change = price_change
        entry.preview_data = preview_data

        self._populate_table(preview_data)
        self._update_op_summary(entry)

        if not preview_data:
            messagebox.showinfo("Info", "No pizzas found for this category.")
            self.detail_apply_btn.configure(state="disabled")
            return

        self.detail_apply_btn.configure(state="normal")
        self.detail_status_lbl.configure(text="Status: Preview ready. Click Apply to save.")

    # ── Apply ──────────────────────────────────────────────────────────────────
    def apply_changes(self):
        entry = self.selected_entry
        if not entry or not entry.preview_data:
            return

        category = entry.category
        price_change = entry.price_change
        if category is None or price_change is None:
            return

        sign = "+" if price_change >= 0 else ""
        reply = messagebox.askyesno(
            "Confirm",
            f"Apply {sign}{price_change} to all '{category}' pizzas in '{entry.name}'?",
        )
        if not reply:
            return

        self._start_progress("Applying unit price…")
        self.detail_apply_btn.configure(state="disabled")

        threading.Thread(
            target=self._threaded_apply, args=(entry,), daemon=True
        ).start()

    def _threaded_apply(self, entry: FileEntry):
        success, rows_modified, new_path = entry.excel_service.apply_and_save(
            entry.category, entry.price_change
        )
        self.after(0, self._on_apply_complete, entry, success, rows_modified, new_path)

    def _on_apply_complete(self, entry: FileEntry, success: bool, rows_modified: int, new_path: str):
        self._complete_progress()
        if success:
            entry.applied = True
            entry.updated_file_path = new_path
            self.audit_service.log_change(
                self.auth_service.get_current_user(),
                entry.category, entry.price_change, rows_modified,
            )
            self.detail_status_lbl.configure(text="Status: Changes applied successfully.")
            self._update_status_badge(entry)
            self._update_op_summary(entry)
            self._rebuild_file_list()
            self.detail_apply_btn.configure(state="disabled")
            self.detail_upload_btn.configure(state="normal")
            messagebox.showinfo("Success", f"Updated {rows_modified} records in '{entry.name}'.")
        else:
            messagebox.showerror("Error", f"Failed to apply: {new_path}")
            self.detail_status_lbl.configure(text="Status: Error applying changes.")
            self.detail_apply_btn.configure(state="normal")

    # ── Single Upload ──────────────────────────────────────────────────────────
    def upload_to_s3(self):
        entry = self.selected_entry
        if not entry or not entry.updated_file_path:
            return

        self._start_progress("Uploading to S3…")
        self.detail_upload_btn.configure(state="disabled")

        threading.Thread(
            target=self._threaded_upload, args=(entry, False), daemon=True
        ).start()

    def _threaded_upload(self, entry: FileEntry, is_bulk: bool):
        success, message = self.s3_service.upload_file(entry.updated_file_path)
        self.after(0, self._on_upload_complete, entry, success, message, is_bulk)

    def _on_upload_complete(self, entry: FileEntry, success: bool, message: str, is_bulk: bool = False):
        if success:
            entry.uploaded = True
            self._update_status_badge(entry)
            self._rebuild_file_list()
            # Refresh detail panel upload button if this file is selected
            if self.selected_entry is entry:
                self.detail_upload_btn.configure(state="disabled")
                self.detail_status_lbl.configure(text="Status: Uploaded to S3.")
        else:
            if self.selected_entry is entry:
                self.detail_status_lbl.configure(text="Status: Upload failed.")
                self.detail_upload_btn.configure(state="normal")

        if is_bulk:
            self._bulk_done += 1
            if not success:
                self._bulk_failed += 1
            self._update_bulk_status_label()
            # All done
            if self._bulk_done >= self._bulk_total:
                self._on_bulk_upload_finished()
        else:
            self._complete_progress()
            if success:
                messagebox.showinfo("Success", f"'{entry.name}' uploaded to S3.")
            else:
                messagebox.showerror("Error", f"Upload failed.\n{message}")

    # ── Bulk Upload ────────────────────────────────────────────────────────────
    def bulk_upload_all_to_s3(self):
        """Upload all applied-but-not-yet-uploaded files in parallel threads."""
        pending = [
            e for e in self.file_entries
            if e.applied and not e.uploaded and e.updated_file_path
        ]

        if not pending:
            messagebox.showinfo(
                "Nothing to Upload",
                "No applied files are ready for upload.\n"
                "Apply price changes first, then use Upload All."
            )
            return

        count = len(pending)
        reply = messagebox.askyesno(
            "Upload All to S3",
            f"Upload {count} file(s) to S3 simultaneously?\n\n"
            + "\n".join(f"  • {e.name}" for e in pending),
        )
        if not reply:
            return

        # Initialise counters
        self._bulk_total = count
        self._bulk_done = 0
        self._bulk_failed = 0
        self.bulk_status_lbl.configure(
            text=f"⬆ Uploading 0 / {count}…", text_color="#1f83d4"
        )
        self.upload_all_btn.configure(state="disabled")

        # Spawn one thread per file — true parallel S3 uploads
        for entry in pending:
            threading.Thread(
                target=self._threaded_upload, args=(entry, True), daemon=True
            ).start()

    def _update_bulk_status_label(self):
        remaining = self._bulk_total - self._bulk_done
        if remaining > 0:
            self.bulk_status_lbl.configure(
                text=f"⬆ Uploading {self._bulk_done} / {self._bulk_total}…",
                text_color="#1f83d4",
            )
        # Final update handled in _on_bulk_upload_finished

    def _on_bulk_upload_finished(self):
        success_count = self._bulk_total - self._bulk_failed
        self.upload_all_btn.configure(state="normal")

        if self._bulk_failed == 0:
            self.bulk_status_lbl.configure(
                text=f"✔ {success_count} / {self._bulk_total} uploaded",
                text_color="#28a745",
            )
            messagebox.showinfo(
                "Bulk Upload Complete",
                f"All {success_count} file(s) uploaded to S3 successfully.",
            )
        else:
            self.bulk_status_lbl.configure(
                text=f"⚠ {success_count} ok, {self._bulk_failed} failed",
                text_color="#dc3545",
            )
            messagebox.showwarning(
                "Bulk Upload Partial",
                f"{success_count} file(s) uploaded.\n"
                f"{self._bulk_failed} file(s) failed — check individual files.",
            )
        # Auto-clear label after 6 seconds
        self.after(6000, lambda: self.bulk_status_lbl.configure(text=""))

    # ── Helpers ────────────────────────────────────────────────────────────────
    def _populate_table(self, preview_data: list):
        for item in self.table.get_children():
            self.table.delete(item)
        for data in preview_data:
            diff_str = f"+{data['difference']}" if data["difference"] > 0 else str(data["difference"])
            self.table.insert(
                "", "end",
                values=(
                    str(data["pizza_name"]),
                    f"{data['old_price']:.2f}",
                    f"{data['new_price']:.2f}",
                    diff_str,
                ),
            )

    def _parse_price(self, text: str):
        try:
            return float(text.strip())
        except (ValueError, AttributeError):
            return None

    # ── Progress bar ───────────────────────────────────────────────────────────
    def _start_progress(self, status_text: str):
        self.progress_container.grid()
        self.detail_status_lbl.configure(text=f"Status: {status_text}")
        self._progress_value = 0
        self.progress_bar.set(0)
        self.progress_label.configure(text="0%")
        self._is_processing = True
        self._animate_progress()

    def _animate_progress(self):
        if self._is_processing and self._progress_value < 90:
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

    # ── Other ──────────────────────────────────────────────────────────────────
    def handle_logout(self):
        self.auth_service.logout()
        self.on_logout()

    def refresh(self):
        self.audit_service = AuditService()
        self.s3_service = S3Service()
        self.detail_status_lbl.configure(text="Status: Refreshed")
        self.master.update()
