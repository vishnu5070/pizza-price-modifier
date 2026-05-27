import os
import json
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse
from requests.exceptions import ConnectionError as RequestsConnectionError
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import requests
from dotenv import load_dotenv

# Load .env from the project root (pizza-price-modifier folder)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


def _get_env_presign_api_url() -> Optional[str]:
    """Read PRESIGN_API_URL from environment (loaded from .env)."""
    url = os.environ.get("PRESIGN_API_URL", "").strip()
    return url if url else None


def _get_env_bucket() -> Optional[str]:
    """Read S3_BUCKET_NAME from environment (loaded from .env)."""
    bucket = os.environ.get("S3_BUCKET_NAME", "").strip()
    return bucket if bucket else None


class S3Service:
    def __init__(self):
        self.client = boto3.client("s3")

    def _normalize_presign_api_url(self, presign_api_url: str) -> str:
        """Accept a full invoke URL or a stage-only URL and append the route when missing."""
        route_path = "/gets3presigneduplodurl"
        parsed = urlparse(presign_api_url.strip())
        if not parsed.scheme or not parsed.netloc:
            raise ValueError("presign API URL must start with https:// and include the API Gateway host")

        path = parsed.path.rstrip("/")
        if not path or path == "" or path in {"/dev", "/prod", "/stage"}:
            path = f"{path}{route_path}"
        elif not path.endswith(route_path):
            # If the user pasted only the stage/base invoke URL, add the expected route.
            if path.count("/") <= 2:
                path = f"{path}{route_path}"

        return urlunparse((parsed.scheme, parsed.netloc, path, parsed.params, parsed.query, parsed.fragment))

    def _parse_presign_response(self, resp: requests.Response) -> Tuple[Optional[str], str]:
        """Return (presigned_url or None, diagnostic_message)."""
        try:
            data = resp.json()
        except ValueError:
            # Non-JSON body
            body_text = resp.text or ""
            return None, f"Non-JSON response from presign API: {body_text}"

        # Common API Gateway proxy pattern: {"statusCode": 200, "body": "{...}"}
        if isinstance(data, dict):
            if "presignedurl" in data and isinstance(data["presignedurl"], str):
                return data["presignedurl"], "OK"

            # body may be a JSON string
            body = data.get("body")
            if isinstance(body, str):
                try:
                    inner = json.loads(body)
                    if isinstance(inner, dict) and "presignedurl" in inner:
                        return inner["presignedurl"], "OK"
                except ValueError:
                    pass

            # sometimes API returns wrapped under other keys — try a shallow search
            for v in data.values():
                if isinstance(v, dict) and "presignedurl" in v:
                    return v["presignedurl"], "OK"

            return None, f"presignedurl not found in response JSON: {json.dumps(data)[:500]}"

        return None, "Unexpected presign API response format"

    def _upload_via_presigned(self, file_path: str, presign_api_url: Optional[str] = None, presigned_url: Optional[str] = None) -> Tuple[bool, str]:
        """If presigned_url provided, PUT directly. Otherwise POST to presign_api_url to obtain URL then PUT."""
        file_name = os.path.basename(file_path)

        # If caller provided presigned URL directly, use it
        if presigned_url:
            try:
                with open(file_path, "rb") as fh:
                    put_resp = requests.put(presigned_url, data=fh, timeout=120)
                if put_resp.status_code in (200, 201):
                    return True, "OK"
                return False, f"S3 PUT failed: {put_resp.status_code} {put_resp.text}"
            except requests.RequestException as exc:
                return False, f"S3 PUT request failed: {exc}"
            except OSError as exc:
                return False, f"Failed to read file: {exc}"

        # Otherwise call presign API to get one
        try:
            print(f"[S3Service] POSTing to presign API: {presign_api_url}")
            resp = requests.post(presign_api_url, json={"file_name": file_name}, timeout=20)
        except RequestsConnectionError as exc:
            return False, (
                "Failed to call presign API: cannot resolve or reach the backend host. "
                "Check the API ID, region, stage, and that the URL is the full invoke URL "
                f"for POST /gets3presigneduplodurl. Details: {exc}"
            )
        except requests.RequestException as exc:
            return False, f"Failed to call presign API: {exc}"

        if resp.status_code >= 400:
            return False, f"Presign API returned status {resp.status_code}: {resp.text}"

        presigned_url, diag = self._parse_presign_response(resp)
        if not presigned_url:
            return False, diag

        print(f"[S3Service] Got presigned URL, uploading file...")
        try:
            with open(file_path, "rb") as fh:
                put_resp = requests.put(presigned_url, data=fh, timeout=120)
            if put_resp.status_code in (200, 201):
                return True, "OK"
            else:
                return False, f"S3 PUT failed: {put_resp.status_code} {put_resp.text}"
        except requests.RequestException as exc:
            return False, f"S3 PUT request failed: {exc}"
        except OSError as exc:
            return False, f"Failed to read file: {exc}"

    def upload_file(self, file_path: str, bucket_name: Optional[str] = None, presign_api_url: Optional[str] = None, presigned_url: Optional[str] = None) -> Tuple[bool, str]:
        """Upload file via presign API (default) or direct boto3. Returns (success, message)."""
        if not file_path or not os.path.exists(file_path):
            return False, "file not found"

        # ── Priority 1: Use presign API URL from .env if not explicitly passed ──
        if not presign_api_url and not presigned_url:
            presign_api_url = _get_env_presign_api_url()

        # ── Priority 2: Fallback bucket from .env ──
        if not bucket_name:
            bucket_name = _get_env_bucket()

        if presign_api_url:
            presign_api_url = presign_api_url.strip()
            if 'your-api-gateway-endpoint-here' in presign_api_url or 'example' in presign_api_url.lower():
                return False, "presign API URL is still a placeholder; update PRESIGN_API_URL in .env"
            try:
                presign_api_url = self._normalize_presign_api_url(presign_api_url)
            except ValueError as exc:
                return False, f"Invalid presign API URL: {exc}"

        print(f"[S3Service] upload_file: file={file_path}, presign_api_url={'set' if presign_api_url else 'none'}, presigned_url={'set' if presigned_url else 'none'}, bucket={'set' if bucket_name else 'none'}")

        # Use presigned URL directly if provided
        if presigned_url:
            return self._upload_via_presigned(file_path, presigned_url=presigned_url)

        # Use presign API to get a fresh presigned URL
        if presign_api_url:
            return self._upload_via_presigned(file_path, presign_api_url=presign_api_url)

        # Last resort: direct boto3 upload
        if not bucket_name:
            return False, "No upload method available: set PRESIGN_API_URL in .env or provide a bucket name"

        file_name = os.path.basename(file_path)
        try:
            self.client.upload_file(file_path, bucket_name, file_name)
            return True, "OK"
        except (BotoCoreError, ClientError, OSError) as exc:
            return False, f"Failed to upload {file_name} via boto3: {exc}"