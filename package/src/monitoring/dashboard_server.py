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

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO, emit

from .dashboard_metrics import SystemMetrics, MetricsBuffer
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
        
        # Setup routes
        self._setup_routes()
        self._setup_socketio_events()
    
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
        """Setup SocketIO event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
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