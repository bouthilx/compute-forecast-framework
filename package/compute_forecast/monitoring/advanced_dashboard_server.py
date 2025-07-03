"""
Advanced Analytics Dashboard Server for Issue #14.
Enhances the existing dashboard with real-time analytics, trend analysis,
performance analytics, and predictive modeling capabilities.
"""

import time
import threading
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

from .dashboard_server import CollectionDashboard
from .advanced_analytics_engine import (
    AdvancedAnalyticsEngine, 
    AnalyticsTimeWindow,
    TrendAnalysis,
    PerformanceAnalytics,
    PredictiveAnalytics,
    AnalyticsSummary
)
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class AdvancedAnalyticsDashboard(CollectionDashboard):
    """
    Enhanced dashboard with advanced analytics capabilities.
    
    Features:
    - Real-time analytics visualization
    - Historical trend analysis with interactive charts
    - Performance analytics for APIs, venues, and collection efficiency
    - Predictive analytics for collection forecasting
    - Custom dashboard configuration and user preferences
    - Export capabilities for reports and data
    - Advanced filtering and drill-down functionality
    """
    
    def __init__(self, 
                 host: str = '127.0.0.1', 
                 port: int = 5000,
                 debug: bool = False,
                 enable_advanced_analytics: bool = True):
        
        # Initialize base dashboard
        super().__init__(host, port, debug)
        
        # Advanced analytics components
        self.enable_advanced_analytics = enable_advanced_analytics
        self.analytics_engine: Optional[AdvancedAnalyticsEngine] = None
        
        if enable_advanced_analytics:
            self.analytics_engine = AdvancedAnalyticsEngine()
        
        # Analytics state
        self._analytics_running = False
        self._analytics_thread: Optional[threading.Thread] = None
        
        # Dashboard configuration
        self.dashboard_config = {
            'refresh_interval_seconds': 5,
            'analytics_cache_duration': 60,
            'chart_data_points': 100,
            'trend_analysis_hours': 6,
            'enable_predictions': True,
            'enable_custom_metrics': True
        }
        
        # Setup enhanced routes
        self._setup_analytics_routes()
        self._setup_enhanced_socketio_events()
        
        logger.info("AdvancedAnalyticsDashboard initialized")
    
    def start_server(self, use_reloader: bool = False) -> None:
        """Start the enhanced dashboard server with analytics"""
        # Start analytics engine
        if self.analytics_engine:
            self.analytics_engine.start()
            self._start_analytics_integration()
        
        # Start base dashboard
        super().start_server(use_reloader)
    
    def stop_server(self) -> None:
        """Stop the enhanced dashboard server"""
        # Stop analytics components
        if self.analytics_engine:
            self.analytics_engine.stop()
        
        self._analytics_running = False
        if self._analytics_thread:
            self._analytics_thread.join(timeout=5.0)
        
        # Stop base dashboard
        super().stop_server()
    
    def set_metrics_collector(self, collector: MetricsCollector) -> None:
        """Set metrics collector and integrate with analytics engine"""
        super().set_metrics_collector(collector)
        
        # Integrate with analytics engine
        if self.analytics_engine:
            self._integrate_analytics_with_metrics()
    
    def _setup_analytics_routes(self) -> None:
        """Setup advanced analytics HTTP routes"""
        
        @self.app.route('/api/analytics/trends/<metric_name>')
        def get_trend_analysis(metric_name):
            """Get trend analysis for specific metric"""
            if not self.analytics_engine:
                return jsonify({'error': 'Analytics engine not available'}), 503
            
            # Parse time window from query parameters
            hours = request.args.get('hours', 6, type=int)
            time_window = AnalyticsTimeWindow.last_hours(hours)
            
            trend_analysis = self.analytics_engine.get_trend_analysis(metric_name, time_window)
            
            if trend_analysis:
                return jsonify(trend_analysis.to_dict())
            else:
                return jsonify({'error': 'Insufficient data for trend analysis'}), 404
        
        @self.app.route('/api/analytics/performance/<metric_name>')
        def get_performance_analysis(metric_name):
            """Get performance analysis for specific metric"""
            if not self.analytics_engine:
                return jsonify({'error': 'Analytics engine not available'}), 503
            
            performance_analysis = self.analytics_engine.get_performance_analytics(metric_name)
            
            if performance_analysis:
                return jsonify(performance_analysis.to_dict())
            else:
                return jsonify({'error': 'Insufficient data for performance analysis'}), 404
        
        @self.app.route('/api/analytics/predictions/<metric_name>')
        def get_predictive_analysis(metric_name):
            """Get predictive analysis for specific metric"""
            if not self.analytics_engine:
                return jsonify({'error': 'Analytics engine not available'}), 503
            
            predictive_analysis = self.analytics_engine.get_predictive_analytics(metric_name)
            
            if predictive_analysis:
                return jsonify(predictive_analysis.to_dict())
            else:
                return jsonify({'error': 'Insufficient data for predictive analysis'}), 404
        
        @self.app.route('/api/analytics/summary')
        def get_analytics_summary():
            """Get comprehensive analytics summary"""
            if not self.analytics_engine:
                return jsonify({'error': 'Analytics engine not available'}), 503
            
            summary = self.analytics_engine.get_comprehensive_summary()
            return jsonify(summary.to_dict())
        
        @self.app.route('/api/analytics/custom', methods=['POST'])
        def get_custom_analytics():
            """Get custom analytics based on configuration"""
            if not self.analytics_engine:
                return jsonify({'error': 'Analytics engine not available'}), 503
            
            config = request.get_json() or {}
            
            try:
                results = self.analytics_engine.get_custom_analytics(config)
                return jsonify(results)
            except Exception as e:
                logger.error(f"Error in custom analytics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/analytics/export/<format>')
        def export_analytics_data(format):
            """Export analytics data in specified format"""
            if not self.analytics_engine:
                return jsonify({'error': 'Analytics engine not available'}), 503
            
            try:
                # Get comprehensive data
                summary = self.analytics_engine.get_comprehensive_summary()
                
                if format.lower() == 'json':
                    return jsonify({
                        'export_timestamp': datetime.now().isoformat(),
                        'summary': summary.to_dict(),
                        'metadata': {
                            'format': 'json',
                            'version': '1.0'
                        }
                    })
                elif format.lower() == 'csv':
                    # Would implement CSV export here
                    return jsonify({'error': 'CSV export not implemented yet'}), 501
                else:
                    return jsonify({'error': f'Unsupported format: {format}'}), 400
                    
            except Exception as e:
                logger.error(f"Error exporting analytics data: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/analytics')
        def analytics_dashboard():
            """Advanced analytics dashboard page"""
            return render_template('analytics_dashboard.html', config=self.dashboard_config)
        
        @self.app.route('/api/dashboard/config')
        def get_dashboard_config():
            """Get dashboard configuration"""
            return jsonify(self.dashboard_config)
        
        @self.app.route('/api/dashboard/config', methods=['POST'])
        def update_dashboard_config():
            """Update dashboard configuration"""
            try:
                new_config = request.get_json() or {}
                self.dashboard_config.update(new_config)
                
                return jsonify({
                    'status': 'success',
                    'config': self.dashboard_config
                })
            except Exception as e:
                logger.error(f"Error updating dashboard config: {e}")
                return jsonify({'error': str(e)}), 500
    
    def _setup_enhanced_socketio_events(self) -> None:
        """Setup enhanced SocketIO events for real-time analytics"""
        
        @self.socketio.on('request_analytics_summary')
        def handle_analytics_summary_request():
            """Handle analytics summary request"""
            if self.analytics_engine:
                try:
                    summary = self.analytics_engine.get_comprehensive_summary()
                    emit('analytics_summary_update', summary.to_dict())
                except Exception as e:
                    logger.error(f"Error getting analytics summary: {e}")
                    emit('analytics_error', {'error': str(e)})
        
        @self.socketio.on('request_trend_analysis')
        def handle_trend_analysis_request(data):
            """Handle trend analysis request"""
            if not self.analytics_engine:
                emit('analytics_error', {'error': 'Analytics engine not available'})
                return
            
            try:
                metric_name = data.get('metric_name', 'papers_per_minute')
                hours = data.get('hours', 6)
                
                time_window = AnalyticsTimeWindow.last_hours(hours)
                trend = self.analytics_engine.get_trend_analysis(metric_name, time_window)
                
                if trend:
                    emit('trend_analysis_update', {
                        'metric_name': metric_name,
                        'trend': trend.to_dict()
                    })
                else:
                    emit('analytics_error', {'error': f'No trend data available for {metric_name}'})
                    
            except Exception as e:
                logger.error(f"Error in trend analysis request: {e}")
                emit('analytics_error', {'error': str(e)})
        
        @self.socketio.on('request_performance_analysis')
        def handle_performance_analysis_request(data):
            """Handle performance analysis request"""
            if not self.analytics_engine:
                emit('analytics_error', {'error': 'Analytics engine not available'})
                return
            
            try:
                metric_name = data.get('metric_name', 'papers_per_minute')
                
                performance = self.analytics_engine.get_performance_analytics(metric_name)
                
                if performance:
                    emit('performance_analysis_update', {
                        'metric_name': metric_name,
                        'performance': performance.to_dict()
                    })
                else:
                    emit('analytics_error', {'error': f'No performance data available for {metric_name}'})
                    
            except Exception as e:
                logger.error(f"Error in performance analysis request: {e}")
                emit('analytics_error', {'error': str(e)})
        
        @self.socketio.on('request_predictions')
        def handle_predictions_request(data):
            """Handle predictions request"""
            if not self.analytics_engine:
                emit('analytics_error', {'error': 'Analytics engine not available'})
                return
            
            try:
                metric_name = data.get('metric_name', 'papers_per_minute')
                
                predictions = self.analytics_engine.get_predictive_analytics(metric_name)
                
                if predictions:
                    emit('predictions_update', {
                        'metric_name': metric_name,
                        'predictions': predictions.to_dict()
                    })
                else:
                    emit('analytics_error', {'error': f'No prediction data available for {metric_name}'})
                    
            except Exception as e:
                logger.error(f"Error in predictions request: {e}")
                emit('analytics_error', {'error': str(e)})
        
        @self.socketio.on('request_custom_analytics')
        def handle_custom_analytics_request(data):
            """Handle custom analytics request"""
            if not self.analytics_engine:
                emit('analytics_error', {'error': 'Analytics engine not available'})
                return
            
            try:
                config = data.get('config', {})
                results = self.analytics_engine.get_custom_analytics(config)
                
                emit('custom_analytics_update', {
                    'config': config,
                    'results': results
                })
                
            except Exception as e:
                logger.error(f"Error in custom analytics request: {e}")
                emit('analytics_error', {'error': str(e)})
    
    def _start_analytics_integration(self) -> None:
        """Start analytics integration thread"""
        self._analytics_running = True
        self._analytics_thread = threading.Thread(
            target=self._analytics_integration_loop,
            daemon=True,
            name="AnalyticsIntegration"
        )
        self._analytics_thread.start()
    
    def _analytics_integration_loop(self) -> None:
        """Analytics integration loop for real-time updates"""
        while self._analytics_running:
            try:
                # Broadcast analytics updates
                if self.analytics_engine:
                    # Get and broadcast analytics summary
                    summary = self.analytics_engine.get_comprehensive_summary()
                    self.socketio.emit('analytics_summary_update', summary.to_dict(), broadcast=True)
                    
                    # Get and broadcast key trend analyses
                    key_metrics = ['papers_per_minute', 'memory_usage_percent', 'cpu_usage_percent']
                    for metric in key_metrics:
                        trend = self.analytics_engine.get_trend_analysis(metric)
                        if trend:
                            self.socketio.emit('trend_analysis_update', {
                                'metric_name': metric,
                                'trend': trend.to_dict()
                            }, broadcast=True)
                
                # Sleep for configured interval
                time.sleep(self.dashboard_config['refresh_interval_seconds'])
                
            except Exception as e:
                logger.error(f"Error in analytics integration loop: {e}")
                time.sleep(5)  # Short delay on error
    
    def _integrate_analytics_with_metrics(self) -> None:
        """Integrate analytics engine with metrics collector"""
        if not self.analytics_engine or not self.metrics_collector:
            return
        
        # Create a wrapper to feed metrics to analytics engine
        original_collect = self.metrics_collector.collect_current_metrics
        
        def enhanced_collect():
            """Enhanced metrics collection that feeds analytics engine"""
            metrics = original_collect()
            
            # Feed metrics to analytics engine
            if self.analytics_engine and metrics:
                self.analytics_engine.add_metrics_data(metrics)
            
            return metrics
        
        # Replace the collection method
        self.metrics_collector.collect_current_metrics = enhanced_collect
        
        logger.info("Analytics engine integrated with metrics collector")
    
    def broadcast_analytics_update(self, analytics_type: str, data: Dict[str, Any]) -> None:
        """Broadcast analytics update to connected clients"""
        try:
            event_name = f"analytics_{analytics_type}_update"
            self.socketio.emit(event_name, data, broadcast=True)
        except Exception as e:
            logger.error(f"Error broadcasting analytics update: {e}")
    
    def get_analytics_engine(self) -> Optional[AdvancedAnalyticsEngine]:
        """Get analytics engine reference"""
        return self.analytics_engine
    
    def set_analytics_config(self, config: Dict[str, Any]) -> None:
        """Update analytics configuration"""
        if self.analytics_engine:
            # Update analytics engine configuration
            for key, value in config.items():
                if hasattr(self.analytics_engine, key):
                    setattr(self.analytics_engine, key, value)
        
        # Update dashboard configuration
        self.dashboard_config.update(config)
        
        logger.info(f"Analytics configuration updated: {config}")


# Factory function for creating enhanced dashboard
def create_advanced_analytics_dashboard(
    host: str = '127.0.0.1',
    port: int = 5000,
    debug: bool = False,
    analytics_config: Optional[Dict[str, Any]] = None
) -> AdvancedAnalyticsDashboard:
    """
    Create and configure advanced analytics dashboard
    
    Args:
        host: Dashboard host address
        port: Dashboard port
        debug: Enable debug mode
        analytics_config: Analytics configuration
    
    Returns:
        Configured AdvancedAnalyticsDashboard instance
    """
    dashboard = AdvancedAnalyticsDashboard(host, port, debug)
    
    if analytics_config:
        dashboard.set_analytics_config(analytics_config)
    
    return dashboard


# Integration utilities
class AnalyticsDashboardAdapter:
    """Adapter for integrating analytics dashboard with existing systems"""
    
    def __init__(self, dashboard: AdvancedAnalyticsDashboard):
        self.dashboard = dashboard
    
    def integrate_with_alerting_system(self, alerting_system) -> None:
        """Integrate dashboard with alerting system"""
        try:
            # Add dashboard notification channel to alerting system
            from .notification_channels import DashboardNotificationChannel
            
            dashboard_channel = DashboardNotificationChannel(
                "analytics_dashboard",
                self.dashboard
            )
            
            if hasattr(alerting_system, 'add_notification_channel'):
                alerting_system.add_notification_channel(dashboard_channel)
            
            logger.info("Analytics dashboard integrated with alerting system")
            
        except Exception as e:
            logger.error(f"Error integrating with alerting system: {e}")
    
    def setup_custom_metrics(self, custom_metrics: List[Dict[str, Any]]) -> None:
        """Setup custom metrics for analytics"""
        try:
            analytics_engine = self.dashboard.get_analytics_engine()
            if analytics_engine:
                # Configure custom metrics
                config = {'custom_metrics': custom_metrics}
                results = analytics_engine.get_custom_analytics(config)
                
                logger.info(f"Setup {len(custom_metrics)} custom metrics")
            
        except Exception as e:
            logger.error(f"Error setting up custom metrics: {e}")
    
    def export_analytics_report(self, format: str = 'json') -> Dict[str, Any]:
        """Export comprehensive analytics report"""
        try:
            analytics_engine = self.dashboard.get_analytics_engine()
            if not analytics_engine:
                return {'error': 'Analytics engine not available'}
            
            # Generate comprehensive report
            summary = analytics_engine.get_comprehensive_summary()
            
            # Add trend analyses for key metrics
            key_metrics = ['papers_per_minute', 'memory_usage_percent', 'cpu_usage_percent', 'api_success_rate']
            trends = {}
            
            for metric in key_metrics:
                trend = analytics_engine.get_trend_analysis(metric)
                if trend:
                    trends[metric] = trend.to_dict()
            
            # Add performance analyses
            performance = {}
            for metric in key_metrics:
                perf = analytics_engine.get_performance_analytics(metric)
                if perf:
                    performance[metric] = perf.to_dict()
            
            # Add predictions
            predictions = {}
            for metric in key_metrics:
                pred = analytics_engine.get_predictive_analytics(metric)
                if pred:
                    predictions[metric] = pred.to_dict()
            
            report = {
                'export_timestamp': datetime.now().isoformat(),
                'format': format,
                'summary': summary.to_dict(),
                'trend_analyses': trends,
                'performance_analyses': performance,
                'predictions': predictions,
                'metadata': {
                    'version': '1.0',
                    'generator': 'AdvancedAnalyticsDashboard'
                }
            }
            
            return report
            
        except Exception as e:
            logger.error(f"Error exporting analytics report: {e}")
            return {'error': str(e)}


# Example configuration
EXAMPLE_ANALYTICS_CONFIG = {
    'refresh_interval_seconds': 5,
    'analytics_cache_duration': 60,
    'chart_data_points': 100,
    'trend_analysis_hours': 6,
    'enable_predictions': True,
    'enable_custom_metrics': True,
    'custom_metrics': [
        {
            'name': 'collection_efficiency',
            'calculation': 'papers_per_minute / (memory_usage / 100)'
        },
        {
            'name': 'system_health_index',
            'calculation': '(100 - memory_usage) * (100 - cpu_usage) / 10000'
        }
    ]
}