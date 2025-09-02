import boto3
import zipfile
import os
import tempfile
import logging
from typing import Optional

class S3Manager:
    def __init__(self, bucket_name: str = "coastal-seven-deployments"):
        self.s3 = boto3.client('s3')
        self.bucket_name = bucket_name
        self._ensure_bucket_exists()
    
    def upload_project(self, project_path: str, project_name: str) -> str:
        """Zip and upload project to S3."""
        try:
            # Create zip file (Windows compatible)
            import tempfile
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, f"{project_name}.zip")
            self._create_zip(project_path, zip_path)
            
            # Upload to S3
            s3_key = f"projects/{project_name}.zip"
            self.s3.upload_file(zip_path, self.bucket_name, s3_key)
            
            # Generate public URL
            s3_url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"
            
            logging.info(f"Uploaded project to S3: {s3_url}")
            
            # Cleanup local zip
            os.remove(zip_path)
            
            return s3_url
            
        except Exception as e:
            logging.error(f"Failed to upload to S3: {str(e)}")
            raise
    
    def _create_zip(self, source_dir: str, zip_path: str):
        """Create zip file from project directory."""
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                # Skip unnecessary directories
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.env']]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, source_dir)
                    zipf.write(file_path, arc_name)
    
    def _ensure_bucket_exists(self):
        """Ensure S3 bucket exists."""
        try:
            self.s3.head_bucket(Bucket=self.bucket_name)
        except:
            try:
                # For ap-south-2, don't specify LocationConstraint
                self.s3.create_bucket(Bucket=self.bucket_name)
                
                # Make bucket public for deployment downloads
                self.s3.put_bucket_policy(
                    Bucket=self.bucket_name,
                    Policy=f'''{{
                        "Version": "2012-10-17",
                        "Statement": [
                            {{
                                "Sid": "PublicReadGetObject",
                                "Effect": "Allow",
                                "Principal": "*",
                                "Action": "s3:GetObject",
                                "Resource": "arn:aws:s3:::{self.bucket_name}/*"
                            }}
                        ]
                    }}'''
                )
                
                logging.info(f"Created S3 bucket: {self.bucket_name}")
            except Exception as e:
                logging.error(f"Failed to create S3 bucket: {str(e)}")
                raise