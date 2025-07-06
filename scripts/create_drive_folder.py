#!/usr/bin/env python3
"""Create a Google Drive folder using the service account."""

import os
import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Load environment
load_dotenv()


def create_pdf_storage_folder():
    """Create a folder owned by the service account."""
    print("Creating Google Drive Folder for PDF Storage")
    print("=" * 60)
    
    # Load credentials
    creds_path = os.getenv('GOOGLE_CREDENTIALS_PATH', 'google_credentials.json')
    if not os.path.exists(creds_path):
        print("❌ Credentials file not found!")
        print("Run setup_google_drive.py first.")
        return
        
    try:
        # Initialize service
        credentials = Credentials.from_service_account_file(
            creds_path,
            scopes=['https://www.googleapis.com/auth/drive.file']
        )
        service = build('drive', 'v3', credentials=credentials)
        
        # Create the folder
        folder_metadata = {
            'name': 'Mila_Compute_Analysis_PDFs',
            'mimeType': 'application/vnd.google-apps.folder',
            'description': 'PDF storage for Mila computational analysis project'
        }
        
        folder = service.files().create(
            body=folder_metadata,
            fields='id, name, webViewLink'
        ).execute()
        
        print(f"\n✓ Successfully created folder: {folder['name']}")
        print(f"  Folder ID: {folder['id']}")
        print(f"  Web Link: {folder.get('webViewLink', 'N/A')}")
        
        # Update .env file
        env_path = Path('.env')
        env_content = ""
        
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
            
            # Update existing GOOGLE_DRIVE_FOLDER_ID
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('GOOGLE_DRIVE_FOLDER_ID='):
                    lines[i] = f"GOOGLE_DRIVE_FOLDER_ID={folder['id']}\n"
                    updated = True
                    break
            
            if not updated:
                lines.append(f"\nGOOGLE_DRIVE_FOLDER_ID={folder['id']}\n")
            
            env_content = ''.join(lines)
        else:
            env_content = f"""# Google Drive Storage Configuration
GOOGLE_CREDENTIALS_PATH={creds_path}
GOOGLE_DRIVE_FOLDER_ID={folder['id']}
"""
        
        with open(env_path, 'w') as f:
            f.write(env_content)
            
        print(f"\n✓ Updated .env file with folder ID")
        
        # Test the folder
        print("\nTesting folder access...")
        test_file_metadata = {
            'name': 'test.txt',
            'parents': [folder['id']]
        }
        
        test_file = service.files().create(
            body=test_file_metadata,
            fields='id'
        ).execute()
        
        # Clean up test file
        service.files().delete(fileId=test_file['id']).execute()
        print("✓ Folder is working correctly!")
        
        print("\n" + "="*60)
        print("Setup complete! The service account now owns the folder.")
        print("You can start using the PDF storage system.")
        
        # Optional: Share with user
        print("\nWould you like to share this folder with your Google account?")
        print("This will let you view the PDFs in your Google Drive.")
        email = input("Enter your Google email (or press Enter to skip): ").strip()
        
        if email and '@' in email:
            try:
                permission = {
                    'type': 'user',
                    'role': 'writer',
                    'emailAddress': email
                }
                
                service.permissions().create(
                    fileId=folder['id'],
                    body=permission,
                    fields='id'
                ).execute()
                
                print(f"✓ Shared folder with {email}")
                print("  You should see it in 'Shared with me' in your Drive")
                
            except HttpError as e:
                print(f"⚠️  Could not share folder: {e}")
                print("  The folder will still work for PDF storage")
        
        return folder['id']
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


if __name__ == "__main__":
    folder_id = create_pdf_storage_folder()
    
    if folder_id:
        print(f"\nNext steps:")
        print(f"1. The folder is ready to use")
        print(f"2. Run your PDF discovery/storage scripts")
        print(f"3. PDFs will be stored in the service account's Drive")