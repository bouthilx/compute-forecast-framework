#!/usr/bin/env python3
"""Interactive setup wizard for Google Drive storage."""

import os
import sys
import json
from pathlib import Path
import logging
from getpass import getpass
from typing import Optional

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.pdf_storage.google_drive_store import GoogleDriveStore

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class GoogleDriveSetupWizard:
    """Interactive wizard for setting up Google Drive storage."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.env_file = self.project_root / ".env"
        self.credentials_file = self.project_root / "google_credentials.json"
        
    def run(self):
        """Run the setup wizard."""
        print("\n" + "="*60)
        print("Google Drive Storage Setup Wizard")
        print("="*60 + "\n")
        
        print("This wizard will help you set up Google Drive storage for PDFs.")
        print("You'll need:")
        print("  1. A Google Cloud Project with Drive API enabled")
        print("  2. A service account with credentials JSON")
        print("  3. A Google Drive folder ID where PDFs will be stored")
        print("")
        
        # Step 1: Service Account Setup
        if not self._setup_service_account():
            return
            
        # Step 2: Drive Folder Setup
        folder_id = self._setup_drive_folder()
        if not folder_id:
            return
            
        # Step 3: Test Connection
        if not self._test_connection(folder_id):
            return
            
        # Step 4: Save Configuration
        self._save_configuration(folder_id)
        
        print("\n" + "="*60)
        print("Setup Complete!")
        print("="*60)
        print("\nGoogle Drive storage is now configured.")
        print("You can now use the PDF storage features in your code.")
        
    def _setup_service_account(self) -> bool:
        """Set up service account credentials."""
        print("\nStep 1: Service Account Setup")
        print("-" * 40)
        
        if self.credentials_file.exists():
            print(f"\nFound existing credentials at: {self.credentials_file}")
            use_existing = input("Use existing credentials? (y/n): ").lower() == 'y'
            if use_existing:
                return True
                
        print("\nTo create a service account:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create or select a project")
        print("3. Enable the Google Drive API")
        print("4. Go to 'Credentials' → 'Create Credentials' → 'Service Account'")
        print("5. Download the JSON key file")
        print("")
        
        while True:
            creds_path = input("Enter path to service account JSON file: ").strip()
            if not creds_path:
                print("Setup cancelled.")
                return False
                
            creds_path = Path(creds_path).expanduser()
            
            if not creds_path.exists():
                print(f"File not found: {creds_path}")
                continue
                
            try:
                # Validate JSON structure
                with open(creds_path, 'r') as f:
                    creds_data = json.load(f)
                    
                required_fields = ['type', 'project_id', 'private_key', 'client_email']
                missing = [f for f in required_fields if f not in creds_data]
                
                if missing:
                    print(f"Invalid credentials file. Missing fields: {missing}")
                    continue
                    
                # Copy to project directory
                import shutil
                shutil.copy2(creds_path, self.credentials_file)
                print(f"\nCredentials saved to: {self.credentials_file}")
                return True
                
            except json.JSONDecodeError:
                print("Invalid JSON file.")
            except Exception as e:
                print(f"Error reading credentials: {e}")
                
    def _setup_drive_folder(self) -> Optional[str]:
        """Set up Google Drive folder."""
        print("\nStep 2: Google Drive Folder Setup")
        print("-" * 40)
        
        print("\nYou need a Google Drive folder to store PDFs.")
        print("The service account email must have write access to this folder.")
        print("")
        
        # Load service account email to show user
        try:
            with open(self.credentials_file, 'r') as f:
                creds_data = json.load(f)
                service_account_email = creds_data.get('client_email', 'Unknown')
                print(f"Your service account email is: {service_account_email}")
        except:
            service_account_email = "your-service-account@project.iam.gserviceaccount.com"
            
        print("\nTo share a folder with the service account:")
        print("1. Create or select a folder in Google Drive")
        print("2. Right-click → 'Share'")
        print(f"3. Add email: {service_account_email}")
        print("4. Grant 'Editor' permissions")
        print("5. Click 'Send'")
        print("")
        print("To get the folder ID:")
        print("1. Open the folder in Google Drive")
        print("2. The URL will be: https://drive.google.com/drive/folders/[FOLDER_ID]")
        print("3. Copy the FOLDER_ID part")
        print("")
        
        while True:
            folder_id = input("Enter Google Drive folder ID: ").strip()
            if not folder_id:
                print("Setup cancelled.")
                return None
                
            # Basic validation
            if len(folder_id) < 20 or ' ' in folder_id:
                print("Invalid folder ID format.")
                continue
                
            return folder_id
            
    def _test_connection(self, folder_id: str) -> bool:
        """Test the Google Drive connection."""
        print("\nStep 3: Testing Connection")
        print("-" * 40)
        
        try:
            # Load credentials to get service account email
            with open(self.credentials_file, 'r') as f:
                creds_data = json.load(f)
                service_account_email = creds_data.get('client_email', 'Unknown')
            
            print(f"\nService account email: {service_account_email}")
            print("\nTesting connection to Google Drive...")
            
            # Initialize store
            store = GoogleDriveStore(str(self.credentials_file), folder_id)
            
            # Test connection
            if store.test_connection():
                print("✓ Successfully connected to Google Drive!")
                
                # List existing files
                try:
                    files = store.list_files(page_size=5)
                    print(f"\nFound {len(files)} existing PDF(s) in the folder")
                except Exception as e:
                    print(f"\nNote: Could not list files, but connection is working: {e}")
                
                return True
            else:
                print("\n✗ Connection test failed.")
                print("\nTroubleshooting steps:")
                print(f"1. Make sure the folder is shared with: {service_account_email}")
                print("2. The service account needs 'Editor' permission on the folder")
                print("3. Double-check the folder ID from the Drive URL")
                print("\nTo share the folder:")
                print("   a. Open the folder in Google Drive")
                print("   b. Click 'Share' button")
                print(f"   c. Add email: {service_account_email}")
                print("   d. Set permission to 'Editor'")
                print("   e. Click 'Send'")
                return False
                
        except Exception as e:
            print(f"\n✗ Connection failed: {e}")
            return False
            
    def _save_configuration(self, folder_id: str):
        """Save configuration to .env file."""
        print("\nStep 4: Saving Configuration")
        print("-" * 40)
        
        # Create .env content
        env_content = f"""# Google Drive Storage Configuration
GOOGLE_CREDENTIALS_PATH={self.credentials_file.name}
GOOGLE_DRIVE_FOLDER_ID={folder_id}
"""
        
        # Add to .gitignore
        gitignore_path = self.project_root / ".gitignore"
        gitignore_entries = [
            ".env",
            "google_credentials.json",
            "temp_pdf_cache/",
            "pdf_download_cache/"
        ]
        
        if gitignore_path.exists():
            with open(gitignore_path, 'r') as f:
                existing_content = f.read()
        else:
            existing_content = ""
            
        entries_to_add = [e for e in gitignore_entries if e not in existing_content]
        
        if entries_to_add:
            with open(gitignore_path, 'a') as f:
                if existing_content and not existing_content.endswith('\n'):
                    f.write('\n')
                f.write('\n# Google Drive Storage\n')
                for entry in entries_to_add:
                    f.write(f"{entry}\n")
            print(f"\n✓ Updated .gitignore with {len(entries_to_add)} entries")
            
        # Save .env file
        with open(self.env_file, 'w') as f:
            f.write(env_content)
        print(f"✓ Configuration saved to {self.env_file}")
        
        # Create example usage file
        self._create_example_usage()
        
    def _create_example_usage(self):
        """Create an example usage file."""
        example_file = self.project_root / "examples" / "google_drive_storage_usage.py"
        example_file.parent.mkdir(exist_ok=True)
        
        example_content = '''"""Example usage of Google Drive storage with PDF discovery."""

import os
from pathlib import Path
from dotenv import load_dotenv

from src.pdf_storage import GoogleDriveStore, PDFManager, PDFDiscoveryStorage
from src.pdf_discovery.core import PDFDiscoveryFramework
from src.data.models import Paper

# Load environment variables
load_dotenv()

# Initialize storage
credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')

# Create storage components
drive_store = GoogleDriveStore(credentials_path, folder_id)
pdf_manager = PDFManager(drive_store)
storage = PDFDiscoveryStorage(drive_store, pdf_manager)

# Initialize discovery framework with storage
discovery = PDFDiscoveryFramework(storage_backend=storage)

# Add collectors (example)
# discovery.add_collector(SemanticScholarCollector())
# discovery.add_collector(OpenReviewCollector())

# Example papers to discover
papers = [
    Paper(
        paper_id="example_2024_1",
        title="Example Paper",
        authors=["Author One", "Author Two"],
        year=2024,
        venue="ICML"
    )
]

# Discover and store PDFs
results = discovery.discover_and_store_pdfs(
    papers,
    download_pdfs=True,
    upload_to_drive=True
)

print(f"Discovery: {results['discovery']}")
print(f"Storage: {results['storage']}")

# Later, retrieve a PDF for analysis
pdf_path = pdf_manager.get_pdf_for_analysis("example_2024_1")
if pdf_path:
    print(f"PDF available at: {pdf_path}")
'''
        
        with open(example_file, 'w') as f:
            f.write(example_content)
            
        print(f"\n✓ Created example usage file: {example_file}")


if __name__ == "__main__":
    wizard = GoogleDriveSetupWizard()
    wizard.run()