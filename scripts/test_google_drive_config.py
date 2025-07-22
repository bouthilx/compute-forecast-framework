#!/usr/bin/env python3
"""Diagnostic script to test Google Drive configuration."""

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
from compute_forecast.storage.google_drive import GoogleDriveStorage

# Load environment
load_dotenv()


def test_configuration():
    """Test Google Drive configuration step by step."""
    print("Google Drive Configuration Diagnostic")
    print("=" * 60)

    # 1. Check credentials file
    creds_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "google_credentials.json")
    print(f"\n1. Checking credentials file: {creds_path}")

    if not os.path.exists(creds_path):
        print("   ❌ Credentials file not found!")
        return

    service_account_email = None
    try:
        with open(creds_path, "r") as f:
            creds_data = json.load(f)

        service_account_email = creds_data.get("client_email")
        project_id = creds_data.get("project_id")

        print(f"   ✓ Found credentials for project: {project_id}")
        print(f"   ✓ Service account: {service_account_email}")
    except Exception as e:
        print(f"   ❌ Error reading credentials: {e}")
        return

    # 2. Test API connection
    print("\n2. Testing Google Drive API connection")
    try:
        credentials = Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/drive.file"]
        )
        service = build("drive", "v3", credentials=credentials)

        # Test basic API access
        about = service.about().get(fields="user").execute()
        print(f"   ✓ Connected as: {about['user']['emailAddress']}")
    except HttpError as e:
        print(f"   ❌ API Error: {e}")
        print("   Make sure Google Drive API is enabled in your project")
        return
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return

    # 3. List accessible files/folders
    print("\n3. Listing accessible items")
    try:
        # List all items the service account can see
        results = (
            service.files()
            .list(
                pageSize=10,
                fields="files(id, name, mimeType, owners, permissions)",
                orderBy="modifiedTime desc",
            )
            .execute()
        )

        items = results.get("files", [])

        if not items:
            print("   ⚠️  No files or folders accessible to this service account")
            print(
                "   This means the service account hasn't been shared any folders yet"
            )
        else:
            print(f"   Found {len(items)} accessible items:")
            for item in items:
                mime_type = item["mimeType"]
                if mime_type == "application/vnd.google-apps.folder":
                    print(f"   📁 Folder: {item['name']} (ID: {item['id']})")
                else:
                    print(f"   📄 File: {item['name']} (ID: {item['id']})")
    except Exception as e:
        print(f"   ❌ Error listing files: {e}")

    # 4. Test specific folder if provided
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    has_access = False
    if folder_id:
        print(f"\n4. Testing access to configured folder: {folder_id}")
        try:
            folder = (
                service.files()
                .get(fileId=folder_id, fields="id, name, mimeType, owners, permissions")
                .execute()
            )

            print(f"   ✓ Folder found: {folder['name']}")
            print(f"   Type: {folder['mimeType']}")

            # Check permissions
            permissions = folder.get("permissions", [])
            has_access = False
            for perm in permissions:
                if perm.get("emailAddress") == service_account_email:
                    has_access = True
                    print(f"   ✓ Service account has '{perm['role']}' permission")
                    break

            if not has_access:
                print("   ❌ Service account does NOT have access to this folder!")
                print(f"   Please share the folder with: {service_account_email}")

        except HttpError as e:
            if e.resp.status == 404:
                print("   ❌ Folder not found or not accessible!")
                print("   Please check:")
                print("   1. The folder ID is correct")
                print(f"   2. The folder is shared with: {service_account_email}")
            else:
                print(f"   ❌ Error: {e}")
    else:
        print("\n4. No folder ID configured in .env file")

    # 5. Test using the actual storage implementation
    print("\n5. Testing storage implementation")
    if folder_id:
        try:
            # Test with the actual GoogleDriveStorage class
            storage = GoogleDriveStorage(
                credentials_path=creds_path, folder_id=folder_id
            )

            if storage.test_connection():
                print("   ✓ Storage implementation is working correctly")
                print("   The download command will use this configuration")
            else:
                print("   ❌ Storage test failed")

        except Exception as e:
            print(f"   ❌ Could not initialize storage: {e}")
    else:
        print("   ⚠️  Skipping storage test (no folder ID configured)")

    print("\n" + "=" * 60)
    print("Diagnostic complete")

    # Provide recommendations
    if folder_id and not has_access:
        print("\nRECOMMENDED ACTIONS:")
        print(f"1. Go to https://drive.google.com/drive/folders/{folder_id}")
        print("2. Click 'Share'")
        print(f"3. Add: {service_account_email}")
        print("4. Set permission to 'Editor'")
        print("5. Click 'Send'")
        print("6. Wait a few seconds and run this test again")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test Google Drive configuration")
    parser.add_argument(
        "--folder-id", help="Test access to a specific folder ID (overrides .env)"
    )
    args = parser.parse_args()

    if args.folder_id:
        os.environ["GOOGLE_DRIVE_FOLDER_ID"] = args.folder_id

    test_configuration()
