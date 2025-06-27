// Dashboard JavaScript - Real-time monitoring interface

class CollectionDashboard {
    constructor() {
        this.socket = null;
        this.charts = {};
        this.isConnected = false;
        this.lastUpdate = null;
        this.metricsHistory = [];
        this.maxHistoryPoints = 50;
        
        // Initialize dashboard
        this.initializeSocket();
        this.initializeCharts();
        this.setupEventHandlers();
        
        console.log('Collection Dashboard initialized');
    }
    
    initializeSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            this.isConnected = true;
            this.updateConnectionStatus(true);
            console.log('Connected to dashboard server');
            
            // Request initial metrics
            this.socket.emit('request_metrics');
        });
        
        this.socket.on('disconnect', () => {
            this.isConnected = false;
            this.updateConnectionStatus(false);
            console.log('Disconnected from dashboard server');
        });
        
        this.socket.on('metrics_update', (data) => {
            this.handleMetricsUpdate(data);
        });
        
        this.socket.on('venue_completed', (data) => {
            this.handleVenueCompleted(data);
        });
        
        this.socket.on('alert_triggered', (data) => {
            this.showAlert(data.alert);
        });
    }
    
    initializeCharts() {
        // Collection Rate Chart
        const collectionCtx = document.getElementById('collection-rate-chart').getContext('2d');
        this.charts.collectionRate = new Chart(collectionCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Papers/Minute',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Papers per Minute'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
        
        // System Resources Chart
        const systemCtx = document.getElementById('system-resources-chart').getContext('2d');
        this.charts.systemResources = new Chart(systemCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Memory %',
                        data: [],
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: false
                    },
                    {
                        label: 'CPU %',
                        data: [],
                        borderColor: '#17a2b8',
                        backgroundColor: 'rgba(23, 162, 184, 0.1)',
                        borderWidth: 2,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Percentage'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    }
                }
            }
        });
    }
    
    setupEventHandlers() {
        // Auto-refresh every 30 seconds as fallback
        setInterval(() => {
            if (this.isConnected) {
                this.socket.emit('request_metrics');
            }
        }, 30000);
        
        // Venue item click handlers
        document.addEventListener('click', (e) => {
            if (e.target.closest('.venue-item')) {
                const venueItem = e.target.closest('.venue-item');
                this.showVenueDetails(venueItem);
            }
        });
    }
    
    handleMetricsUpdate(data) {
        this.lastUpdate = new Date();
        this.updateLastUpdateTime();
        
        const metrics = data.system_metrics;
        
        // Update collection progress
        this.updateCollectionProgress(metrics.collection_progress);
        
        // Update API health
        this.updateAPIHealth(metrics.api_health);
        
        // Update system resources
        this.updateSystemResources(metrics.system_resources);
        
        // Update processing metrics
        this.updateProcessingMetrics(metrics.processing);
        
        // Update venue progress grid
        this.updateVenueGrid(metrics.venue_progress);
        
        // Update charts
        this.updateCharts(metrics);
        
        // Store metrics for history
        this.storeMetricsHistory(metrics);
    }
    
    updateCollectionProgress(progress) {
        document.getElementById('session-id').textContent = progress.session_id || '--';
        document.getElementById('papers-collected').textContent = progress.papers_collected.toLocaleString();
        document.getElementById('collection-rate').textContent = progress.papers_per_minute.toFixed(1);
        document.getElementById('completed-venues').textContent = progress.completed_venues;
        document.getElementById('total-venues').textContent = progress.total_venues;
        
        // Update progress bar
        const progressBar = document.getElementById('overall-progress');
        const progressText = document.getElementById('progress-text');
        const percentage = Math.min(progress.completion_percentage, 100);
        
        progressBar.style.width = percentage + '%';
        progressText.textContent = percentage.toFixed(1) + '%';
        
        // Update progress bar color based on completion
        progressBar.className = 'progress-bar';
        if (percentage < 25) {
            progressBar.classList.add('bg-danger');
        } else if (percentage < 75) {
            progressBar.classList.add('bg-warning');
        } else {
            progressBar.classList.add('bg-success');
        }
        
        // Update estimated completion time
        if (progress.estimated_completion_time) {
            const eta = new Date(progress.estimated_completion_time);
            document.getElementById('estimated-completion').textContent = eta.toLocaleTimeString();
        }
    }
    
    updateAPIHealth(apiHealth) {
        const container = document.getElementById('api-health-container');
        container.innerHTML = '';
        
        for (const [apiName, health] of Object.entries(apiHealth)) {
            const apiItem = document.createElement('div');
            apiItem.className = `api-item ${health.status}`;
            
            apiItem.innerHTML = `
                <div class="api-name">${apiName}</div>
                <div class="api-metrics">
                    <span class="api-status ${health.status}">${health.status}</span>
                    <span>Success: ${(health.success_rate * 100).toFixed(1)}%</span>
                    <span>Response: ${health.avg_response_time.toFixed(0)}ms</span>
                    <span>Papers: ${health.papers_collected}</span>
                </div>
            `;
            
            container.appendChild(apiItem);
        }
    }
    
    updateSystemResources(resources) {
        // Update memory usage
        const memoryProgress = document.getElementById('memory-progress');
        const memoryText = document.getElementById('memory-text');
        memoryProgress.style.width = resources.memory_usage + '%';
        memoryText.textContent = resources.memory_usage.toFixed(1) + '%';
        
        // Color code memory usage
        memoryProgress.className = 'progress-bar';
        if (resources.memory_usage > 80) {
            memoryProgress.classList.add('bg-danger');
        } else if (resources.memory_usage > 60) {
            memoryProgress.classList.add('bg-warning');
        } else {
            memoryProgress.classList.add('bg-success');
        }
        
        // Update CPU usage
        const cpuProgress = document.getElementById('cpu-progress');
        const cpuText = document.getElementById('cpu-text');
        cpuProgress.style.width = resources.cpu_usage + '%';
        cpuText.textContent = resources.cpu_usage.toFixed(1) + '%';
        
        // Update system details
        document.getElementById('process-memory').textContent = resources.process_memory_mb.toFixed(1);
        document.getElementById('thread-count').textContent = resources.thread_count;
        document.getElementById('network-connections').textContent = resources.network_connections;
    }
    
    updateProcessingMetrics(processing) {
        document.getElementById('venues-normalized').textContent = processing.venues_normalized;
        document.getElementById('normalization-accuracy').textContent = (processing.normalization_accuracy * 100).toFixed(1) + '%';
        document.getElementById('papers-deduplicated').textContent = processing.papers_deduplicated;
        document.getElementById('duplicates-removed').textContent = processing.duplicates_removed;
        document.getElementById('papers-analyzed').textContent = processing.papers_analyzed;
        document.getElementById('breakthrough-papers').textContent = processing.breakthrough_papers_found;
    }
    
    updateVenueGrid(venueProgress) {
        const grid = document.getElementById('venue-grid');
        
        // Group venues by name and year
        const venuesByName = {};
        for (const [venueKey, progress] of Object.entries(venueProgress)) {
            const venueName = progress.venue_name;
            if (!venuesByName[venueName]) {
                venuesByName[venueName] = {};
            }
            venuesByName[venueName][progress.year] = progress;
        }
        
        // Clear existing grid
        grid.innerHTML = '';
        
        // Create venue items
        for (const [venueName, years] of Object.entries(venuesByName)) {
            for (const [year, progress] of Object.entries(years)) {
                const venueItem = document.createElement('div');
                venueItem.className = `venue-item ${progress.status}`;
                venueItem.dataset.venue = venueName;
                venueItem.dataset.year = year;
                
                venueItem.innerHTML = `
                    <div class="venue-name">${venueName}</div>
                    <div class="venue-year">${year}</div>
                    <div class="venue-progress">${progress.papers_collected}/${progress.target_papers}</div>
                `;
                
                grid.appendChild(venueItem);
            }
        }
    }
    
    updateCharts(metrics) {
        const timestamp = new Date().toLocaleTimeString();
        
        // Update collection rate chart
        const collectionChart = this.charts.collectionRate;
        collectionChart.data.labels.push(timestamp);
        collectionChart.data.datasets[0].data.push(metrics.collection_progress.papers_per_minute);
        
        // Keep only last 20 points
        if (collectionChart.data.labels.length > 20) {
            collectionChart.data.labels.shift();
            collectionChart.data.datasets[0].data.shift();
        }
        
        collectionChart.update('none');
        
        // Update system resources chart
        const systemChart = this.charts.systemResources;
        systemChart.data.labels.push(timestamp);
        systemChart.data.datasets[0].data.push(metrics.system_resources.memory_usage);
        systemChart.data.datasets[1].data.push(metrics.system_resources.cpu_usage);
        
        // Keep only last 20 points
        if (systemChart.data.labels.length > 20) {
            systemChart.data.labels.shift();
            systemChart.data.datasets[0].data.shift();
            systemChart.data.datasets[1].data.shift();
        }
        
        systemChart.update('none');
    }
    
    storeMetricsHistory(metrics) {
        this.metricsHistory.push({
            timestamp: new Date(),
            ...metrics
        });
        
        // Keep only recent history
        if (this.metricsHistory.length > this.maxHistoryPoints) {
            this.metricsHistory.shift();
        }
    }
    
    updateConnectionStatus(connected) {
        const indicator = document.getElementById('connection-indicator');
        const text = document.getElementById('connection-text');
        
        if (connected) {
            indicator.className = 'status-indicator connected';
            text.textContent = 'Connected';
        } else {
            indicator.className = 'status-indicator disconnected';
            text.textContent = 'Disconnected';
        }
    }
    
    updateLastUpdateTime() {
        const element = document.getElementById('last-update');
        if (this.lastUpdate) {
            element.textContent = this.lastUpdate.toLocaleTimeString();
        }
    }
    
    handleVenueCompleted(data) {
        // Show completion notification
        this.showNotification(`Venue ${data.venue} (${data.year}) completed with ${data.papers_collected} papers`, 'success');
        
        // Update the venue item in grid
        const venueItems = document.querySelectorAll(`.venue-item[data-venue="${data.venue}"][data-year="${data.year}"]`);
        venueItems.forEach(item => {
            item.className = 'venue-item completed';
            item.querySelector('.venue-progress').textContent = `${data.papers_collected}/${data.papers_collected}`;
        });
    }
    
    showVenueDetails(venueItem) {
        const venue = venueItem.dataset.venue;
        const year = venueItem.dataset.year;
        const status = venueItem.classList.contains('completed') ? 'Completed' :
                      venueItem.classList.contains('in-progress') ? 'In Progress' :
                      venueItem.classList.contains('failed') ? 'Failed' : 'Not Started';
        
        const progress = venueItem.querySelector('.venue-progress').textContent;
        
        alert(`Venue: ${venue}\nYear: ${year}\nStatus: ${status}\nProgress: ${progress}`);
    }
    
    showAlert(alert) {
        const alertContainer = this.getOrCreateAlertContainer();
        
        const alertElement = document.createElement('div');
        alertElement.className = `alert alert-${this.getBootstrapAlertClass(alert.severity)} alert-dismissible fade show`;
        alertElement.innerHTML = `
            <strong>${alert.title}</strong><br>
            ${alert.message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(alertElement);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.remove();
            }
        }, 10000);
    }
    
    showNotification(message, type = 'info') {
        const alertContainer = this.getOrCreateAlertContainer();
        
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        alertContainer.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }
    
    getOrCreateAlertContainer() {
        let container = document.querySelector('.alert-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'alert-container';
            document.body.appendChild(container);
        }
        return container;
    }
    
    getBootstrapAlertClass(severity) {
        const mapping = {
            'info': 'info',
            'warning': 'warning',
            'error': 'danger',
            'critical': 'danger'
        };
        return mapping[severity] || 'info';
    }
}

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CollectionDashboard();
});