#!/usr/bin/env python3
"""
Demo script for the Real-Time Collection Dashboard.

This script demonstrates the dashboard functionality with mock data,
showing how it integrates with the metrics collector and provides
real-time monitoring of collection progress.
"""

import sys
import time
import logging
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.monitoring.dashboard_server import CollectionDashboard
from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.integration_utils import DashboardIntegration


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DashboardDemo:
    """Demo class for testing dashboard functionality"""
    
    def __init__(self, port: int = 8080):
        self.port = port
        self.dashboard = None
        self.metrics_collector = None
        self.integration = None
        self.running = False
        
    def start_demo(self):
        """Start the dashboard demo"""
        logger.info("Starting Collection Dashboard Demo")
        
        try:
            # Create mock integration components
            self.integration = DashboardIntegration()
            self.integration.create_mock_components()
            
            # Initialize metrics collector
            self.metrics_collector = MetricsCollector(collection_interval_seconds=3)
            
            # Start metrics collection with mock components
            self.metrics_collector.start_collection(
                venue_engine=self.integration.venue_adapter,
                state_manager=self.integration.state_adapter,
                data_processors={
                    'venue_normalizer': self.integration.processor_adapter,
                    'deduplicator': self.integration.processor_adapter,
                    'computational_filter': self.integration.processor_adapter
                }
            )
            
            # Initialize and start dashboard
            self.dashboard = CollectionDashboard(
                port=self.port,
                update_interval_seconds=5
            )
            
            self.dashboard.start_dashboard(self.metrics_collector)
            
            self.running = True
            
            # Print connection info
            logger.info(f"Dashboard started successfully!")
            logger.info(f"Open your browser to: http://localhost:{self.port}")
            logger.info("Press Ctrl+C to stop the demo")
            
            # Keep the demo running
            self.run_demo_loop()
            
        except KeyboardInterrupt:
            logger.info("Demo interrupted by user")
        except Exception as e:
            logger.error(f"Demo failed: {e}")
            raise
        finally:
            self.stop_demo()
    
    def run_demo_loop(self):
        """Main demo loop"""
        start_time = time.time()
        
        while self.running:
            try:
                # Print periodic status updates
                elapsed_minutes = (time.time() - start_time) / 60
                
                if int(elapsed_minutes) % 2 == 0 and elapsed_minutes > 0:
                    # Get current metrics for status update
                    try:
                        current_metrics = self.metrics_collector.collect_current_metrics()
                        papers_collected = current_metrics.collection_progress.papers_collected
                        collection_rate = current_metrics.collection_progress.papers_per_minute
                        
                        logger.info(f"Demo Status - Papers: {papers_collected}, Rate: {collection_rate:.1f}/min, "
                                  f"Runtime: {elapsed_minutes:.1f} minutes")
                    except Exception as e:
                        logger.debug(f"Could not get metrics for status: {e}")
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in demo loop: {e}")
                time.sleep(5)
    
    def stop_demo(self):
        """Stop the dashboard demo"""
        logger.info("Stopping dashboard demo...")
        
        self.running = False
        
        if self.dashboard:
            try:
                self.dashboard.stop_dashboard()
                logger.info("Dashboard stopped")
            except Exception as e:
                logger.error(f"Error stopping dashboard: {e}")
        
        if self.metrics_collector:
            try:
                self.metrics_collector.stop_collection()
                logger.info("Metrics collection stopped")
            except Exception as e:
                logger.error(f"Error stopping metrics collector: {e}")
        
        logger.info("Demo cleanup complete")


def signal_handler(signum, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal, stopping demo...")
    global demo_instance
    if demo_instance:
        demo_instance.running = False


def main():
    """Main demo function"""
    global demo_instance
    
    # Set up signal handling
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Collection Dashboard Demo')
    parser.add_argument('--port', type=int, default=8080, 
                       help='Port for dashboard server (default: 8080)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check if port is available
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', args.port))
    except OSError:
        logger.error(f"Port {args.port} is already in use. Try a different port with --port")
        sys.exit(1)
    
    # Create and start demo
    demo_instance = DashboardDemo(port=args.port)
    
    try:
        demo_instance.start_demo()
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    demo_instance = None
    main()