"""Worker process for parallel venue collection."""

import multiprocessing
import logging
import traceback
from typing import List, Optional
from queue import Queue

from ..sources.scrapers.registry import get_registry
from ..sources.scrapers.base import ScrapingConfig
from .models import CollectionResult


class VenueWorker(multiprocessing.Process):
    """Worker process that collects papers from a single venue across multiple years."""
    
    def __init__(
        self, 
        venue: str, 
        years: List[int], 
        config: ScrapingConfig, 
        result_queue: multiprocessing.Queue,
        scraper_override: Optional[str] = None,
        log_level: int = logging.WARNING
    ):
        """
        Initialize venue worker.
        
        Args:
            venue: Venue name to scrape
            years: List of years to scrape (will be sorted)
            config: Scraping configuration
            result_queue: Queue to put results in
            scraper_override: Optional scraper name to use instead of default
            log_level: Logging level for the worker
        """
        super().__init__(name=f"VenueWorker-{venue}")
        self.venue = venue
        self.years = sorted(years)  # Process years in order
        self.config = config
        self.result_queue = result_queue
        self.scraper_override = scraper_override
        self.log_level = log_level
        
    def run(self):
        """Main worker process loop."""
        # Configure logging for this process
        logging.basicConfig(
            level=self.log_level,
            format=f'%(asctime)s - [{self.venue}] %(name)s - %(levelname)s - %(message)s'
        )
        logger = logging.getLogger(f"worker.{self.venue}")
        
        try:
            # Get appropriate scraper
            registry = get_registry()
            
            if self.scraper_override:
                # User provided specific scraper
                scraper_class = registry._scrapers.get(self.scraper_override)
                if scraper_class:
                    scraper = scraper_class(self.config)
                    logger.info(f"Using override scraper: {self.scraper_override}")
                else:
                    error_msg = f"Unknown scraper {self.scraper_override}"
                    logger.error(error_msg)
                    self._send_error_for_all_years(error_msg)
                    return
            else:
                # Use default scraper for venue
                scraper = registry.get_scraper_for_venue(self.venue, self.config)
                if not scraper:
                    error_msg = f"No scraper available for venue {self.venue}"
                    logger.error(error_msg)
                    self._send_error_for_all_years(error_msg)
                    return
            
            # Process each year
            for year in self.years:
                logger.info(f"Starting collection for {self.venue} {year}")
                
                try:
                    # First, try to estimate paper count
                    estimated_count = None
                    try:
                        estimated_count = scraper.estimate_paper_count(self.venue, year)
                        if estimated_count:
                            # Apply max_papers limit to estimate
                            max_papers = self.config.batch_size if self.config.batch_size < 10000 else None
                            if max_papers and estimated_count > max_papers:
                                estimated_count = max_papers
                            
                            logger.info(f"Estimated {estimated_count} papers for {self.venue} {year}")
                            # Send progress initialization
                            self.result_queue.put(
                                CollectionResult.progress_result(
                                    self.venue, year, estimated_count
                                )
                            )
                    except Exception as e:
                        logger.debug(f"Could not estimate paper count: {e}")
                    
                    # Stream papers one by one
                    paper_count = 0
                    error_count = 0
                    max_papers = self.config.batch_size if self.config.batch_size < 10000 else None
                    
                    for paper in scraper.scrape_venue_year_iter(self.venue, year):
                        try:
                            # Log when putting paper in queue
                            if paper_count == 0:
                                logger.info(f"Putting first paper in queue for {self.venue} {year}")
                            
                            self.result_queue.put(
                                CollectionResult.paper_result(self.venue, year, paper)
                            )
                            paper_count += 1
                            
                            # Check if we've reached the max_papers limit
                            if max_papers and paper_count >= max_papers:
                                logger.info(f"Reached max_papers limit ({max_papers}), stopping")
                                break
                            
                            # Log progress periodically
                            if paper_count % 100 == 0:
                                logger.info(f"Collected {paper_count} papers so far")
                                
                        except Exception as e:
                            error_count += 1
                            logger.warning(f"Error sending paper to queue: {e}")
                            if error_count > 10:
                                logger.error("Too many errors sending papers to queue, stopping")
                                break
                    
                    logger.info(f"Completed {self.venue} {year}: collected {paper_count} papers")
                    
                    # Signal completion of venue/year
                    self.result_queue.put(
                        CollectionResult.completion_result(self.venue, year)
                    )
                    
                except Exception as e:
                    error_msg = f"Error collecting {self.venue} {year}: {str(e)}"
                    logger.error(error_msg)
                    logger.debug(traceback.format_exc())
                    
                    self.result_queue.put(
                        CollectionResult.error_result(self.venue, year, error_msg)
                    )
                    
                    # Signal completion even on error
                    self.result_queue.put(
                        CollectionResult.completion_result(self.venue, year)
                    )
            
            logger.info(f"Worker completed all years for {self.venue}")
            
        except Exception as e:
            logger.error(f"Worker crashed: {e}")
            logger.debug(traceback.format_exc())
            
        finally:
            # Always signal worker completion
            self.result_queue.put(CollectionResult.worker_done_result())
    
    def _send_error_for_all_years(self, error_msg: str):
        """Send error results for all years when scraper unavailable."""
        for year in self.years:
            self.result_queue.put(
                CollectionResult.error_result(self.venue, year, error_msg)
            )
            self.result_queue.put(
                CollectionResult.completion_result(self.venue, year)
            )
        
        # Signal worker done
        self.result_queue.put(CollectionResult.worker_done_result())