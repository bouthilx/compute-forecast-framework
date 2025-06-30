"""
<<<<<<< HEAD
CollectionDashboard - Flask-based real-time monitoring dashboard.

Provides WebSocket-based dashboard for monitoring 4-6 hour collection sessions
with comprehensive visibility into collection progress, API health, and data quality.
"""

import json
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import eventlet

from .metrics_collector import MetricsCollector
from .dashboard_metrics import DashboardStatus, SystemMetrics

=======
CollectionDashboard - Flask-SocketIO server for real-time collection monitoring.
Provides WebSocket-based dashboard with <100ms update latency requirement.
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import json
import logging

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

from .dashboard_metrics import SystemMetrics, MetricsBuffer
from .metrics_collector import MetricsCollector
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)

logger = logging.getLogger(__name__)


class CollectionDashboard:
    """
<<<<<<< HEAD
    WebSocket-based dashboard for real-time collection monitoring
    
    Provides comprehensive visibility into collection progress, API health,
    and data quality with live updates during 4-6 hour sessions.
    """
    
    def __init__(self, port: int = 8080, update_interval_seconds: int = 5, metrics_buffer_size: int = 1000):
        self.port = port
        self.update_interval = update_interval_seconds
        self.metrics_buffer_size = metrics_buffer_size
        
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
        
        # Components
        self.metrics_collector: Optional[MetricsCollector] = None
        self.app: Optional[Flask] = None
        self.socketio: Optional[SocketIO] = None
        self.server_thread: Optional[threading.Thread] = None
        self.broadcast_thread: Optional[threading.Thread] = None
        
        # Thread control
        self.should_broadcast = False
        self._lock = threading.RLock()
        
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
            if self.status.is_running:
                logger.warning("Dashboard already running")
                return
            
            # Store metrics collector
            self.metrics_collector = metrics_collector
            
            # Initialize Flask app and SocketIO
            self._setup_flask_app()
            
            # Start server in separate thread
            self.status.is_running = True
            self.status.server_start_time = datetime.now()
            self.should_broadcast = True
            
            self.server_thread = threading.Thread(
                target=self._run_server,
                name="DashboardServer",
                daemon=True
            )
            self.server_thread.start()
            
            # Start metrics broadcasting
            self.broadcast_thread = threading.Thread(
                target=self._broadcast_loop,
                name="DashboardBroadcast",
                daemon=True
            )
            self.broadcast_thread.start()
            
            logger.info(f"Dashboard server started on port {self.port}")
    
    def stop_dashboard(self) -> None:
        """Gracefully stop dashboard server"""
        with self._lock:
            if not self.status.is_running:
                return
            
            self.status.is_running = False
            self.should_broadcast = False
            
            # Stop SocketIO server
            if self.socketio:
                self.socketio.stop()
            
            # Wait for threads to finish
            if self.broadcast_thread and self.broadcast_thread.is_alive():
                self.broadcast_thread.join(timeout=5)
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5)
            
            logger.info("Dashboard server stopped")
    
    def broadcast_metrics(self, metrics: SystemMetrics) -> None:
        """
        Broadcast metrics to all connected clients
        
        REQUIREMENTS:
        - Must send to all connected WebSocket clients
        - Must handle disconnected clients gracefully
        - Must complete within 100ms
        """
        if not self.socketio or not self.status.is_running:
            return
        
        broadcast_start = time.time()
        
        try:
            # Format metrics for frontend
            metrics_data = self._format_metrics_for_frontend(metrics)
            
            # Broadcast to all connected clients
            self.socketio.emit('metrics_update', {
                'timestamp': metrics.timestamp.isoformat(),
                'system_metrics': metrics_data
            })
            
            # Update broadcast statistics
            self.status.update_broadcast_stats()
            
            broadcast_time = (time.time() - broadcast_start) * 1000  # Convert to ms
            
            if broadcast_time > 100:
                logger.warning(f"Metrics broadcast took {broadcast_time:.1f}ms (>100ms limit)")
                
        except Exception as e:
            logger.error(f"Failed to broadcast metrics: {e}")
    
    def _setup_flask_app(self):
        """Initialize Flask app and SocketIO with routes"""
        self.app = Flask(__name__, 
                        template_folder=str(Path(__file__).parent / 'templates'),
                        static_folder=str(Path(__file__).parent / 'static'))
        self.app.config['SECRET_KEY'] = 'dashboard_secret_key'
        
        # Initialize SocketIO
        self.socketio = SocketIO(
            self.app, 
            cors_allowed_origins="*",
            async_mode='eventlet',
            logger=False,
            engineio_logger=False
        )
=======
    Real-time collection dashboard server with WebSocket updates.
    
    Performance requirements:
    - <2 second dashboard load time
    - <100ms WebSocket update latency
    - Real-time venue progress grid (25x6 venue/year matrix)
    """
    
    def __init__(self, 
                 host: str = '127.0.0.1', 
                 port: int = 5000,
                 debug: bool = False):
        self.host = host
        self.port = port
        self.debug = debug
        
        # Flask app setup
        self.app = Flask(__name__, 
                        template_folder='templates',
                        static_folder='static')
        self.app.config['SECRET_KEY'] = 'collection-dashboard-secret'
        
        # SocketIO setup
        self.socketio = SocketIO(self.app, 
                               cors_allowed_origins="*",
                               async_mode='eventlet')
        
        # Metrics collector
        self.metrics_collector: Optional[MetricsCollector] = None
        self._running = False
        self._broadcast_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
        
        # Setup routes
        self._setup_routes()
        self._setup_socketio_events()
    
<<<<<<< HEAD
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
        
        @self.app.route('/api/health')
        def get_api_health():
            """GET /api/health - API health status"""
            try:
                if not self.metrics_collector:
                    return jsonify({'error': 'Metrics collector not available'}), 503
                
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if not current_metrics:
                    return jsonify({'apis': {}})
                
                # Format API health data
                apis_health = {}
                for api_name, api_data in current_metrics.api_metrics.items():
                    apis_health[api_name] = {
                        'status': api_data.health_status,
                        'success_rate': api_data.success_rate,
                        'avg_response_time': api_data.avg_response_time_ms,
                        'requests_made': api_data.requests_made,
                        'papers_collected': api_data.papers_collected
                    }
                
                return jsonify({'apis': apis_health})
                
            except Exception as e:
                logger.error(f"Error getting API health: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/history')
        def get_collection_history():
            """GET /api/history?hours=N - Historical metrics"""
            try:
                hours = request.args.get('hours', 24, type=int)
                hours = min(hours, 72)  # Limit to 72 hours max
                
                if not self.metrics_collector:
                    return jsonify({'error': 'Metrics collector not available'}), 503
                
                # Get metrics summary for time window
                summary = self.metrics_collector.get_metrics_summary(hours * 60)
                
                # Get recent metrics for trend data
                recent_metrics = self.metrics_collector.metrics_buffer.get_metrics_in_window(hours * 60)
                
                # Format historical data
                history_data = {
                    'summary': {
                        'time_period_hours': hours,
                        'avg_collection_rate': summary.avg_collection_rate,
                        'peak_collection_rate': summary.peak_collection_rate,
                        'total_papers_collected': summary.total_papers_collected,
                        'total_venues_completed': summary.total_venues_completed
                    },
                    'trends': {
                        'collection_rate': [
                            {
                                'timestamp': m.timestamp.isoformat(),
                                'rate': m.collection_progress.papers_per_minute
                            }
                            for m in recent_metrics[-50:]  # Last 50 data points
                        ],
                        'memory_usage': [
                            {
                                'timestamp': m.timestamp.isoformat(),
                                'percentage': m.system_metrics.memory_usage_percentage
                            }
                            for m in recent_metrics[-50:]
                        ]
                    }
                }
                
                return jsonify(history_data)
                
            except Exception as e:
                logger.error(f"Error getting collection history: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/api/status')
        def get_dashboard_status():
            """Get dashboard server status"""
            return jsonify({
                'is_running': self.status.is_running,
                'connected_clients': self.status.connected_clients,
                'uptime_minutes': self.status.get_uptime_minutes(),
                'messages_sent': self.status.messages_sent,
                'last_broadcast': self.status.last_broadcast_time.isoformat() if self.status.last_broadcast_time else None
            })
    
    def _setup_socketio_events(self):
=======
    def set_metrics_collector(self, collector: MetricsCollector) -> None:
        """Set metrics collector reference"""
        with self._lock:
            self.metrics_collector = collector
    
    def start_server(self, use_reloader: bool = False) -> None:
        """Start the dashboard server"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            
            # Start metrics broadcasting
            self._start_metrics_broadcast()
            
            logger.info(f"Starting dashboard server on {self.host}:{self.port}")
            
            # Start Flask-SocketIO server
            self.socketio.run(
                self.app,
                host=self.host,
                port=self.port,
                debug=self.debug,
                use_reloader=use_reloader
            )
    
    def stop_server(self) -> None:
        """Stop the dashboard server"""
        with self._lock:
            self._running = False
            
        if self._broadcast_thread:
            self._broadcast_thread.join(timeout=5.0)
            
        logger.info("Dashboard server stopped")
    
    def broadcast_metrics(self, metrics: SystemMetrics) -> None:
        """
        Broadcast metrics to all connected clients.
        Must complete within 100ms per requirement.
        """
        start_time = time.time()
        
        try:
            # Convert metrics to JSON-serializable format
            metrics_data = metrics.to_dict()
            
            # Broadcast to all connected clients
            self.socketio.emit('metrics_update', metrics_data, broadcast=True)
            
            broadcast_time = (time.time() - start_time) * 1000  # Convert to ms
            if broadcast_time > 100:
                logger.warning(f"Metrics broadcast took {broadcast_time:.1f}ms (requirement: <100ms)")
                
        except Exception as e:
            logger.error(f"Error broadcasting metrics: {e}")
    
    def _setup_routes(self) -> None:
        """Setup Flask HTTP routes"""
        
        @self.app.route('/')
        def dashboard():
            """Main dashboard page"""
            return render_template('dashboard.html')
        
        @self.app.route('/api/metrics/current')
        def get_current_metrics():
            """Get current metrics as JSON"""
            if not self.metrics_collector:
                return jsonify({'error': 'Metrics collector not available'}), 503
            
            metrics = self.metrics_collector.get_latest_metrics()
            if metrics:
                return jsonify(metrics.to_dict())
            else:
                return jsonify({'error': 'No metrics available'}), 404
        
        @self.app.route('/api/metrics/history')
        def get_metrics_history():
            """Get metrics history"""
            if not self.metrics_collector:
                return jsonify({'error': 'Metrics collector not available'}), 503
            
            count = request.args.get('count', 100, type=int)
            history = self.metrics_collector.get_metrics_history(count)
            
            return jsonify([m.to_dict() for m in history])
        
        @self.app.route('/api/venues/progress')
        def get_venue_progress():
            """Get venue progress data"""
            if not self.metrics_collector:
                return jsonify({'error': 'Metrics collector not available'}), 503
            
            metrics = self.metrics_collector.get_latest_metrics()
            if metrics:
                return jsonify(metrics.venue_progress)
            else:
                return jsonify({})
        
        @self.app.route('/api/health')
        def health_check():
            """Health check endpoint"""
            status = {
                'status': 'healthy' if self._running else 'stopped',
                'timestamp': datetime.now().isoformat(),
                'metrics_collector_connected': self.metrics_collector is not None
            }
            
            if self.metrics_collector:
                latest = self.metrics_collector.get_latest_metrics()
                status['last_metrics_time'] = latest.timestamp.isoformat() if latest else None
            
            return jsonify(status)
    
    def _setup_socketio_events(self) -> None:
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
<<<<<<< HEAD
            """Handle client connection"""
            self.status.connected_clients += 1
            logger.info(f"Client connected. Total clients: {self.status.connected_clients}")
            
            # Send initial metrics to new client
            if self.metrics_collector:
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if current_metrics:
                    metrics_data = self._format_metrics_for_frontend(current_metrics)
                    emit('metrics_update', {
                        'timestamp': current_metrics.timestamp.isoformat(),
                        'system_metrics': metrics_data
                    })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection"""
            self.status.connected_clients = max(0, self.status.connected_clients - 1)
            logger.info(f"Client disconnected. Total clients: {self.status.connected_clients}")
        
        @self.socketio.on('request_metrics')
        def handle_metrics_request():
            """Handle explicit metrics request from client"""
            if self.metrics_collector:
                current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                if current_metrics:
                    metrics_data = self._format_metrics_for_frontend(current_metrics)
                    emit('metrics_update', {
                        'timestamp': current_metrics.timestamp.isoformat(),
                        'system_metrics': metrics_data
                    })
    
    def _run_server(self):
        """Run Flask-SocketIO server in separate thread"""
        try:
            # Use eventlet for better WebSocket performance
            eventlet.monkey_patch()
            
            logger.info(f"Starting SocketIO server on port {self.port}")
            self.socketio.run(
                self.app,
                host='0.0.0.0',
                port=self.port,
                debug=False,
                use_reloader=False
            )
        except Exception as e:
            logger.error(f"Dashboard server error: {e}")
            self.status.is_running = False
    
    def _broadcast_loop(self):
        """Metrics broadcasting loop"""
        logger.info(f"Starting metrics broadcast loop with {self.update_interval}s interval")
        
        while self.should_broadcast and self.status.is_running:
            try:
                if self.metrics_collector and self.status.connected_clients > 0:
                    current_metrics = self.metrics_collector.metrics_buffer.get_current_metrics()
                    if current_metrics:
                        self.broadcast_metrics(current_metrics)
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                time.sleep(self.update_interval)
        
        logger.info("Metrics broadcast loop stopped")
    
    def _format_metrics_for_frontend(self, metrics: SystemMetrics) -> Dict[str, Any]:
        """Format metrics data for frontend consumption"""
        return {
            'collection_progress': {
                'session_id': metrics.collection_progress.session_id,
                'total_venues': metrics.collection_progress.total_venues,
                'completed_venues': metrics.collection_progress.completed_venues,
                'papers_collected': metrics.collection_progress.papers_collected,
                'papers_per_minute': round(metrics.collection_progress.papers_per_minute, 2),
                'completion_percentage': round(metrics.collection_progress.completion_percentage, 1),
                'estimated_completion_time': metrics.collection_progress.estimated_completion_time.isoformat() if metrics.collection_progress.estimated_completion_time else None
            },
            'api_health': {
                api_name: {
                    'status': api_data.health_status,
                    'success_rate': round(api_data.success_rate, 3),
                    'avg_response_time': round(api_data.avg_response_time_ms, 1),
                    'papers_collected': api_data.papers_collected
                }
                for api_name, api_data in metrics.api_metrics.items()
            },
            'processing': {
                'venues_normalized': metrics.processing_metrics.venues_normalized,
                'normalization_accuracy': round(metrics.processing_metrics.normalization_accuracy, 3),
                'papers_deduplicated': metrics.processing_metrics.papers_deduplicated,
                'duplicates_removed': metrics.processing_metrics.duplicates_removed,
                'papers_analyzed': metrics.processing_metrics.papers_analyzed,
                'breakthrough_papers_found': metrics.processing_metrics.breakthrough_papers_found
            },
            'system_resources': {
                'memory_usage': round(metrics.system_metrics.memory_usage_percentage, 1),
                'cpu_usage': round(metrics.system_metrics.cpu_usage_percentage, 1),
                'process_memory_mb': round(metrics.system_metrics.process_memory_mb, 1),
                'thread_count': metrics.system_metrics.thread_count,
                'network_connections': metrics.system_metrics.network_connections
            },
            'venue_progress': {
                venue_key: {
                    'venue_name': progress.venue_name,
                    'year': progress.year,
                    'status': progress.status,
                    'papers_collected': progress.papers_collected,
                    'target_papers': progress.target_papers,
                    'completion_percentage': round(progress.completion_percentage, 1)
                }
                for venue_key, progress in metrics.venue_progress.items()
            }
        }
    
    def get_dashboard_status(self) -> DashboardStatus:
        """Get current dashboard status"""
        with self._lock:
            self.status.uptime_seconds = (datetime.now() - self.status.server_start_time).total_seconds()
            return self.status
=======
            logger.info(f"Client connected: {request.sid}")
            
            # Send current metrics immediately on connect
            if self.metrics_collector:
                metrics = self.metrics_collector.get_latest_metrics()
                if metrics:
                    emit('metrics_update', metrics.to_dict())
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            logger.info(f"Client disconnected: {request.sid}")
        
        @self.socketio.on('request_metrics')
        def handle_metrics_request():
            """Handle explicit metrics request"""
            if self.metrics_collector:
                metrics = self.metrics_collector.get_latest_metrics()
                if metrics:
                    emit('metrics_update', metrics.to_dict())
        
        @self.socketio.on('request_history')
        def handle_history_request(data):
            """Handle metrics history request"""
            count = data.get('count', 100) if data else 100
            
            if self.metrics_collector:
                history = self.metrics_collector.get_metrics_history(count)
                emit('metrics_history', [m.to_dict() for m in history])
    
    def _start_metrics_broadcast(self) -> None:
        """Start background metrics broadcasting"""
        if self._broadcast_thread and self._broadcast_thread.is_alive():
            return
        
        self._broadcast_thread = threading.Thread(
            target=self._broadcast_loop,
            daemon=True,
            name="DashboardBroadcast"
        )
        self._broadcast_thread.start()
    
    def _broadcast_loop(self) -> None:
        """Main broadcasting loop"""
        while self._running:
            try:
                if self.metrics_collector:
                    metrics = self.metrics_collector.get_latest_metrics()
                    if metrics:
                        self.broadcast_metrics(metrics)
                
                time.sleep(5)  # Broadcast every 5 seconds
                
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")
                time.sleep(1)  # Short delay on error


# Integration utilities for existing systems
class DashboardIntegrationAdapter:
    """Adapter for integrating dashboard with existing venue engines"""
    
    def __init__(self, dashboard: CollectionDashboard):
        self.dashboard = dashboard
    
    def integrate_with_venue_engine(self, venue_engine) -> None:
        """Integrate dashboard with venue collection engine"""
        if hasattr(self.dashboard, 'metrics_collector') and self.dashboard.metrics_collector:
            self.dashboard.metrics_collector.set_venue_engine(venue_engine)
    
    def integrate_with_state_manager(self, state_manager) -> None:
        """Integrate dashboard with state manager"""
        if hasattr(self.dashboard, 'metrics_collector') and self.dashboard.metrics_collector:
            self.dashboard.metrics_collector.set_state_manager(state_manager)
    
    def integrate_with_processors(self, processors) -> None:
        """Integrate dashboard with data processors"""
        if hasattr(self.dashboard, 'metrics_collector') and self.dashboard.metrics_collector:
            self.dashboard.metrics_collector.set_data_processors(processors)


# Mock components for testing
class MockVenueEngine:
    """Mock venue engine for testing dashboard"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.paper_count = 0
        
    def get_collection_stats(self) -> Dict[str, Any]:
        """Return mock collection statistics"""
        # Simulate growing paper count
        self.paper_count += 1
        
        return {
            'total_papers': self.paper_count,
            'venues_completed': 2,
            'venues_in_progress': 1,
            'venues_remaining': 3,
            'total_venues': 6
        }
    
    def get_venue_progress(self) -> Dict[str, Dict[str, Any]]:
        """Return mock venue progress"""
        venues = {}
        
        # Create sample venue progress
        for i, venue in enumerate(['ICML', 'NeurIPS', 'ICLR', 'AAAI', 'IJCAI', 'UAI']):
            for year in [2020, 2021, 2022, 2023, 2024]:
                key = f"{venue}_{year}"
                
                # Simulate different statuses
                if i < 2:  # First 2 venues completed
                    status = 'completed'
                    papers = 50
                elif i == 2:  # Third venue in progress
                    status = 'in_progress'
                    papers = 25
                else:  # Rest not started
                    status = 'not_started'
                    papers = 0
                
                venues[key] = {
                    'venue_name': venue,
                    'year': year,
                    'status': status,
                    'papers_collected': papers,
                    'target_papers': 50,
                    'start_time': self.start_time if status != 'not_started' else None,
                    'api_source': 'semantic_scholar',
                    'error_count': 0,
                    'last_activity': datetime.now() if status == 'in_progress' else None
                }
        
        return venues


class MockDataProcessors:
    """Mock data processors for testing"""
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Return mock processing statistics"""
        return {
            'papers_processed': 150,
            'papers_filtered': 25,
            'papers_normalized': 150,
            'papers_deduplicated': 5,
            'queue_size': 10,
            'processing_errors': 2
        }


class MockStateManager:
    """Mock state manager for testing"""
    
    def get_state_stats(self) -> Dict[str, Any]:
        """Return mock state statistics"""
        return {
            'total_checkpoints': 15,
            'last_checkpoint_time': datetime.now() - timedelta(minutes=5),
            'checkpoint_size_mb': 2.5,
            'validation_errors': 0,
            'backup_count': 3
        }
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
