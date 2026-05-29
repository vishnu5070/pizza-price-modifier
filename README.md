# Pizza Pricing Tool

A professional desktop application built with **Python** and **CustomTkinter** for managing and updating pizza sales data across multiple Excel files. Authorized users can log in, upload one or more Excel files, apply category-wide unit price adjustments per file, preview changes before committing, save updated files, and upload them directly to AWS S3 using a presigned URL API.

---

## Features

- **Secure Authentication** — Local JSON-backed user login with bcrypt-hashed passwords. Supports user registration.
- **Multi-File Upload** — Browse and load multiple `.xlsx` files at once. Each file is managed independently.
- **Per-File Detail Preview** — Click any file in the sidebar to view its category, price change, and a full preview table showing Old Price, New Price, and Difference.
- **Category-Based Price Updates** — Apply a unit price adjustment to all pizzas in a selected category within a specific file.
- **Apply & Save** — Saves the modified file as `<original_name>_updated.xlsx` under `data/updated_excels/`.
- **Single File Upload** — Upload the updated file for any selected file individually to S3.
- **Bulk Upload All to S3** — Upload all applied (but not yet uploaded) files to S3 simultaneously using parallel threads.
- **Live Upload Progress** — Header shows a real-time counter (`⬆ Uploading 2 / 5…`) during bulk uploads.
- **File Status Badges** — Each file card shows its current state: `⏳ Loading`, `● Loaded`, `✔ Applied`, `✔ Uploaded`.
- **Operation Summary** — After applying or previewing, a summary line shows: `Category | Price Change | Rows affected`.
- **Audit Logging** — Every applied price change is appended to `data/audit_logs.jsonl` with username, category, change value, rows modified, and timestamp.
- **Threaded Operations** — All heavy operations (file loading, apply & save, S3 upload) run in background threads so the UI never freezes.
- **Animated Progress Bar** — Smooth animated progress bar with percentage label during all long-running operations.
- **Refresh** — Reinitializes all services to pick up any `.env` config changes without restarting the app.

---

## Screenshots / Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  Dashboard — Welcome, admin       [⬆ Upload All] [Refresh] [Logout] │
├────────────────┬─────────────────────────────────────────────────┤
│  Uploaded Files│  📄 pizza_menu_A.xlsx          [Applied ✔]      │
│                │  Category: [Classic ▼]  Price Δ: [+5]  [Preview]│
│  📄 file_A     │ ─────────────────────────────────────────────── │
│  ✔ Applied     │  Operation applied — Category: Classic | +5 | 12│
│                │ ┌──────────┬───────────┬───────────┬──────────┐ │
│  📄 file_B     │ │Pizza Name│ Old Price │ New Price │Difference│ │
│  ● Loaded      │ │ Margherita│  10.00   │  15.00   │   +5     │ │
│                │ └──────────┴───────────┴───────────┴──────────┘ │
│  📄 file_C     │                                                  │
│  ✔ Uploaded    │  [Apply & Save]  [Upload To S3]      Status: Ready│
└────────────────┴─────────────────────────────────────────────────┘
```

---

## Installation

### Prerequisites
- Python **3.10** or higher
- pip

### Steps

1. Clone this repository or extract the project files.

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your S3 presigned URL endpoint in the `.env` file:
   ```env
   PRESIGN_API_URL=https://your-api-gateway-id.execute-api.region.amazonaws.com/stage
   ```

4. Run the application:
   ```bash
   python main.py
   ```

> On the first run, `data/credentials.json` is auto-created with the default admin account, and `data/updated_excels/` is created when the first file is saved.

---

## Default Credentials

| Field    | Value      |
|----------|------------|
| Username | `admin`    |
| Password | `admin123` |

You can register additional accounts from the **Register** screen on the login page.

---

## AWS S3 Configuration

This app uses a **presigned URL API** (API Gateway + Lambda) to upload files to S3. No AWS credentials need to be configured locally.

### `.env` file (project root)

```env
PRESIGN_API_URL=https://<api-id>.execute-api.<region>.amazonaws.com/<stage>
S3_BUCKET_NAME=your-bucket-name
```

### How It Works

1. The app POSTs `{ "file_name": "pizza_menu_updated.xlsx" }` to your Lambda endpoint.
2. Lambda generates a fresh **presigned PUT URL** (1-hour expiry recommended).
3. The app uploads the file directly to S3 using that URL — no AWS keys needed on the client.

### Bulk Upload

When using **"⬆ Upload All to S3"**, each file gets its **own fresh presigned URL** independently — one thread per file, all running simultaneously.

---

## How to Use

### Single File Workflow
1. **Log in** with your credentials.
2. Click **＋ Add Files** → select one or more `.xlsx` files.
3. Click a **file card** in the left sidebar to open its detail panel.
4. Select a **Category** and enter a **Unit Price change** (e.g. `+5`, `-2.5`).
5. Click **Preview** → review the price changes in the table.
6. Click **Apply & Save** → confirm and save the updated file.
7. Click **Upload To S3** → upload that specific file to S3.

### Bulk Upload Workflow
1. Apply price changes to **multiple files** (steps 1–6 above, per file).
2. Click **⬆ Upload All to S3** in the header.
3. A confirmation dialog lists all pending files.
4. All files upload to S3 **simultaneously** in parallel threads.
5. The header badge updates live: `⬆ Uploading 2 / 5…` → `✔ 5 / 5 uploaded`.

---

## Excel File Format

Your `.xlsx` file should contain the following columns (names are auto-normalized):

| Column            | Required | Description                        |
|-------------------|----------|------------------------------------|
| `pizza_name`      | ✅ Yes   | Name of the pizza item             |
| `pizza_category`  | ✅ Yes   | Category used for filtering        |
| `unit_price`      | ✅ Yes   | Price to be modified               |
| `quantity`        | Optional | Used to recalculate `total_price`  |
| `total_price`     | Optional | Auto-recalculated if present       |

> Column names are case-insensitive and space-tolerant — e.g. `Pizza Category` and `pizza_category` both work.

---

## Project Structure

```
pizza-price-modifier/
├── main.py                     # App entry point, window & navigation management
├── .env                        # Environment config (PRESIGN_API_URL, S3_BUCKET_NAME)
├── requirements.txt            # Python dependencies
│
├── ui/
│   ├── dashboard_window.py     # Main dashboard — multi-file list + per-file detail panel
│   ├── login_window.py         # Login screen
│   └── register_window.py      # User registration screen
│
├── services/
│   ├── excel_service.py        # Excel load, preview, apply & save logic (pandas)
│   ├── auth_service.py         # Local JSON authentication with bcrypt
│   ├── audit_service.py        # Appends audit records to JSONL log file
│   └── s3_service.py           # Presigned URL upload to AWS S3
│
└── data/
    ├── credentials.json        # Local user store (bcrypt hashed passwords)
    ├── audit_logs.jsonl        # Append-only audit log (one JSON record per line)
    └── updated_excels/         # Saved modified Excel files (<name>_updated.xlsx)
```

---

## Dependencies

| Package           | Purpose                                      |
|-------------------|----------------------------------------------|
| `customtkinter`   | Modern themed desktop UI framework           |
| `pandas`          | Excel file reading and DataFrame manipulation|
| `openpyxl`        | Pandas backend for `.xlsx` read/write        |
| `bcrypt`          | Secure password hashing and verification     |
| `requests`        | Presign API calls and S3 presigned PUT upload|
| `python-dotenv`   | Load `.env` config into environment variables|
| `boto3`           | AWS SDK (fallback direct S3 upload)          |

---

## Audit Log Format

Each price change is logged to `data/audit_logs.jsonl` as a single JSON line:

```json
{"username": "admin", "category": "Classic", "change_value": 5.0, "rows_modified": 12, "timestamp": "2026-05-29T05:10:00Z"}
```

---

## Threading Model

| Operation         | Threading           | UI Behaviour                        |
|-------------------|---------------------|-------------------------------------|
| File loading      | One thread per file | Parallel load; badge updates on done |
| Apply & Save      | Background thread   | Progress bar animates during save   |
| Single S3 upload  | Background thread   | Progress bar animates during upload |
| Bulk S3 upload    | One thread per file | All upload simultaneously; live counter in header |
