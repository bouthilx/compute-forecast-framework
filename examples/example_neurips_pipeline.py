#!/usr/bin/env python3
"""
Enhanced NeurIPS pipeline example that:
1. Saves extracted text to files
2. Integrates with Google Drive storage
3. Provides detailed affiliation extraction logging
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
import requests
from datetime import datetime
import os

from compute_forecast.pdf_parser.core.processor import OptimizedPDFProcessor
from compute_forecast.pdf_parser.extractors.pymupdf_extractor import PyMuPDFExtractor
from compute_forecast.pdf_download.downloader import SimplePDFDownloader
from compute_forecast.pdf_discovery.sources.openreview_collector import (
    OpenReviewPDFCollector,
)
from compute_forecast.data.models import CollectionQuery
from compute_forecast.data.collectors.citation_collector import CitationCollector

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed logs
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("neurips_pipeline_debug.log"),
    ],
)
logger = logging.getLogger(__name__)

# Import Google Drive components
try:
    from compute_forecast.pdf_storage.google_drive_store import GoogleDriveStore
    from compute_forecast.pdf_storage.pdf_manager import PDFManager

    GOOGLE_DRIVE_AVAILABLE = True
except ImportError:
    logger.warning("Google Drive integration not available")
    GOOGLE_DRIVE_AVAILABLE = False


class EnhancedNeurIPS2024Pipeline:
    """Enhanced pipeline with text saving, Google Drive, and detailed logging."""

    def __init__(
        self,
        cache_dir: str = "neurips_2024_enhanced_cache",
        use_google_drive: bool = True,
        drive_folder_id: Optional[str] = None,
    ):
        """Initialize the enhanced pipeline.

        Args:
            cache_dir: Local cache directory
            use_google_drive: Whether to use Google Drive storage
            drive_folder_id: Google Drive folder ID for PDFs
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        # Create subdirectories
        self.pdfs_dir = self.cache_dir / "pdfs"
        self.pdfs_dir.mkdir(exist_ok=True)
        self.extracted_text_dir = self.cache_dir / "extracted_text"
        self.extracted_text_dir.mkdir(exist_ok=True)
        self.extraction_logs_dir = self.cache_dir / "extraction_logs"
        self.extraction_logs_dir.mkdir(exist_ok=True)

        # Initialize PDF processor with PyMuPDF
        self.processor = OptimizedPDFProcessor({"test_mode": True})
        self.pymupdf_extractor = PyMuPDFExtractor()
        self.processor.register_extractor("pymupdf", self.pymupdf_extractor, level=1)

        # Initialize PDF downloader
        self.downloader = SimplePDFDownloader(cache_dir=str(self.pdfs_dir))

        # Initialize OpenReview collector
        self.openreview_collector = OpenReviewPDFCollector()

        # Initialize Google Drive storage if requested
        self.use_google_drive = use_google_drive and GOOGLE_DRIVE_AVAILABLE
        self.pdf_manager = None

        if self.use_google_drive:
            try:
                # Check for credentials
                if not os.path.exists("credentials.json"):
                    logger.warning(
                        "Google Drive credentials.json not found - disabling Drive storage"
                    )
                    self.use_google_drive = False
                else:
                    drive_store = GoogleDriveStore(
                        credentials_file="credentials.json", folder_id=drive_folder_id
                    )
                    self.pdf_manager = PDFManager(
                        drive_store=drive_store, cache_dir=str(self.pdfs_dir)
                    )
                    logger.info("Google Drive storage initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive: {e}")
                self.use_google_drive = False

        # Test results
        self.results = {
            "papers_collected": 0,
            "pdfs_downloaded": 0,
            "pdfs_uploaded_to_drive": 0,
            "successful_extractions": 0,
            "failed_extractions": 0,
            "extraction_details": [],
            "saved_text_files": [],
        }

    def collect_neurips_2024_papers(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Collect NeurIPS 2024 papers using citation collectors."""
        logger.info(f"Collecting NeurIPS 2024 papers (limit: {limit})...")

        try:
            # Initialize citation collector
            citation_collector = CitationCollector()

            # Create query
            query = CollectionQuery(
                domain="machine_learning",
                year=2024,
                venue="NeurIPS",
                keywords=["neural", "deep learning", "machine learning"],
                max_results=limit * 2,
            )

            # Collect from all sources
            results = citation_collector.collect_from_all_sources(query)
            all_papers = citation_collector.get_combined_papers(results)

            # Convert to dict format
            collected_papers = []
            for paper in all_papers:
                # Accept papers with ML keywords
                if any(
                    kw in paper.title.lower() for kw in ["neural", "learning", "model"]
                ):
                    # Discover PDF URL
                    pdf_url = None
                    if paper.urls:
                        for url in paper.urls:
                            if ".pdf" in url:
                                pdf_url = url
                                break

                    if pdf_url:
                        paper_dict = {
                            "paper_id": paper.paper_id
                            or f"neurips_2024_{len(collected_papers)}",
                            "title": paper.title,
                            "authors": [author.name for author in paper.authors],
                            "url": pdf_url,
                            "venue": paper.venue,
                            "year": paper.year,
                            "abstract": paper.abstract[:200] + "..."
                            if paper.abstract
                            else "",
                        }
                        collected_papers.append(paper_dict)

                        if len(collected_papers) >= limit:
                            break

            self.results["papers_collected"] = len(collected_papers)
            logger.info(f"Collected {len(collected_papers)} papers")
            return collected_papers

        except Exception as e:
            logger.error(f"Failed to collect papers: {e}")
            return []

    def download_and_store_pdfs(
        self, papers: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Download PDFs and optionally upload to Google Drive."""
        logger.info(f"Downloading {len(papers)} PDFs...")

        downloaded_papers = []

        for paper in papers:
            try:
                logger.info(f"Downloading: {paper['title'][:50]}...")

                # Download PDF
                response = requests.get(paper["url"], timeout=30)
                response.raise_for_status()

                # Save locally
                pdf_filename = f"{paper['paper_id']}.pdf"
                pdf_path = self.pdfs_dir / pdf_filename

                with open(pdf_path, "wb") as f:
                    f.write(response.content)

                paper["pdf_path"] = str(pdf_path)
                paper["pdf_size"] = len(response.content)

                logger.info(
                    f"✓ Downloaded {pdf_filename} ({len(response.content)} bytes)"
                )
                self.results["pdfs_downloaded"] += 1

                # Upload to Google Drive if enabled
                if self.use_google_drive and self.pdf_manager:
                    try:
                        metadata = {
                            "title": paper["title"],
                            "authors": paper["authors"],
                            "venue": paper["venue"],
                            "year": paper["year"],
                        }
                        file_id = self.pdf_manager.upload_new_pdf(
                            paper["paper_id"], pdf_path, metadata
                        )
                        paper["drive_file_id"] = file_id
                        self.results["pdfs_uploaded_to_drive"] += 1
                        logger.info(f"✓ Uploaded to Google Drive: {file_id}")
                    except Exception as e:
                        logger.error(f"Failed to upload to Drive: {e}")

                downloaded_papers.append(paper)
                time.sleep(1)  # Rate limiting

            except Exception as e:
                logger.error(f"✗ Failed to download {paper['title'][:30]}: {e}")
                continue

        return downloaded_papers

    def extract_and_save_text(self, papers: List[Dict[str, Any]]) -> None:
        """Extract text with detailed logging and save to files."""
        logger.info(f"Extracting text from {len(papers)} papers...")

        for paper in papers:
            extraction_log = {
                "paper_id": paper["paper_id"],
                "title": paper["title"],
                "timestamp": datetime.now().isoformat(),
                "affiliation_extraction": {},
                "full_text_extraction": {},
            }

            try:
                pdf_path = Path(paper["pdf_path"])
                if not pdf_path.exists():
                    raise FileNotFoundError(f"PDF not found: {pdf_path}")

                # Create paper metadata
                paper_metadata = {"title": paper["title"], "authors": paper["authors"]}

                logger.info(f"Processing: {paper['title'][:50]}...")

                # Extract with detailed logging
                start_time = time.time()

                # Manually extract affiliations first for detailed logging
                logger.debug("Starting affiliation extraction...")
                try:
                    affiliation_result = self.pymupdf_extractor.extract_first_pages(
                        pdf_path, pages=[0, 1]
                    )

                    extraction_log["affiliation_extraction"] = {
                        "status": "extracted",
                        "confidence": affiliation_result.get("confidence", 0.0),
                        "text_length": len(affiliation_result.get("text", "")),
                        "first_100_chars": affiliation_result.get("text", "")[:100],
                    }

                    # Log validation details
                    from compute_forecast.pdf_parser.core.validation import (
                        AffiliationValidator,
                    )

                    validator = AffiliationValidator()
                    is_valid = validator.validate_affiliations(
                        affiliation_result, paper_metadata
                    )

                    extraction_log["affiliation_extraction"]["validation"] = {
                        "passed": is_valid,
                        "confidence_threshold": validator.min_confidence,
                        "actual_confidence": affiliation_result.get("confidence", 0.0),
                        "min_text_length": validator.min_text_length,
                        "actual_text_length": len(affiliation_result.get("text", "")),
                        "affiliations_found": len(
                            affiliation_result.get("affiliations", [])
                        ),
                    }

                    logger.debug(f"Affiliation validation: {is_valid}")
                    logger.debug(
                        f"Confidence: {affiliation_result.get('confidence', 0.0)}"
                    )
                    logger.debug(
                        f"Text length: {len(affiliation_result.get('text', ''))}"
                    )

                except Exception as e:
                    extraction_log["affiliation_extraction"] = {
                        "status": "failed",
                        "error": str(e),
                    }
                    logger.error(f"Affiliation extraction failed: {e}")

                # Process full document
                result = self.processor.process_pdf(pdf_path, paper_metadata)
                extraction_time = time.time() - start_time

                # Extract full text
                full_text = result.get("full_text", "")

                extraction_log["full_text_extraction"] = {
                    "status": "success" if full_text else "failed",
                    "text_length": len(full_text),
                    "word_count": len(full_text.split()) if full_text else 0,
                    "extraction_time": extraction_time,
                    "method": result.get("method", "unknown"),
                }

                if full_text:
                    # Save extracted text
                    text_filename = f"{paper['paper_id']}_extracted.txt"
                    text_path = self.extracted_text_dir / text_filename

                    with open(text_path, "w", encoding="utf-8") as f:
                        f.write(f"Title: {paper['title']}\n")
                        f.write(f"Authors: {', '.join(paper['authors'])}\n")
                        f.write(f"Venue: {paper['venue']}\n")
                        f.write(f"Year: {paper['year']}\n")
                        f.write(f"Extraction timestamp: {datetime.now().isoformat()}\n")
                        f.write(f"{'=' * 80}\n\n")
                        f.write(full_text)

                    self.results["saved_text_files"].append(str(text_path))
                    self.results["successful_extractions"] += 1
                    extraction_log["saved_text_file"] = str(text_path)

                    logger.info(f"✓ Saved extracted text to: {text_path}")
                    logger.info(
                        f"  Text length: {len(full_text)} chars, {len(full_text.split())} words"
                    )
                else:
                    self.results["failed_extractions"] += 1
                    logger.error(f"✗ No text extracted from {paper['paper_id']}")

            except Exception as e:
                logger.error(f"✗ Extraction failed for {paper['paper_id']}: {e}")
                self.results["failed_extractions"] += 1
                extraction_log["error"] = str(e)

            # Save detailed extraction log
            log_filename = f"{paper['paper_id']}_extraction_log.json"
            log_path = self.extraction_logs_dir / log_filename

            with open(log_path, "w") as f:
                json.dump(extraction_log, f, indent=2)

            self.results["extraction_details"].append(extraction_log)

    def run_complete_pipeline(self, num_papers: int = 3) -> Dict[str, Any]:
        """Run the complete enhanced pipeline."""
        logger.info("=" * 60)
        logger.info("STARTING ENHANCED NEURIPS 2024 PIPELINE")
        logger.info("=" * 60)

        start_time = time.time()

        try:
            # Step 1: Collect papers
            papers = self.collect_neurips_2024_papers(limit=num_papers)

            if not papers:
                raise RuntimeError("No papers collected")

            # Step 2: Download PDFs and upload to Drive
            downloaded_papers = self.download_and_store_pdfs(papers)

            # Step 3: Extract and save text
            self.extract_and_save_text(downloaded_papers)

            # Calculate final metrics
            total_time = time.time() - start_time
            self.results["pipeline_summary"] = {
                "total_runtime": round(total_time, 2),
                "success_rate": round(
                    (
                        self.results["successful_extractions"]
                        / max(
                            1,
                            self.results["successful_extractions"]
                            + self.results["failed_extractions"],
                        )
                    )
                    * 100,
                    1,
                ),
                "google_drive_enabled": self.use_google_drive,
                "text_files_saved": len(self.results["saved_text_files"]),
            }

            # Print summary
            self._print_pipeline_summary()

            # Save results
            self._save_results()

            return self.results

        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise

    def _print_pipeline_summary(self) -> None:
        """Print comprehensive pipeline summary."""
        logger.info("\n" + "=" * 60)
        logger.info("ENHANCED PIPELINE SUMMARY")
        logger.info("=" * 60)

        summary = self.results["pipeline_summary"]

        logger.info("📊 OVERALL METRICS:")
        logger.info(f"   Total Runtime: {summary['total_runtime']} seconds")
        logger.info(f"   Success Rate: {summary['success_rate']}%")
        logger.info(
            f"   Google Drive: {'Enabled' if summary['google_drive_enabled'] else 'Disabled'}"
        )

        logger.info("\n📄 PAPER PROCESSING:")
        logger.info(f"   Papers Collected: {self.results['papers_collected']}")
        logger.info(f"   PDFs Downloaded: {self.results['pdfs_downloaded']}")
        if self.use_google_drive:
            logger.info(
                f"   PDFs Uploaded to Drive: {self.results['pdfs_uploaded_to_drive']}"
            )
        logger.info(
            f"   Successful Extractions: {self.results['successful_extractions']}"
        )
        logger.info(f"   Failed Extractions: {self.results['failed_extractions']}")
        logger.info(f"   Text Files Saved: {summary['text_files_saved']}")

        logger.info("\n📁 OUTPUT LOCATIONS:")
        logger.info(f"   PDFs: {self.pdfs_dir}")
        logger.info(f"   Extracted Text: {self.extracted_text_dir}")
        logger.info(f"   Extraction Logs: {self.extraction_logs_dir}")

        logger.info("\n🔍 EXTRACTION DETAILS:")
        for detail in self.results["extraction_details"][:3]:  # Show first 3
            logger.info(f"   Paper: {detail['title'][:50]}...")

            # Affiliation extraction details
            aff_info = detail.get("affiliation_extraction", {})
            if aff_info.get("status") == "extracted":
                validation = aff_info.get("validation", {})
                logger.info(
                    f"   - Affiliation extraction: {'PASSED' if validation.get('passed') else 'FAILED'}"
                )
                logger.info(
                    f"     Confidence: {aff_info.get('confidence', 0):.3f} (threshold: {validation.get('confidence_threshold', 0.5)})"
                )
                logger.info(
                    f"     Text length: {aff_info.get('text_length', 0)} (min: {validation.get('min_text_length', 20)})"
                )
                logger.info(
                    f"     Affiliations found: {validation.get('affiliations_found', 0)}"
                )
            else:
                logger.info(
                    f"   - Affiliation extraction: FAILED - {aff_info.get('error', 'Unknown error')}"
                )

            # Full text extraction
            full_info = detail.get("full_text_extraction", {})
            if full_info.get("status") == "success":
                logger.info(
                    f"   - Full text: {full_info.get('word_count', 0)} words in {full_info.get('extraction_time', 0):.2f}s"
                )

            if "saved_text_file" in detail:
                logger.info(f"   - Saved to: {Path(detail['saved_text_file']).name}")

        logger.info("\n" + "=" * 60)

    def _save_results(self) -> None:
        """Save detailed results."""
        results_file = (
            self.cache_dir
            / f"pipeline_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        logger.info(f"📁 Results saved to: {results_file}")


def main():
    """Run the enhanced pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced NeurIPS 2024 Pipeline")
    parser.add_argument(
        "--papers", type=int, default=3, help="Number of papers to process"
    )
    parser.add_argument(
        "--no-drive", action="store_true", help="Disable Google Drive storage"
    )
    parser.add_argument("--drive-folder", type=str, help="Google Drive folder ID")
    parser.add_argument(
        "--cache-dir",
        type=str,
        default="neurips_2024_enhanced_cache",
        help="Cache directory",
    )

    args = parser.parse_args()

    try:
        # Initialize pipeline
        pipeline = EnhancedNeurIPS2024Pipeline(
            cache_dir=args.cache_dir,
            use_google_drive=not args.no_drive,
            drive_folder_id=args.drive_folder,
        )

        # Run pipeline
        results = pipeline.run_complete_pipeline(num_papers=args.papers)

        # Print success
        if results["successful_extractions"] > 0:
            print("\n🎉 SUCCESS: Enhanced pipeline completed!")
            print(f"   Processed {results['successful_extractions']} papers")
            print(f"   Saved text files to: {pipeline.extracted_text_dir}")
            print(f"   Detailed logs in: {pipeline.extraction_logs_dir}")
        else:
            print("\n❌ FAILURE: No papers successfully processed")
            return 1

        return 0

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
