"""Integration between PDF Discovery Framework and Google Drive storage."""

import logging
from typing import Dict, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from compute_forecast.pdf_discovery.core.models import PDFRecord, DiscoveryResult
from compute_forecast.pdf_download.downloader import SimplePDFDownloader
from .pdf_manager import PDFManager
from .google_drive_store import GoogleDriveStore

logger = logging.getLogger(__name__)


class PDFDiscoveryStorage:
    """Integrates PDF discovery with Google Drive storage."""

    def __init__(
        self,
        drive_store: GoogleDriveStore,
        pdf_manager: Optional[PDFManager] = None,
        download_cache_dir: str = "./pdf_download_cache",
        max_workers: int = 5,
    ):
        """Initialize discovery storage integration.

        Args:
            drive_store: Google Drive storage backend
            pdf_manager: Optional PDF manager (will create if not provided)
            download_cache_dir: Directory for temporary downloads
            max_workers: Maximum parallel workers
        """
        self.drive_store = drive_store
        self.pdf_manager = pdf_manager or PDFManager(drive_store)
        self.downloader = SimplePDFDownloader(cache_dir=download_cache_dir)
        self.max_workers = max_workers

    def process_discovery_results(
        self,
        discovery_result: DiscoveryResult,
        download_pdfs: bool = True,
        upload_to_drive: bool = True,
        show_progress: bool = True,
    ) -> Dict[str, Any]:
        """Process discovery results by downloading and storing PDFs.

        Args:
            discovery_result: Results from PDF discovery
            download_pdfs: Whether to download PDFs
            upload_to_drive: Whether to upload to Google Drive
            show_progress: Whether to show progress

        Returns:
            Processing statistics
        """
        start_time = time.time()

        # Convert discovery records to dict for downloader
        pdf_records = {record.paper_id: record for record in discovery_result.records}

        stats = {
            "total_discovered": len(pdf_records),
            "downloaded": 0,
            "uploaded": 0,
            "failed_download": 0,
            "failed_upload": 0,
            "already_stored": 0,
            "execution_time": 0,
        }

        if not pdf_records:
            return stats

        # Check which PDFs are already stored
        already_stored = []
        to_process = {}

        for paper_id, record in pdf_records.items():
            if paper_id in self.pdf_manager.metadata:
                already_stored.append(paper_id)
            else:
                to_process[paper_id] = record

        stats["already_stored"] = len(already_stored)
        logger.info(f"Skipping {stats['already_stored']} already stored PDFs")

        if not to_process:
            stats["execution_time"] = time.time() - start_time
            return stats

        # Download PDFs
        if download_pdfs:
            logger.info(f"Downloading {len(to_process)} PDFs...")
            download_results = self.downloader.download_batch(
                to_process, max_workers=self.max_workers, show_progress=show_progress
            )

            stats["downloaded"] = len(download_results["successful"])
            stats["failed_download"] = len(download_results["failed"])

            # Upload to Drive
            if upload_to_drive and download_results["successful"]:
                logger.info(f"Uploading {stats['downloaded']} PDFs to Google Drive...")

                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    futures = {}

                    for paper_id, pdf_path in download_results["successful"].items():
                        # Get metadata from discovery record
                        record = to_process[paper_id]
                        metadata = {
                            "source": record.source,
                            "discovery_timestamp": record.discovery_timestamp.isoformat(),
                            "confidence_score": record.confidence_score,
                            "pdf_url": record.pdf_url,
                            "version_info": record.version_info,
                        }

                        future = executor.submit(
                            self.pdf_manager.store_pdf, paper_id, pdf_path, metadata
                        )
                        futures[future] = paper_id

                    # Process results
                    for future in as_completed(futures):
                        paper_id = futures[future]
                        try:
                            success = future.result()
                            if success:
                                stats["uploaded"] += 1
                            else:
                                stats["failed_upload"] += 1
                        except Exception as e:
                            logger.error(f"Failed to upload {paper_id}: {e}")
                            stats["failed_upload"] += 1

        stats["execution_time"] = time.time() - start_time

        logger.info(
            f"Processing complete in {stats['execution_time']:.2f}s: "
            f"{stats['uploaded']} uploaded, {stats['failed_upload']} failed, "
            f"{stats['already_stored']} already stored"
        )

        return stats

    def download_and_store_pdf(
        self, pdf_record: PDFRecord, metadata: Optional[Dict] = None
    ) -> bool:
        """Download and store a single PDF.

        Args:
            pdf_record: PDF record from discovery
            metadata: Optional additional metadata

        Returns:
            True if successful
        """
        try:
            # Download PDF
            pdf_path = self.downloader.download_pdf(
                pdf_record.pdf_url, pdf_record.paper_id
            )

            # Prepare metadata
            pdf_metadata = {
                "source": pdf_record.source,
                "discovery_timestamp": pdf_record.discovery_timestamp.isoformat(),
                "confidence_score": pdf_record.confidence_score,
                "pdf_url": pdf_record.pdf_url,
                "version_info": pdf_record.version_info,
                **(metadata or {}),
            }

            # Store in Drive
            return self.pdf_manager.store_pdf(
                pdf_record.paper_id, pdf_path, pdf_metadata
            )

        except Exception as e:
            logger.error(f"Failed to process {pdf_record.paper_id}: {e}")
            return False

    def get_storage_summary(self) -> Dict[str, Any]:
        """Get summary of storage status.

        Returns:
            Storage summary statistics
        """
        manager_stats = self.pdf_manager.get_statistics()
        downloader_stats = self.downloader.get_cache_stats()

        return {
            "pdf_manager": manager_stats,
            "downloader_cache": downloader_stats,
            "drive_connection": self.drive_store.test_connection(),
        }

    def cleanup(self, force: bool = False):
        """Clean up temporary files and caches.

        Args:
            force: Force cleanup of all caches
        """
        # Clean up PDF manager cache
        self.pdf_manager.cleanup_cache(force=force)

        # Clean up downloader cache if forcing
        if force:
            count = self.downloader.clear_cache()
            logger.info(f"Cleared {count} files from download cache")
