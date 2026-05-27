import boto3
import os

class S3Service:
    def __init__(self):
        # Initializes the client using standard environment variables if present
        # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
        self.s3 = boto3.client('s3')

    def upload_file(self, file_path: str, bucket_name: str) -> bool:
        if not os.path.exists(file_path):
            return False

        file_name = os.path.basename(file_path)
        try:
            self.s3.upload_file(file_path, bucket_name, file_name)
            return True
        except Exception as e:
            print(f"Failed to upload to S3: {e}")
            return False
