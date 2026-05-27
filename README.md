# Pizza Pricing Tool

A professional desktop application built with Python and PyQt6 for managing and updating pizza sales data. It allows authorized users to securely log in, upload an Excel file, apply category-wide price adjustments, preview changes, save the updated file, and upload it directly to an AWS S3 bucket. All modifications are logged to a local SQLite database for auditing.

## Features
- **Secure Authentication:** SQLite-backed user login with hashed passwords.
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
   *Note: On the first run, the database (`data/pizza_tool.db`) is automatically initialized and an admin user is seeded.*

## Default Credentials
- **Username:** `admin`
- **Password:** `admin123`

## AWS Configuration
To enable the S3 upload feature, make sure the environment has AWS credentials configured. You can use standard AWS environment variables:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`

## Architecture & Structure
- **ui/**: Contains PyQt6 components for Login, Dashboard, and styling.
- **services/**: Contains the core business logic (Authentication, Excel, Audit, S3).
- **db/**: Contains SQLite setup and connection handling.
- **data/**: Default location for the SQLite database and test data.
