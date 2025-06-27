/**
 * Dashboard JavaScript - Real-time collection monitoring client
 * Handles WebSocket connections, chart updates, and venue grid management
 */

class CollectionDashboard {
    constructor() {
        // Socket.IO connection
        this.socket = null;
        this.isConnected = false;
        
        // Charts
        this.collectionRateChart = null;
        this.systemResourcesChart = null;
        
        // Data storage
        this.metricsHistory = [];
        this.maxHistorySize = 100;
        
        // Venues configuration
        this.venues = [
            'ICML', 'NeurIPS', 'ICLR', 'AAAI', 'IJCAI', 'UAI', 'AISTATS', 
            'COLT', 'ALT', 'ACML', 'ECML', 'PKDD', 'KDD', 'WSDM', 'WWW',
            'SIGIR', 'CIKM', 'ICDM', 'SDM', 'PAKDD', 'VLDB', 'ICDE', 
            'EDBT', 'PODS', 'SIGMOD'
        ];
        this.years = [2019, 2020, 2021, 2022, 2023, 2024];
        
        // Initialize dashboard
        this.initializeSocket();
        this.initializeCharts();
        this.createVenueGrid();
        
        // Set up periodic updates
        setInterval(() => this.requestMetricsUpdate(), 30000); // Every 30 seconds
    }
    
    initializeSocket() {
        console.log('Initializing Socket.IO connection...');
        
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to dashboard server');
            this.updateConnectionStatus(true);
            this.requestMetricsUpdate();
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from dashboard server');
            this.updateConnectionStatus(false);
        });
        
        this.socket.on('metrics_update', (data) => {
            console.log('Received metrics update');
            this.updateDashboard(data);
        });
        
        this.socket.on('metrics_history', (data) => {
            console.log('Received metrics history');
            this.metricsHistory = data;
            this.updateCharts();
        });
        
        this.socket.on('alert_notification', (alert) => {
            console.log('Received alert notification', alert);
            this.showAlert(alert);
        });
        
        // Handle connection errors
        this.socket.on('connect_error', (error) => {
            console.error('Socket connection error:', error);
            this.updateConnectionStatus(false, 'Connection Error');
        });
    }
    
    updateConnectionStatus(connected, message = null) {
        const statusBadge = document.getElementById('connection-status');
        if (statusBadge) {
            if (connected) {
                statusBadge.className = 'badge bg-success';
                statusBadge.textContent = 'Connected';
            } else {
                statusBadge.className = 'badge bg-danger';
                statusBadge.textContent = message || 'Disconnected';
            }
        }
        this.isConnected = connected;
    }
    
    initializeCharts() {
        // Collection rate chart
        const collectionCtx = document.getElementById('collectionRateChart');
        if (collectionCtx) {
            this.collectionRateChart = new Chart(collectionCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Papers/minute',
                        data: [],
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        }
                    }
                }
            });
        }
        
        // System resources chart
        const resourcesCtx = document.getElementById('systemResourcesChart');
        if (resourcesCtx) {
            this.systemResourcesChart = new Chart(resourcesCtx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: [],
                    datasets: [{
                        label: 'Memory %',
                        data: [],
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    }, {
                        label: 'CPU %',
                        data: [],
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        tension: 0.1,
                        yAxisID: 'y'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            max: 100
                        }
                    }
                }
            });
        }
    }
    
    createVenueGrid() {
        const venueGrid = document.getElementById('venue-grid');
        if (!venueGrid) return;
        
        venueGrid.innerHTML = '';
        
        this.venues.forEach(venue => {
            const venueRow = document.createElement('div');
            venueRow.className = 'venue-row mb-2';
            
            const venueHeader = document.createElement('div');
            venueHeader.className = 'd-flex align-items-center mb-1';
            venueHeader.innerHTML = `<strong>${venue}</strong>`;
            venueRow.appendChild(venueHeader);
            
            const yearGrid = document.createElement('div');
            yearGrid.className = 'd-flex flex-wrap gap-1';
            
            this.years.forEach(year => {
                const yearBadge = document.createElement('span');
                yearBadge.id = `venue-${venue}-${year}`;
                yearBadge.className = 'badge bg-secondary';
                yearBadge.textContent = year;
                yearBadge.style.cursor = 'pointer';
                yearBadge.onclick = () => this.showVenueDetails(venue, year);
                yearGrid.appendChild(yearBadge);
            });
            
            venueRow.appendChild(yearGrid);
            venueGrid.appendChild(venueRow);
        });
    }
    
    updateDashboard(metrics) {
        if (!metrics) return;
        
        // Update timestamp
        const lastUpdate = document.getElementById('last-update');
        if (lastUpdate) {
            lastUpdate.textContent = new Date(metrics.timestamp).toLocaleString();
        }
        
        // Add to history
        this.addToHistory(metrics);
        
        // Update each section
        this.updateSummaryCards(metrics.collection_progress);
        this.updateVenueGrid(metrics.venue_progress);
        this.updateAPIHealth(metrics.api_metrics);
        this.updateProcessingMetrics(metrics.processing_metrics);
        this.updateStateMetrics(metrics.state_metrics);
        
        // Update charts
        this.updateCharts();
    }
    
    updateSummaryCards(progress) {
        if (!progress) return;
        
        // Update total papers
        const totalPapers = document.getElementById('total-papers');
        if (totalPapers) {
            totalPapers.textContent = progress.total_papers_collected.toLocaleString();
        }
        
        // Update collection rate
        const collectionRate = document.getElementById('collection-rate');
        if (collectionRate) {
            collectionRate.textContent = `${progress.papers_per_minute.toFixed(1)}/min`;
        }
        
        // Update overall progress
        const overallProgress = document.getElementById('overall-progress');
        const overallProgressBar = document.getElementById('overall-progress-bar');
        if (overallProgress && overallProgressBar) {
            const percentage = progress.overall_completion_percent;
            overallProgress.textContent = `${percentage.toFixed(1)}%`;
            overallProgressBar.style.width = `${percentage}%`;
            overallProgressBar.className = `progress-bar ${percentage >= 75 ? 'bg-success' : percentage >= 50 ? 'bg-info' : 'bg-warning'}`;
        }
        
        // Update active alerts
        const activeAlerts = document.getElementById('active-alerts');
        if (activeAlerts && progress.active_alerts !== undefined) {
            activeAlerts.textContent = progress.active_alerts;
        }
    }
    
    updateVenueGrid(venueProgress) {
        if (!venueProgress) return;
        
        Object.entries(venueProgress).forEach(([key, progress]) => {
            const badge = document.getElementById(`venue-${progress.venue_name}-${progress.year}`);
            if (badge) {
                // Update status color
                let colorClass = 'bg-secondary';
                if (progress.status === 'completed') {
                    colorClass = 'bg-success';
                } else if (progress.status === 'in_progress') {
                    colorClass = 'bg-warning';
                } else if (progress.status === 'failed') {
                    colorClass = 'bg-danger';
                }
                
                badge.className = `badge ${colorClass}`;
                
                // Add progress indicator if in progress
                if (progress.status === 'in_progress' && progress.completion_percent > 0) {
                    badge.innerHTML = `${progress.year} <small>(${progress.completion_percent.toFixed(0)}%)</small>`;
                }
                
                // Add tooltip
                badge.title = this.createVenueTooltip(progress);
            }
        });
    }
    
    updateAPIHealth(apiMetrics) {
        if (!apiMetrics) return;
        
        const apiHealthDiv = document.getElementById('api-health');
        if (!apiHealthDiv) return;
        
        apiHealthDiv.innerHTML = '';
        
        Object.entries(apiMetrics).forEach(([apiName, metrics]) => {
            const apiCard = document.createElement('div');
            apiCard.className = 'api-health-item d-flex justify-content-between align-items-center mb-2';
            
            const statusClass = metrics.health_status === 'healthy' ? 'text-success' : 
                               metrics.health_status === 'degraded' ? 'text-warning' : 'text-danger';
            
            apiCard.innerHTML = `
                <div>
                    <span class="api-status-badge ${metrics.health_status}"></span>
                    <strong>${apiName}</strong>
                </div>
                <div class="text-end">
                    <small class="${statusClass}">${metrics.health_status}</small>
                    <br>
                    <small class="text-muted">${metrics.success_rate.toFixed(1)}% success</small>
                </div>
            `;
            
            apiHealthDiv.appendChild(apiCard);
        });
    }
    
    updateProcessingMetrics(processing) {
        if (!processing) return;
        
        // Update processing errors
        const processingErrors = document.getElementById('processing-errors');
        if (processingErrors) {
            processingErrors.textContent = processing.processing_errors;
            if (processing.processing_errors > 0) {
                processingErrors.classList.add('text-danger');
            } else {
                processingErrors.classList.remove('text-danger');
            }
        }
        
        // Update data quality score
        const qualityScore = document.getElementById('quality-score');
        if (qualityScore) {
            const score = processing.data_quality_score * 100;
            qualityScore.textContent = `${score.toFixed(1)}%`;
            
            // Color based on score
            if (score >= 90) {
                qualityScore.className = 'metric-value text-success';
            } else if (score >= 70) {
                qualityScore.className = 'metric-value text-warning';
            } else {
                qualityScore.className = 'metric-value text-danger';
            }
        }
    }
    
    updateStateMetrics(state) {
        if (!state) return;
        
        // Update checkpoint count
        const checkpointCount = document.getElementById('checkpoint-count');
        if (checkpointCount) {
            checkpointCount.textContent = state.total_checkpoints;
        }
        
        // Update last checkpoint time
        const lastCheckpoint = document.getElementById('last-checkpoint');
        if (lastCheckpoint && state.last_checkpoint_time) {
            const timeSince = this.getTimeSince(new Date(state.last_checkpoint_time));
            lastCheckpoint.textContent = timeSince;
        }
    }
    
    addToHistory(metrics) {
        this.metricsHistory.push({
            timestamp: metrics.timestamp,
            papers_per_minute: metrics.collection_progress.papers_per_minute,
            memory_percent: metrics.system_metrics.memory_usage_percent,
            cpu_percent: metrics.system_metrics.cpu_usage_percent
        });
        
        // Keep only last N entries
        if (this.metricsHistory.length > this.maxHistorySize) {
            this.metricsHistory = this.metricsHistory.slice(-this.maxHistorySize);
        }
    }
    
    updateCharts() {
        if (!this.metricsHistory.length) return;
        
        const labels = this.metricsHistory.map(m => 
            new Date(m.timestamp).toLocaleTimeString()
        );
        
        // Update collection rate chart
        if (this.collectionRateChart) {
            this.collectionRateChart.data.labels = labels;
            this.collectionRateChart.data.datasets[0].data = 
                this.metricsHistory.map(m => m.papers_per_minute);
            this.collectionRateChart.update('none');
        }
        
        // Update system resources chart
        if (this.systemResourcesChart) {
            this.systemResourcesChart.data.labels = labels;
            this.systemResourcesChart.data.datasets[0].data = 
                this.metricsHistory.map(m => m.memory_percent);
            this.systemResourcesChart.data.datasets[1].data = 
                this.metricsHistory.map(m => m.cpu_percent);
            this.systemResourcesChart.update('none');
        }
    }
    
    requestMetricsUpdate() {
        if (this.socket && this.isConnected) {
            this.socket.emit('request_metrics');
        }
    }
    
    showVenueDetails(venue, year) {
        // Create modal content
        const modalContent = `
            <div class="modal fade" id="venueDetailsModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${venue} ${year} Collection Details</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>Loading details...</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal if any
        const existingModal = document.getElementById('venueDetailsModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalContent);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('venueDetailsModal'));
        modal.show();
        
        // Request details from server
        if (this.socket && this.isConnected) {
            this.socket.emit('get_venue_details', { venue, year }, (details) => {
                const modalBody = document.querySelector('#venueDetailsModal .modal-body');
                if (modalBody && details) {
                    modalBody.innerHTML = `
                        <table class="table table-sm">
                            <tr><td>Status:</td><td><span class="badge bg-${this.getStatusColor(details.status)}">${details.status}</span></td></tr>
                            <tr><td>Papers Collected:</td><td>${details.papers_collected || 0}</td></tr>
                            <tr><td>Progress:</td><td>${(details.completion_percent || 0).toFixed(1)}%</td></tr>
                            <tr><td>Started:</td><td>${details.start_time ? new Date(details.start_time).toLocaleString() : 'Not started'}</td></tr>
                            <tr><td>Last Activity:</td><td>${details.last_activity ? new Date(details.last_activity).toLocaleString() : 'N/A'}</td></tr>
                            ${details.error_message ? `<tr><td>Error:</td><td class="text-danger">${details.error_message}</td></tr>` : ''}
                        </table>
                    `;
                } else {
                    modalBody.innerHTML = '<p class="text-muted">No details available</p>';
                }
            });
        }
    }
    
    showAlert(alert) {
        const alertsContainer = document.getElementById('alerts-container');
        if (!alertsContainer) return;
        
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${this.getAlertClass(alert.severity)} alert-dismissible fade show`;
        alertDiv.innerHTML = `
            <strong>${alert.rule_name}:</strong> ${alert.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertsContainer.insertBefore(alertDiv, alertsContainer.firstChild);
        
        // Auto-dismiss after 30 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 30000);
        
        // Update alerts list
        this.updateAlertsList(alert);
    }
    
    updateAlertsList(alert) {
        const alertsList = document.getElementById('recent-alerts');
        if (!alertsList) return;
        
        const alertItem = document.createElement('div');
        alertItem.className = 'alert-item';
        alertItem.innerHTML = `
            <div class="d-flex justify-content-between">
                <div>
                    <span class="alert-badge ${alert.severity}">${alert.severity}</span>
                    <strong>${alert.rule_name}</strong>
                </div>
                <small class="alert-time">${new Date(alert.timestamp).toLocaleTimeString()}</small>
            </div>
            <div class="text-muted small mt-1">${alert.message}</div>
        `;
        
        alertsList.insertBefore(alertItem, alertsList.firstChild);
        
        // Keep only last 10 alerts
        while (alertsList.children.length > 10) {
            alertsList.removeChild(alertsList.lastChild);
        }
    }
    
    createVenueTooltip(progress) {
        let tooltip = `Status: ${progress.status}\n`;
        tooltip += `Papers: ${progress.papers_collected}\n`;
        tooltip += `Progress: ${progress.completion_percent.toFixed(1)}%`;
        
        if (progress.last_activity) {
            tooltip += `\nLast activity: ${this.getTimeSince(new Date(progress.last_activity))} ago`;
        }
        
        return tooltip;
    }
    
    getTimeSince(date) {
        const seconds = Math.floor((new Date() - date) / 1000);
        
        if (seconds < 60) return `${seconds}s`;
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) return `${minutes}m`;
        const hours = Math.floor(minutes / 60);
        if (hours < 24) return `${hours}h`;
        const days = Math.floor(hours / 24);
        return `${days}d`;
    }
    
    getStatusColor(status) {
        switch(status) {
            case 'completed': return 'success';
            case 'in_progress': return 'warning';
            case 'failed': return 'danger';
            default: return 'secondary';
        }
    }
    
    getAlertClass(severity) {
        switch(severity) {
            case 'critical': return 'danger';
            case 'error': return 'danger';
            case 'warning': return 'warning';
            case 'info': return 'info';
            default: return 'secondary';
        }
    }
}

// Initialize dashboard when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CollectionDashboard();
    console.log('Dashboard initialized');
});