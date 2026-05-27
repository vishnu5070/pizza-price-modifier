# Pizza Pricing Tool

A professional desktop application built with Python and PyQt6 for managing and updating pizza sales data. It allows authorized users to securely log in, upload an Excel file, apply category-wide price adjustments, preview changes, save the updated file, and upload it directly to an AWS S3 bucket. Account credentials are stored locally in a JSON file, while audit events are logged to a local SQLite database.

## Features
- **Secure Authentication:** Local JSON-backed user login with hashed passwords.
- **Excel Processing:** Reads and updates `.xlsx` files using Pandas.
- **Category-Based Updates:** Modifies prices for all pizzas in a chosen category.
- **Preview Screen:** Displays Old Price, New Price, and Differences before committing.
- **Audit Logging:** Logs user, category, applied change, and timestamp to the SQLite DB.
- **AWS S3 Integration:** Uploads the modified Excel files to a designated S3 bucket.

## Installation

### Prerequisites
- Python 3.8 or higher.
- AWS Credentials configured on your machine (e.g. via `aws configure` or Environment Variables).

### Steps
1. Clone this repository or extract the files.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   python main.py
   ```
   *Note: On the first run, the database (`data/pizza_tool.db`) is automatically initialized, the local credentials file (`data/credentials.json`) is seeded with an admin user, and updated spreadsheets are saved under `data/updated_excels/`.*

## Default Credentials
- **Username:** `admin`
- **Password:** `admin123`

## AWS Configuration
- To enable the S3 upload feature, make sure the environment has AWS credentials configured. You can use standard AWS environment variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`

Alternatively, you can use a REST API + Lambda presigned-URL flow. In the app click **Upload To S3**, choose the backend presigned-URL option and provide the API endpoint if it is not already set in `data/config.json`. The app will POST `{"file_name": "..."}` to that backend, receive a fresh 1-hour presigned URL, and then upload the file directly to S3.

### Presigned Upload Config
- `data/config.json` can store your backend endpoint:
   - `presign_api_url`: the POST endpoint that returns a fresh presigned URL
   - `expires_in`: recommended `3600` for a 1-hour URL on the backend

## Architecture & Structure
- **ui/**: Contains PyQt6 components for Login, Dashboard, and styling.
- **services/**: Contains the core business logic (Authentication, Excel, Audit, S3).
- **db/**: Contains SQLite setup and connection handling for audit logging.
- **data/**: Default location for the SQLite database, local credentials file, and test data.
