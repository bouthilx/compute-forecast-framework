#!/usr/bin/env python3
"""Migration script to upload existing PDFs to Google Drive."""

import os
import sys
import json
from pathlib import Path
import logging
from typing import Dict, List, Tuple
import time

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich.console import Console
from rich.table import Table

from src.pdf_storage import GoogleDriveStore, PDFManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()


class PDFMigrationTool:
    """Tool for migrating existing PDFs to Google Drive."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        load_dotenv(self.project_root / ".env")
        
        # Load configuration
        self.credentials_path = os.getenv('GOOGLE_CREDENTIALS_PATH')
        self.folder_id = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        if not self.credentials_path or not self.folder_id:
            raise ValueError(
                "Google Drive not configured. Run setup_google_drive.py first."
            )
            
        # Initialize storage
        self.drive_store = GoogleDriveStore(self.credentials_path, self.folder_id)
        self.pdf_manager = PDFManager(self.drive_store)
        
    def find_existing_pdfs(self) -> Dict[str, List[Path]]:
        """Find all existing PDFs in the project.
        
        Returns:
            Dictionary mapping directory to list of PDF files
        """
        pdf_locations = {}
        
        # Common PDF directories
        search_dirs = [
            self.project_root / "pdf_cache",
            self.project_root / "pdf_download_cache",
            self.project_root / "temp_pdf_cache",
            self.project_root / "data" / "pdfs",
            self.project_root / "pdfs"
        ]
        
        # Also search for any *.pdf files in the project
        all_pdfs = list(self.project_root.glob("**/*.pdf"))
        
        for pdf_path in all_pdfs:
            # Skip hidden directories
            if any(part.startswith('.') for part in pdf_path.parts):
                continue
                
            dir_path = pdf_path.parent
            if dir_path not in pdf_locations:
                pdf_locations[dir_path] = []
            pdf_locations[dir_path].append(pdf_path)
            
        return pdf_locations
        
    def extract_paper_id(self, pdf_path: Path) -> str:
        """Extract paper ID from PDF filename.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Paper ID
        """
        # Remove .pdf extension
        filename = pdf_path.stem
        
        # Common patterns:
        # - paper_id.pdf
        # - 2024_author_title.pdf
        # - arxiv_2401_12345.pdf
        
        return filename
        
    def migrate_pdfs(self, dry_run: bool = False):
        """Migrate PDFs to Google Drive.
        
        Args:
            dry_run: If True, only show what would be done
        """
        console.print("\n[bold]PDF Migration Tool[/bold]")
        console.print("=" * 60)
        
        # Find existing PDFs
        with console.status("[bold green]Searching for PDFs..."):
            pdf_locations = self.find_existing_pdfs()
            
        if not pdf_locations:
            console.print("[yellow]No PDFs found to migrate.[/yellow]")
            return
            
        # Display found PDFs
        total_pdfs = sum(len(pdfs) for pdfs in pdf_locations.values())
        console.print(f"\nFound [bold]{total_pdfs}[/bold] PDFs in {len(pdf_locations)} directories:")
        
        table = Table(title="PDF Locations")
        table.add_column("Directory", style="cyan")
        table.add_column("PDF Count", style="green")
        table.add_column("Total Size", style="yellow")
        
        for dir_path, pdfs in sorted(pdf_locations.items()):
            total_size = sum(pdf.stat().st_size for pdf in pdfs)
            size_mb = total_size / (1024 * 1024)
            table.add_row(
                str(dir_path.relative_to(self.project_root)),
                str(len(pdfs)),
                f"{size_mb:.1f} MB"
            )
            
        console.print(table)
        
        if dry_run:
            console.print("\n[yellow]DRY RUN - No files will be uploaded[/yellow]")
        else:
            # Confirm migration
            console.print(f"\nThis will upload {total_pdfs} PDFs to Google Drive.")
            confirm = console.input("Continue? (y/n): ")
            if confirm.lower() != 'y':
                console.print("[red]Migration cancelled.[/red]")
                return
                
        # Check existing files in Drive
        console.print("\n[bold]Checking existing files in Drive...[/bold]")
        existing_files = self.drive_store.list_files(page_size=1000)
        existing_names = {f['name'].replace('.pdf', '') for f in existing_files}
        console.print(f"Found {len(existing_files)} existing PDFs in Drive")
        
        # Prepare migration
        to_migrate = []
        skipped = []
        
        for dir_path, pdfs in pdf_locations.items():
            for pdf_path in pdfs:
                paper_id = self.extract_paper_id(pdf_path)
                
                if paper_id in existing_names:
                    skipped.append((paper_id, pdf_path))
                else:
                    to_migrate.append((paper_id, pdf_path))
                    
        console.print(f"\nTo migrate: [green]{len(to_migrate)}[/green]")
        console.print(f"Already exists: [yellow]{len(skipped)}[/yellow]")
        
        if not to_migrate:
            console.print("\n[green]All PDFs are already in Drive![/green]")
            return
            
        if dry_run:
            console.print("\n[yellow]Would upload the following PDFs:[/yellow]")
            for paper_id, pdf_path in to_migrate[:10]:
                console.print(f"  - {paper_id} ({pdf_path.name})")
            if len(to_migrate) > 10:
                console.print(f"  ... and {len(to_migrate) - 10} more")
            return
            
        # Perform migration
        console.print(f"\n[bold]Migrating {len(to_migrate)} PDFs...[/bold]")
        
        successful = 0
        failed = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Uploading PDFs", total=len(to_migrate))
            
            for paper_id, pdf_path in to_migrate:
                progress.update(task, description=f"Uploading {paper_id}...")
                
                try:
                    # Extract any metadata from filename
                    metadata = {
                        'original_path': str(pdf_path.relative_to(self.project_root)),
                        'migration_time': time.time()
                    }
                    
                    # Upload to Drive
                    success = self.pdf_manager.store_pdf(paper_id, pdf_path, metadata)
                    
                    if success:
                        successful += 1
                    else:
                        failed.append((paper_id, "Upload failed"))
                        
                except Exception as e:
                    failed.append((paper_id, str(e)))
                    logger.error(f"Failed to migrate {paper_id}: {e}")
                    
                progress.advance(task)
                
        # Summary
        console.print("\n[bold]Migration Summary[/bold]")
        console.print("=" * 60)
        console.print(f"Successfully uploaded: [green]{successful}[/green]")
        console.print(f"Failed: [red]{len(failed)}[/red]")
        
        if failed:
            console.print("\n[red]Failed uploads:[/red]")
            for paper_id, error in failed[:10]:
                console.print(f"  - {paper_id}: {error}")
            if len(failed) > 10:
                console.print(f"  ... and {len(failed) - 10} more")
                
        # Sync metadata
        console.print("\n[bold]Syncing metadata...[/bold]")
        sync_stats = self.pdf_manager.sync_with_drive()
        console.print(f"Metadata synced: {sync_stats}")
        
        console.print("\n[green]Migration complete![/green]")
        
    def cleanup_local_pdfs(self, dry_run: bool = True):
        """Clean up local PDFs that are already in Drive.
        
        Args:
            dry_run: If True, only show what would be deleted
        """
        console.print("\n[bold]Local PDF Cleanup[/bold]")
        console.print("=" * 60)
        
        # Sync with Drive first
        self.pdf_manager.sync_with_drive()
        
        # Find local PDFs
        pdf_locations = self.find_existing_pdfs()
        
        to_delete = []
        total_size = 0
        
        for dir_path, pdfs in pdf_locations.items():
            for pdf_path in pdfs:
                paper_id = self.extract_paper_id(pdf_path)
                
                # Check if in Drive
                if paper_id in self.pdf_manager.metadata:
                    to_delete.append(pdf_path)
                    total_size += pdf_path.stat().st_size
                    
        if not to_delete:
            console.print("[yellow]No local PDFs to clean up.[/yellow]")
            return
            
        size_mb = total_size / (1024 * 1024)
        console.print(f"\nFound {len(to_delete)} PDFs to clean up ({size_mb:.1f} MB)")
        
        if dry_run:
            console.print("\n[yellow]DRY RUN - No files will be deleted[/yellow]")
            console.print("\nWould delete:")
            for pdf_path in to_delete[:10]:
                console.print(f"  - {pdf_path.relative_to(self.project_root)}")
            if len(to_delete) > 10:
                console.print(f"  ... and {len(to_delete) - 10} more")
        else:
            confirm = console.input("\nDelete these files? (y/n): ")
            if confirm.lower() != 'y':
                console.print("[red]Cleanup cancelled.[/red]")
                return
                
            deleted = 0
            for pdf_path in to_delete:
                try:
                    pdf_path.unlink()
                    deleted += 1
                except Exception as e:
                    logger.error(f"Failed to delete {pdf_path}: {e}")
                    
            console.print(f"\n[green]Deleted {deleted} files, freed {size_mb:.1f} MB[/green]")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate existing PDFs to Google Drive"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up local PDFs that are already in Drive"
    )
    
    args = parser.parse_args()
    
    try:
        tool = PDFMigrationTool()
        
        if args.cleanup:
            tool.cleanup_local_pdfs(dry_run=args.dry_run)
        else:
            tool.migrate_pdfs(dry_run=args.dry_run)
            
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Migration cancelled by user.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Unexpected error: {e}[/red]")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()