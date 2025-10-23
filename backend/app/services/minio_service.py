from minio import Minio
from minio.error import S3Error
from app.core.config import settings
from typing import Optional
from datetime import timedelta
import os

class MinIOService:
    """Service class for MinIO operations"""
    
    def __init__(self):
        """Initialize MinIO client with settings"""
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE
        )
        self.bucket = settings.MINIO_MEDIA_BUCKET
        self._ensure_bucket()
    
    def _ensure_bucket(self):
        """Create bucket if it doesn't exist"""
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)
            print(f"✅ Created MinIO bucket: {self.bucket}")
    
    def upload_file(self, file_path: str, object_name: str, content_type: str = None) -> str:
        """Upload file to MinIO and return object name"""
        try:
            file_stat = os.stat(file_path)
            with open(file_path, "rb") as file_data:
                self.client.put_object(
                    self.bucket,
                    object_name,
                    file_data,
                    file_stat.st_size,
                    content_type=content_type
                )
            print(f"✅ Uploaded to MinIO: {self.bucket}/{object_name}")
            return object_name
        except S3Error as e:
            raise Exception(f"MinIO upload failed: {e}")
    
    def get_presigned_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        """Get presigned URL for file access"""
        try:
            # Convert seconds to timedelta object
            expires = timedelta(seconds=expires_seconds)
            return self.client.presigned_get_object(
                self.bucket, 
                object_name, 
                expires
            )
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {e}")
    
    def file_exists(self, object_name: str) -> bool:
        """Check if file exists in MinIO"""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

    def download_to_file(self, object_name: str, destination_path: str) -> str:
        """Download an object from MinIO to a local file and return the path"""
        from shutil import copyfileobj
        try:
            response = self.client.get_object(self.bucket, object_name)
            try:
                with open(destination_path, "wb") as file_data:
                    copyfileobj(response, file_data)
                print(f"✅ Downloaded from MinIO: {self.bucket}/{object_name} -> {destination_path}")
                return destination_path
            finally:
                response.close()
                response.release_conn()
        except S3Error as e:
            raise Exception(f"MinIO download failed: {e}")
