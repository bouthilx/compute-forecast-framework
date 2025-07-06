"""
CollectionDashboard - Flask-SocketIO server for real-time collection monitoring.
Provides WebSocket-based dashboard with <100ms update latency requirement.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import logging
from pathlib import Path

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit
import eventlet

from .dashboard_metrics import SystemMetrics, MetricsBuffer, DashboardStatus
from .metrics_collector import MetricsCollector

logger = logging.getLogger(__name__)


class CollectionDashboard:
    """
    Real-time collection dashboard server with WebSocket updates.

    Performance requirements:
    - <2 second dashboard load time
    - <100ms WebSocket update latency
    - Real-time venue progress grid (25x6 venue/year matrix)
    """

    def __init__(self,
                 host: str = '127.0.0.1',
                 port: int = 5000,
                 debug: bool = False,
                 update_interval_seconds: int = 5):
        self.host = host
        self.port = port
        self.debug = debug
        self.update_interval = update_interval_seconds

        # Flask app setup
        self.app = Flask(__name__,
                        template_folder=str(Path(__file__).parent / 'templates'),
                        static_folder=str(Path(__file__).parent / 'static'))
        self.app.config['SECRET_KEY'] = 'collection-dashboard-secret'

        # SocketIO setup
        self.socketio = SocketIO(self.app,
                               cors_allowed_origins="*",
                               async_mode='eventlet',
                               logger=False,
                               engineio_logger=False)

        # Dashboard state
        self.status = DashboardStatus(
            is_running=False,
            connected_clients=0,
            port=port,
            uptime_seconds=0.0,
            messages_sent=0,
            last_broadcast_time=None,
            server_start_time=datetime.now()
        )

        # Metrics collector
        self.metrics_collector: Optional[MetricsCollector] = None
        self._running = False
        self._broadcast_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        # Setup routes
        self._setup_routes()
        self._setup_socketio_events()

    def start_dashboard(self, metrics_collector: MetricsCollector) -> None:
        """
        Start dashboard web server and metric broadcasting
        
        REQUIREMENTS:
        - Must serve web interface on specified port
        - Must start WebSocket server for real-time updates
        - Must begin metric collection and broadcasting
        - Must be non-blocking (run in separate thread)
        """
        with self._lock:
            if self._running:
                logger.warning("Dashboard already running")
                return
            
            self.metrics_collector = metrics_collector
            self._running = True
            self.status.is_running = True
            self.status.server_start_time = datetime.now()
            
            # Start broadcast thread
            self._broadcast_thread = threading.Thread(
                target=self._broadcast_loop,
                name="DashboardBroadcast",
                daemon=True
            )
            self._broadcast_thread.start()
            
            # Start Flask-SocketIO server
            logger.info(f"Starting dashboard server on {self.host}:{self.port}")
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=False,
                log_output=False
            )

    def stop_dashboard(self) -> None:
        """Gracefully stop dashboard server"""
        with self._lock:
            if not self._running:
                return
            
            self._running = False
            self.status.is_running = False
            
            # Stop SocketIO server
            if self.socketio:
                self.socketio.stop()
            
            # Wait for broadcast thread
            if self._broadcast_thread and self._broadcast_thread.is_alive():
                self._broadcast_thread.join(timeout=5)
            
            logger.info("Dashboard server stopped")

    def broadcast_metrics(self, metrics: SystemMetrics) -> None:
        """
        Broadcast metrics to all connected clients
        
        REQUIREMENTS:
        - Must send to all connected WebSocket clients
        - Must handle disconnected clients gracefully
        - Must complete within 100ms
        """
        if not self.socketio or not self._running:
            return
        
        broadcast_start = time.time()
        
        try:
            # Format metrics for frontend
            metrics_data = self._format_metrics_for_frontend(metrics)
            
            # Broadcast to all connected clients
            self.socketio.emit('metrics_update', {
                'timestamp': metrics.timestamp.isoformat(),
                'system_metrics': metrics_data
            }, broadcast=True)
            
            # Update broadcast statistics
            self.status.update_broadcast_stats()
            
            broadcast_time = (time.time() - broadcast_start) * 1000  # Convert to ms
            
            if broadcast_time > 100:
                logger.warning(f"Metrics broadcast took {broadcast_time:.1f}ms (>100ms limit)")
                
        except Exception as e:
            logger.error(f"Failed to broadcast metrics: {e}")

    def _setup_routes(self):
        """Setup Flask routes for REST API"""
        
        @self.app.route('/')
        def dashboard_home():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/metrics')
        def get_current_metrics():
            """GET /api/metrics - Current system metrics"""
            try:
                if not self.metrics_collector:
                    return jsonify({'error': 'Metrics collector not available'}), 503
                
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if not current_metrics:
                    return jsonify({'error': 'No metrics available'}), 404
                
                metrics_data = self._format_metrics_for_frontend(current_metrics)
                return jsonify({
                    'timestamp': current_metrics.timestamp.isoformat(),
                    'metrics': metrics_data
                })
                
            except Exception as e:
                logger.error(f"Error getting current metrics: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/venues')
        def get_venue_progress():
            """GET /api/venues - Venue collection progress"""
            try:
                if not self.metrics_collector:
                    return jsonify({'error': 'Metrics collector not available'}), 503
                
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if not current_metrics:
                    return jsonify({'venues': {}})
                
                # Format venue progress for grid display
                venues_data = {}
                for venue_key, progress in current_metrics.venue_progress.items():
                    venue_name = progress.venue_name
                    year = progress.year
                    
                    if venue_name not in venues_data:
                        venues_data[venue_name] = {}
                    
                    venues_data[venue_name][str(year)] = {
                        'status': progress.status,
                        'papers': progress.papers_collected,
                        'target': progress.target_papers,
                        'completion_percentage': progress.completion_percentage,
                        'last_update': progress.last_update_time.isoformat()
                    }
                
                return jsonify({'venues': venues_data})
                
            except Exception as e:
                logger.error(f"Error getting venue progress: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/status')
        def get_dashboard_status():
            """GET /api/status - Dashboard server status"""
            with self._lock:
                uptime = (datetime.now() - self.status.server_start_time).total_seconds()
                
                return jsonify({
                    'is_running': self.status.is_running,
                    'connected_clients': self.status.connected_clients,
                    'uptime_seconds': uptime,
                    'messages_sent': self.status.messages_sent,
                    'last_broadcast': self.status.last_broadcast_time.isoformat() if self.status.last_broadcast_time else None
                })
        
        @self.app.route('/api/metrics/history')
        def get_metrics_history():
            """GET /api/metrics/history - Historical metrics"""
            try:
                if not self.metrics_collector:
                    return jsonify({'error': 'Metrics collector not available'}), 503
                
                # Get time range from query params
                minutes = request.args.get('minutes', default=60, type=int)
                
                # Get metrics from buffer
                history = self.metrics_collector.metrics_buffer.get_metrics_since(
                    datetime.now() - timedelta(minutes=minutes)
                )
                
                # Format for frontend
                formatted_history = []
                for metrics in history:
                    formatted_history.append({
                        'timestamp': metrics.timestamp.isoformat(),
                        'metrics': self._format_metrics_for_frontend(metrics)
                    })
                
                return jsonify({
                    'history': formatted_history,
                    'count': len(formatted_history)
                })
                
            except Exception as e:
                logger.error(f"Error getting metrics history: {e}")
                return jsonify({'error': str(e)}), 500

    def _setup_socketio_events(self):
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection"""
            with self._lock:
                self.status.connected_clients += 1
            
            logger.info(f"Client connected. Total clients: {self.status.connected_clients}")
            
            # Send current metrics to new client
            if self.metrics_collector:
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if current_metrics:
                    emit('metrics_update', {
                        'timestamp': current_metrics.timestamp.isoformat(),
                        'system_metrics': self._format_metrics_for_frontend(current_metrics)
                    })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            with self._lock:
                self.status.connected_clients = max(0, self.status.connected_clients - 1)
            
            logger.info(f"Client disconnected. Total clients: {self.status.connected_clients}")
        
        @self.socketio.on('request_metrics')
        def handle_metrics_request():
            """Handle explicit metrics request from client"""
            if self.metrics_collector:
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if current_metrics:
                    emit('metrics_update', {
                        'timestamp': current_metrics.timestamp.isoformat(),
                        'system_metrics': self._format_metrics_for_frontend(current_metrics)
                    })

    def _broadcast_loop(self):
        """Background thread for broadcasting metrics"""
        logger.info("Starting metrics broadcast loop")
        
        while self._running:
            try:
                # Sleep for update interval
                time.sleep(self.update_interval)
                
                # Skip if no clients connected
                if self.status.connected_clients == 0:
                    continue
                
                # Get current metrics
                if self.metrics_collector:
                    current_metrics = self.metrics_collector.get_current_metrics()
                    if current_metrics:
                        self.broadcast_metrics(current_metrics)
                        
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
        
        logger.info("Metrics broadcast loop stopped")

    def _format_metrics_for_frontend(self, metrics: SystemMetrics) -> Dict[str, Any]:
        """Format metrics for frontend consumption"""
        return {
            'collection_progress': {
                'total_venues': metrics.collection_progress.total_venues,
                'completed_venues': metrics.collection_progress.completed_venues,
                'in_progress_venues': metrics.collection_progress.in_progress_venues,
                'failed_venues': metrics.collection_progress.failed_venues,
                'papers_collected': metrics.collection_progress.papers_collected,
                'papers_per_minute': round(metrics.collection_progress.papers_per_minute, 2),
                'completion_percentage': round(metrics.collection_progress.completion_percentage, 2),
                'estimated_remaining_minutes': round(metrics.collection_progress.estimated_remaining_minutes, 1)
            },
            'api_health': {
                api_name: {
                    'status': api.health_status,
                    'success_rate': round(api.success_rate * 100, 1),
                    'avg_response_time': round(api.avg_response_time_ms, 1),
                    'requests_made': api.requests_made,
                    'papers_collected': api.papers_collected
                }
                for api_name, api in metrics.api_metrics.items()
            },
            'processing': {
                'papers_processed': metrics.processing_metrics.papers_processed,
                'papers_deduplicated': metrics.processing_metrics.papers_deduplicated,
                'duplicates_removed': metrics.processing_metrics.duplicates_removed,
                'papers_above_threshold': metrics.processing_metrics.papers_above_threshold,
                'breakthrough_papers_found': metrics.processing_metrics.breakthrough_papers_found
            },
            'system_resources': {
                'cpu_usage': round(metrics.system_metrics.cpu_usage_percent, 1),
                'memory_usage': round(metrics.system_metrics.memory_usage_percent, 1),
                'disk_usage': round(metrics.system_metrics.disk_usage_percent, 1),
                'network_sent_mb': round(metrics.system_metrics.network_sent_mb, 2),
                'network_recv_mb': round(metrics.system_metrics.network_recv_mb, 2)
            }
        }


def create_dashboard(host: str = '127.0.0.1',
                    port: int = 5000,
                    debug: bool = False) -> CollectionDashboard:
    """Factory function to create dashboard instance"""
    return CollectionDashboard(host=host, port=port, debug=debug)