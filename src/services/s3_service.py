import os
import mimetypes
from pathlib import Path
from typing import Optional
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class S3Service:
    """Service class for uploading files to Amazon S3 with MIME type detection."""
    
    def __init__(self):
        """Initialize S3 client with credentials from environment variables."""
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.aws_region = os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            raise ValueError(
                "Missing required AWS credentials. Please set AWS_ACCESS_KEY_ID, "
                "AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET_NAME environment variables."
            )
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
    
    def get_mime_type(self, file_name: str, file_content: Optional[bytes] = None) -> str:
        """
        Determine MIME type from file extension or content.
        
        Args:
            file_name: Name of the file
            file_content: Optional file content bytes for content-based detection
            
        Returns:
            MIME type string (e.g., 'image/jpeg', 'application/pdf')
        """
        # First, try to detect from file extension
        mime_type, _ = mimetypes.guess_type(file_name)
        
        if mime_type:
            return mime_type
        
        # If extension-based detection fails, try content-based detection
        if file_content:
            try:
                import magic
                mime_type = magic.from_buffer(file_content, mime=True)
                return mime_type
            except ImportError:
                pass  # python-magic not installed, fall through to default
        
        # Default to application/octet-stream if detection fails
        return 'application/octet-stream'
    
    def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        folder: Optional[str] = None,
        content_type: Optional[str] = None
    ) -> str:
        """
        Upload a file to S3 and return the full URL.
        
        Args:
            file_content: File content as bytes
            file_name: Original file name
            folder: Optional folder path in S3 (e.g., 'contracts', 'documents')
            content_type: Optional MIME type. If not provided, will be auto-detected.
            
        Returns:
            Full URL of the uploaded file
        """
        # Generate unique file name to avoid conflicts
        file_ext = Path(file_name).suffix
        unique_file_name = f"{uuid4()}{file_ext}"
        
        # Determine MIME type if not provided
        if not content_type:
            content_type = self.get_mime_type(file_name, file_content)
        
        # Construct S3 key (path)
        if folder:
            s3_key = f"{folder}/{unique_file_name}"
        else:
            s3_key = unique_file_name
        
        try:
            # Upload file to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=file_content,
                ContentType=content_type,
                ACL='private'  # Change to 'public-read' if files should be publicly accessible
            )
            
            # Construct and return full URL
            file_url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            
            return file_url
            
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    def delete_file(self, file_url: str) -> bool:
        """
        Delete a file from S3.
        
        Args:
            file_url: Full URL of the file to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Extract S3 key from URL
            # URL format: https://bucket-name.s3.region.amazonaws.com/key
            if f"https://{self.bucket_name}.s3" in file_url:
                s3_key = file_url.split(f".s3.{self.aws_region}.amazonaws.com/")[-1]
            else:
                # Try to extract key from other URL formats
                s3_key = file_url.split(f"{self.bucket_name}/")[-1] if f"{self.bucket_name}/" in file_url else file_url
            
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError as e:
            print(f"Failed to delete file from S3: {str(e)}")
            return False
