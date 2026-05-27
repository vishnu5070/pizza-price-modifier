import os
import json
from typing import Optional, Tuple

import boto3
from botocore.exceptions import BotoCoreError, ClientError
import requests


class S3Service:
    def __init__(self):
        self.client = boto3.client("s3")

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

            # sometimes API returns wrapped under other keys
            # try a shallow search
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
                    put_resp = requests.put(presigned_url, data=fh, headers={"Content-Type": "application/octet-stream"}, timeout=120)
                if put_resp.status_code in (200, 201):
                    return True, "OK"
                return False, f"S3 PUT failed: {put_resp.status_code} {put_resp.text}"
            except requests.RequestException as exc:
                return False, f"S3 PUT request failed: {exc}"
            except OSError as exc:
                return False, f"Failed to read file: {exc}"

        # Otherwise call presign API to get one
        try:
            resp = requests.post(presign_api_url, json={"file_name": file_name}, timeout=20)
        except requests.RequestException as exc:
            return False, f"Failed to call presign API: {exc}"

        if resp.status_code >= 400:
            return False, f"Presign API returned status {resp.status_code}: {resp.text}"

        presigned_url, diag = self._parse_presign_response(resp)
        if not presigned_url:
            return False, diag

        # Basic validation: URL should contain required query params
        if "X-Amz-" not in presigned_url and "Signature" not in presigned_url and "Expires" not in presigned_url:
            # still attempt, but warn
            print("Warning: presigned URL looks unusual")

        try:
            with open(file_path, "rb") as fh:
                put_resp = requests.put(presigned_url, data=fh, headers={"Content-Type": "application/octet-stream"}, timeout=120)
            if put_resp.status_code in (200, 201):
                return True, "OK"
            else:
                return False, f"S3 PUT failed: {put_resp.status_code} {put_resp.text}"
        except requests.RequestException as exc:
            return False, f"S3 PUT request failed: {exc}"
        except OSError as exc:
            return False, f"Failed to read file: {exc}"

    def upload_file(self, file_path: str, bucket_name: Optional[str] = None, presign_api_url: Optional[str] = None, presigned_url: Optional[str] = None) -> Tuple[bool, str]:
        """Upload file either via presign API or direct boto3. Returns (success, message)."""
        if not file_path or not os.path.exists(file_path):
            return False, "file not found"

        if presign_api_url:
            presign_api_url = presign_api_url.strip()
            if 'your-api-gateway-endpoint-here' in presign_api_url or 'example' in presign_api_url.lower():
                return False, "presign API URL is still a placeholder; set a real backend endpoint in data/config.json or enter it when prompted"

        # Diagnostic log of inputs
        try:
            print(f"S3Service.upload_file called with file_path={file_path}, bucket_name={bucket_name}, presign_api_url={'set' if presign_api_url else 'none'}, presigned_url={'set' if presigned_url else 'none'}")
        except Exception:
            pass

        # If caller provided a presigned URL directly, use it
        if presigned_url:
            return self._upload_via_presigned(file_path, presigned_url=presigned_url)

        if presign_api_url:
            return self._upload_via_presigned(file_path, presign_api_url=presign_api_url)

        # If no inputs provided, try to read saved presigned URL from data/config.json
        if not bucket_name and not presign_api_url and not presigned_url:
            try:
                cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'config.json')
                if os.path.exists(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as cf:
                        cfg = json.load(cf)
                        saved = cfg.get('presigned_url')
                        expires_at = int(cfg.get('expires_at', 0))
                        if saved and int(__import__('time').time()) < expires_at:
                            return self._upload_via_presigned(file_path, presigned_url=saved)
            except Exception:
                pass

        if not bucket_name:
            return False, f"bucket name required for direct upload (presign_api_url set: {bool(presign_api_url)}, presigned_url set: {bool(presigned_url)})"

        file_name = os.path.basename(file_path)
        try:
            self.client.upload_file(file_path, bucket_name, file_name)
            return True, "OK"
        except (BotoCoreError, ClientError, OSError) as exc:
            return False, f"Failed to upload {file_name} via boto3: {exc}"