import os
import mimetypes
from pathlib import Path
from typing import Optional, List
from uuid import uuid4

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()


class S3Service:
    """Service class for uploading files to Amazon S3 with MIME type detection and validation."""
    
    # Common allowed MIME types for file uploads
    ALLOWED_MIME_TYPES = {
        # Documents
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # .docx
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-powerpoint',
        'application/vnd.openxmlformats-officedocument.presentationml.presentation',  # .pptx
        'text/plain',
        'text/csv',
        # Images
        'image/jpeg',
        'image/jpg',
        'image/png',
        'image/gif',
        'image/webp',
        'image/bmp',
        'image/svg+xml',
        # Archives
        'application/zip',
        'application/x-zip-compressed',
        'application/x-rar-compressed',
        'application/x-tar',
        'application/gzip',
    }
    
    def __init__(self):
        """Initialize S3 client with credentials from environment variables."""
        self.aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        # Support both AWS_REGION and AWS_BUCKET_REGION for backward compatibility
        self.aws_region = os.getenv("AWS_BUCKET_REGION") or os.getenv("AWS_REGION", "us-east-1")
        self.bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        
        if not all([self.aws_access_key_id, self.aws_secret_access_key, self.bucket_name]):
            raise ValueError(
                "Missing required AWS credentials. Please set AWS_ACCESS_KEY_ID, "
                "AWS_SECRET_ACCESS_KEY, and AWS_S3_BUCKET_NAME environment variables."
            )
        
        # Load allowed MIME types from environment if provided (comma-separated)
        allowed_mime_types_env = os.getenv("ALLOWED_MIME_TYPES")
        if allowed_mime_types_env:
            self.allowed_mime_types = set(mt.strip() for mt in allowed_mime_types_env.split(","))
        else:
            self.allowed_mime_types = self.ALLOWED_MIME_TYPES
        
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            region_name=self.aws_region
        )
    
    def validate_mime_type(self, mime_type: str) -> bool:
        """
        Validate if a MIME type is allowed.
        
        Args:
            mime_type: MIME type to validate
            
        Returns:
            True if MIME type is allowed, False otherwise
        """
        return mime_type.lower() in (mt.lower() for mt in self.allowed_mime_types)
    
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
        content_type: Optional[str] = None,
        validate_mime: bool = True
    ) -> str:
        """
        Upload a file to S3 and return the full URL.
        
        Args:
            file_content: File content as bytes
            file_name: Original file name
            folder: Optional folder path in S3 (e.g., 'contracts', 'documents')
            content_type: Optional MIME type. If not provided, will be auto-detected.
            validate_mime: Whether to validate MIME type against allowed types (default: True)
            
        Returns:
            Full URL of the uploaded file
            
        Raises:
            ValueError: If MIME type validation fails
        """
        # Generate unique file name to avoid conflicts
        file_ext = Path(file_name).suffix
        unique_file_name = f"{uuid4()}{file_ext}"
        
        # Determine MIME type if not provided
        if not content_type:
            content_type = self.get_mime_type(file_name, file_content)
        
        # Validate MIME type if enabled
        if validate_mime and not self.validate_mime_type(content_type):
            raise ValueError(
                f"File type '{content_type}' is not allowed. "
                f"Allowed types: {', '.join(sorted(self.allowed_mime_types))}"
            )
        
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
            
            # Generate presigned URL for private files (valid for 7 days - AWS maximum)
            # This allows the file to be accessed in a browser without making it public
            # Presigned URLs work regardless of the bucket's region/endpoint configuration
            # Note: AWS S3 presigned URLs have a maximum expiration of 7 days (604800 seconds)
            file_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=604800  # 7 days in seconds (AWS maximum)
            )
            
            return file_url
            
        except ClientError as e:
            raise Exception(f"Failed to upload file to S3: {str(e)}")
    
    def get_presigned_url(self, s3_key: str, expires_in: int = 604800) -> str:
        """
        Generate a presigned URL for an existing S3 object.
        
        Args:
            s3_key: S3 key (path) of the file
            expires_in: URL expiration time in seconds (default: 7 days, max: 604800)
            
        Returns:
            Presigned URL string
            
        Note:
            AWS S3 presigned URLs have a maximum expiration of 7 days (604800 seconds)
        """
        if expires_in > 604800:
            expires_in = 604800  # Cap at AWS maximum
        
        try:
            return self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expires_in
            )
        except ClientError as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")
    
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
