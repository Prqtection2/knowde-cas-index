# Google Drive API Implementation for File Updates
# This file shows how to implement the replace functionality

import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
import io
import pandas as pd

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveManager:
    def __init__(self):
        self.creds = None
        self.service = None
        self.setup_credentials()
    
    def setup_credentials(self):
        """Set up Google Drive API credentials"""
        # The file token.json stores the user's access and refresh tokens
        if os.path.exists('token.json'):
            self.creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open('token.json', 'w') as token:
                token.write(self.creds.to_json())
        
        self.service = build('drive', 'v3', credentials=self.creds)
    
    def replace_file_content(self, file_id, new_file_path):
        """
        Replace file content while keeping the same file ID
        This is the key method that solves the file ID changing problem
        """
        try:
            # Create media upload object
            media = MediaFileUpload(new_file_path, resumable=True)
            
            # Update the file content (this keeps the same file ID)
            updated_file = self.service.files().update(
                fileId=file_id,
                media_body=media
            ).execute()
            
            return {
                'success': True,
                'file_id': updated_file['id'],
                'file_name': updated_file['name'],
                'modified_time': updated_file['modifiedTime']
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_file(self, file_id, local_path):
        """Download file from Google Drive"""
        try:
            request = self.service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                print(f"Download {int(status.progress() * 100)}%")
            
            # Save to local file
            with open(local_path, 'wb') as f:
                f.write(fh.getvalue())
            
            return {'success': True, 'path': local_path}
        
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_file_info(self, file_id):
        """Get file information"""
        try:
            file = self.service.files().get(fileId=file_id).execute()
            return {
                'success': True,
                'name': file['name'],
                'size': file['size'],
                'modified_time': file['modifiedTime'],
                'created_time': file['createdTime']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Example usage in your Flask app:
"""
def update_database_from_google_drive(database_key):
    # Get the file ID from config
    file_id = GOOGLE_DRIVE_FILES[database_key]['file_id']
    
    # Initialize Google Drive manager
    drive_manager = GoogleDriveManager()
    
    # Download current file
    download_result = drive_manager.download_file(file_id, f'temp_{database_key}.csv')
    
    if download_result['success']:
        # Process the new file (validate, etc.)
        new_data = pd.read_csv(download_result['path'])
        
        # If validation passes, update the local database
        if validate_data(new_data):
            # Update local file
            new_data.to_csv(LOCAL_FILES[database_key], index=False)
            
            # Reload data in memory
            load_data()
            
            return {'success': True, 'message': 'Database updated successfully'}
        else:
            return {'success': False, 'error': 'Data validation failed'}
    else:
        return {'success': False, 'error': 'Failed to download file'}
"""

# Setup instructions:
"""
1. Enable Google Drive API in Google Cloud Console
2. Create credentials (OAuth 2.0 Client ID)
3. Download credentials.json
4. Install required packages:
   pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

5. First run will open browser for authentication
6. Token will be saved for future use
""" 