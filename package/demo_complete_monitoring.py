#!/usr/bin/env python3
"""
Complete Monitoring System Demo - Dashboard + Intelligent Alerting

Demonstrates the full monitoring system with real-time dashboard and
intelligent alerting working together to monitor collection sessions.
"""

import sys
import time
import logging
import signal
import threading
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from src.monitoring.dashboard_server import CollectionDashboard
from src.monitoring.metrics_collector import MetricsCollector
from src.monitoring.alert_system import IntelligentAlertSystem
from src.monitoring.alert_structures import AlertConfiguration
from src.monitoring.integration_utils import DashboardIntegration


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CompleteMonitoringDemo:
    """Demo class for complete monitoring system"""
    
    def __init__(self, dashboard_port: int = 8080):
        self.dashboard_port = dashboard_port
        
        # Components
        self.dashboard = None
        self.metrics_collector = None
        self.alert_system = None
        self.integration = None
        
        # Control
        self.running = False
        self.alert_monitor_thread = None
        
    def start_demo(self):
        """Start the complete monitoring demo"""
        logger.info("Starting Complete Monitoring System Demo")
        
        try:
            # Create mock integration components
            self.integration = DashboardIntegration()
            self.integration.create_mock_components()
            
            # Initialize alert system
            alert_config = AlertConfiguration(
                collection_rate_threshold=8.0,  # Lower threshold for demo
                api_error_rate_threshold=0.15,  # Higher threshold for demo
                memory_usage_threshold=0.85,    # Higher threshold for demo
                console_notifications=True,
                dashboard_notifications=True
            )
            
            self.alert_system = IntelligentAlertSystem(alert_config)
            
            # Initialize metrics collector
            self.metrics_collector = MetricsCollector(collection_interval_seconds=3)
            
            # Start metrics collection
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
                port=self.dashboard_port,
                update_interval_seconds=5
            )
            
            self.dashboard.start_dashboard(self.metrics_collector)
            
            # Connect alert system to dashboard
            self.alert_system.set_dashboard_server(self.dashboard)
            
            # Start alert monitoring
            self.running = True
            self.alert_monitor_thread = threading.Thread(
                target=self._alert_monitoring_loop,
                name="AlertMonitor",
                daemon=True
            )
            self.alert_monitor_thread.start()
            
            # Print startup information
            logger.info("Complete monitoring system started successfully!")
            logger.info(f"Dashboard: http://localhost:{self.dashboard_port}")
            logger.info("Alert system: Active with console and dashboard notifications")
            logger.info("Press Ctrl+C to stop the demo")
            
            # Demonstrate alerting capabilities
            self._demonstrate_alerting()
            
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
        """Main demo loop with status updates"""
        start_time = time.time()
        last_alert_demo = 0
        
        while self.running:
            try:
                elapsed_minutes = (time.time() - start_time) / 60
                
                # Print periodic status updates
                if int(elapsed_minutes) % 3 == 0 and elapsed_minutes > 0:
                    self._print_system_status()
                
                # Demonstrate different alert scenarios every 5 minutes
                if int(elapsed_minutes) % 5 == 0 and int(elapsed_minutes) != last_alert_demo:
                    last_alert_demo = int(elapsed_minutes)
                    self._trigger_demo_alerts()
                
                time.sleep(10)  # Check every 10 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in demo loop: {e}")
                time.sleep(5)
    
    def _alert_monitoring_loop(self):
        """Continuous alert monitoring loop"""
        logger.info("Alert monitoring started")
        
        while self.running:
            try:
                # Get current metrics
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                
                if current_metrics:
                    # Evaluate alerts
                    triggered_alerts = self.alert_system.evaluate_alerts(current_metrics)
                    
                    # Send alerts if any triggered
                    for alert in triggered_alerts:
                        delivery_result = self.alert_system.send_alert(alert)
                        if delivery_result.success:
                            logger.info(f"Alert delivered: {alert.title} -> {delivery_result.delivery_channels}")
                        else:
                            logger.warning(f"Alert delivery failed: {alert.title} -> {delivery_result.failed_channels}")
                
                # Check every 10 seconds
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in alert monitoring: {e}")
                time.sleep(5)
        
        logger.info("Alert monitoring stopped")
    
    def _demonstrate_alerting(self):
        """Demonstrate various alerting capabilities"""
        logger.info("=== Alerting System Demonstration ===")
        
        # Show configured rules
        alert_summary = self.alert_system.get_alert_summary(1)  # Last 1 hour
        system_status = self.alert_system.get_system_status()
        
        logger.info(f"Alert rules configured: {system_status['total_rules']}")
        logger.info(f"Alert rules enabled: {system_status['enabled_rules']}")
        logger.info("Built-in alert rules:")
        
        for rule_id, rule in self.alert_system.alert_rules.items():
            if rule.enabled:
                logger.info(f"  - {rule.rule_name} ({rule.severity})")
        
        # Demonstrate suppression
        logger.info("\nDemonstrating alert suppression...")
        self.alert_system.suppress_alerts(
            alert_pattern="test",
            duration_minutes=5,
            reason="Demo suppression rule"
        )
        
        suppression_stats = self.alert_system.suppression_manager.get_suppression_statistics()
        logger.info(f"Active suppressions: {suppression_stats['total_active_suppressions']}")
    
    def _trigger_demo_alerts(self):
        """Trigger some demo alerts to show the system working"""
        logger.info("=== Triggering Demo Alerts ===")
        
        # This would normally be done by the metrics triggering the conditions
        # For demo, we'll manually create some alerts
        from src.monitoring.alert_structures import Alert
        
        demo_alert = Alert(
            alert_id=f"demo_alert_{int(time.time())}",
            rule_id="demo_rule",
            timestamp=datetime.now(),
            severity="warning",
            title="Demo Alert - Collection Rate Variation",
            message="This is a demonstration alert showing system monitoring capabilities",
            affected_components=["demo_system"],
            current_value=5.5,
            threshold_value=8.0,
            metrics_context={"demo": True},
            recommended_actions=[
                "This is a demo - no action needed",
                "Check dashboard for real-time metrics"
            ],
            status="active"
        )
        
        # Send through alert system (will use notification channels)
        delivery_result = self.alert_system.send_alert(demo_alert)
        logger.info(f"Demo alert sent to: {delivery_result.delivery_channels}")
    
    def _print_system_status(self):
        """Print current system status"""
        try:
            # Get metrics
            current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
            if not current_metrics:
                return
            
            # Get alert system status
            alert_status = self.alert_system.get_system_status()
            alert_summary = self.alert_system.get_alert_summary(1)
            
            logger.info("=== System Status ===")
            logger.info(f"Papers Collected: {current_metrics.collection_progress.papers_collected}")
            logger.info(f"Collection Rate: {current_metrics.collection_progress.papers_per_minute:.1f} papers/min")
            logger.info(f"Memory Usage: {current_metrics.system_metrics.memory_usage_percentage:.1f}%")
            logger.info(f"Alerts (1h): {alert_summary.total_alerts}")
            logger.info(f"Alert Evaluations: {alert_status['evaluation_stats']['total_evaluations']}")
            logger.info(f"Dashboard Clients: {self.dashboard.status.connected_clients}")
            
        except Exception as e:
            logger.debug(f"Error printing status: {e}")
    
    def stop_demo(self):
        """Stop the complete monitoring demo"""
        logger.info("Stopping complete monitoring demo...")
        
        self.running = False
        
        # Stop alert monitoring
        if self.alert_monitor_thread and self.alert_monitor_thread.is_alive():
            self.alert_monitor_thread.join(timeout=5)
        
        # Stop dashboard
        if self.dashboard:
            try:
                self.dashboard.stop_dashboard()
                logger.info("Dashboard stopped")
            except Exception as e:
                logger.error(f"Error stopping dashboard: {e}")
        
        # Stop metrics collection
        if self.metrics_collector:
            try:
                self.metrics_collector.stop_collection()
                logger.info("Metrics collection stopped")
            except Exception as e:
                logger.error(f"Error stopping metrics collector: {e}")
        
        # Print final statistics
        if self.alert_system:
            try:
                final_summary = self.alert_system.get_alert_summary(24)
                logger.info(f"Final alert summary - Total: {final_summary.total_alerts}, "
                           f"Trend: {final_summary.alert_rate_trend}")
            except Exception as e:
                logger.debug(f"Error getting final summary: {e}")
        
        logger.info("Complete monitoring demo stopped")


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
    parser = argparse.ArgumentParser(description='Complete Monitoring System Demo')
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
    
    # Print startup information
    logger.info("=== Complete Monitoring System Demo ===")
    logger.info("This demo showcases:")
    logger.info("  • Real-time collection dashboard")
    logger.info("  • Intelligent alerting system")
    logger.info("  • Alert suppression and routing")
    logger.info("  • Multi-channel notifications")
    logger.info("  • System health monitoring")
    logger.info("")
    
    # Create and start demo
    demo_instance = CompleteMonitoringDemo(dashboard_port=args.port)
    
    try:
        demo_instance.start_demo()
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    demo_instance = None
    main()