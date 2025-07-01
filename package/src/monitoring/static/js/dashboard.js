<<<<<<< HEAD
// Dashboard JavaScript - Real-time monitoring interface

class CollectionDashboard {
    constructor() {
        this.socket = null;
        this.charts = {};
        this.isConnected = false;
        this.lastUpdate = null;
        this.metricsHistory = [];
        this.maxHistoryPoints = 50;
=======
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
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
        
        // Initialize dashboard
        this.initializeSocket();
        this.initializeCharts();
<<<<<<< HEAD
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
=======
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
        this.isConnected = connected;
        const statusElement = document.getElementById('connection-status');
        
        if (connected) {
            statusElement.className = 'badge bg-success';
            statusElement.innerHTML = '<i class="fas fa-wifi me-1"></i>Connected';
        } else {
            statusElement.className = 'badge bg-danger';
            const msg = message || 'Disconnected';
            statusElement.innerHTML = `<i class="fas fa-wifi-slash me-1"></i>${msg}`;
        }
    }
    
    requestMetricsUpdate() {
        if (this.socket && this.isConnected) {
            this.socket.emit('request_metrics');
        }
    }
    
    updateDashboard(metrics) {
        // Update timestamp
        const timestamp = new Date(metrics.timestamp);
        document.getElementById('last-update').textContent = timestamp.toLocaleTimeString();
        
        // Update summary cards
        this.updateSummaryCards(metrics);
        
        // Update venue grid
        this.updateVenueGrid(metrics.venue_progress || {});
        
        // Update API health
        this.updateAPIHealth(metrics.api_metrics || {});
        
        // Update processing metrics
        this.updateProcessingMetrics(metrics.processing_metrics || {});
        
        // Update state metrics
        this.updateStateMetrics(metrics.state_metrics || {});
        
        // Add to history and update charts
        this.addToHistory(metrics);
        this.updateCharts();
    }
    
    updateSummaryCards(metrics) {
        const progress = metrics.collection_progress || {};
        const system = metrics.system_metrics || {};
        
        // Papers collected
        document.getElementById('total-papers').textContent = 
            (progress.total_papers_collected || 0).toLocaleString();
        document.getElementById('papers-per-minute').textContent = 
            (progress.papers_per_minute || 0).toFixed(1);
        
        // Venues completed
        document.getElementById('venues-completed').textContent = 
            progress.venues_completed || 0;
        document.getElementById('venues-progress').textContent = 
            `${progress.venues_completed || 0}/${progress.total_venues || 0}`;
        
        // Session duration
        const duration = progress.session_duration_minutes || 0;
        const hours = Math.floor(duration / 60);
        const minutes = Math.floor(duration % 60);
        document.getElementById('session-duration').textContent = `${hours}h ${minutes}m`;
        
        // ETA
        if (progress.estimated_completion_time) {
            const eta = new Date(progress.estimated_completion_time);
            document.getElementById('estimated-completion').textContent = eta.toLocaleTimeString();
        } else {
            document.getElementById('estimated-completion').textContent = '--';
        }
        
        // Memory and CPU
        document.getElementById('memory-usage').textContent = 
            `${(system.memory_usage_percent || 0).toFixed(1)}%`;
        document.getElementById('cpu-usage').textContent = 
            (system.cpu_usage_percent || 0).toFixed(1);
    }
    
    createVenueGrid() {
        const grid = document.getElementById('venue-grid');
        grid.innerHTML = '';
        
        // Header row
        grid.appendChild(this.createElement('div', 'venue-grid-header', ''));
        this.years.forEach(year => {
            grid.appendChild(this.createElement('div', 'venue-grid-header', year.toString()));
        });
        
        // Venue rows
        this.venues.forEach(venue => {
            // Venue name
            grid.appendChild(this.createElement('div', 'venue-grid-venue-name', venue));
            
            // Year cells
            this.years.forEach(year => {
                const cell = this.createElement('div', 'venue-grid-cell venue-status-not-started', '');
                cell.id = `venue-${venue}-${year}`;
                cell.setAttribute('data-venue', venue);
                cell.setAttribute('data-year', year);
                
                // Add click handler for venue details
                cell.addEventListener('click', () => this.showVenueDetails(venue, year));
                
                grid.appendChild(cell);
            });
        });
    }
    
    updateVenueGrid(venueProgress) {
        this.venues.forEach(venue => {
            this.years.forEach(year => {
                const cellId = `venue-${venue}-${year}`;
                const cell = document.getElementById(cellId);
                const key = `${venue}_${year}`;
                
                if (cell && venueProgress[key]) {
                    const progress = venueProgress[key];
                    const status = progress.status || 'not_started';
                    const papers = progress.papers_collected || 0;
                    const target = progress.target_papers || 50;
                    const percent = progress.progress_percent || 0;
                    
                    // Update cell class
                    cell.className = `venue-grid-cell venue-status-${status}`;
                    
                    // Update cell content
                    cell.innerHTML = `
                        <div class="venue-papers-count">${papers}/${target}</div>
                        <div class="venue-progress-bar">${percent.toFixed(0)}%</div>
                    `;
                    
                    // Add tooltip with details
                    const tooltip = this.createVenueTooltip(progress);
                    cell.setAttribute('title', tooltip);
                    cell.setAttribute('data-bs-toggle', 'tooltip');
                    cell.setAttribute('data-bs-placement', 'top');
                }
            });
        });
        
        // Re-initialize tooltips
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function (tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }
    
    createVenueTooltip(progress) {
        const lines = [
            `Venue: ${progress.venue_name} (${progress.year})`,
            `Status: ${progress.status}`,
            `Papers: ${progress.papers_collected}/${progress.target_papers}`,
            `Progress: ${(progress.progress_percent || 0).toFixed(1)}%`
        ];
        
        if (progress.api_source) {
            lines.push(`API: ${progress.api_source}`);
        }
        
        if (progress.start_time) {
            const start = new Date(progress.start_time);
            lines.push(`Started: ${start.toLocaleTimeString()}`);
        }
        
        if (progress.error_count > 0) {
            lines.push(`Errors: ${progress.error_count}`);
        }
        
        return lines.join('\\n');
    }
    
    updateAPIHealth(apiMetrics) {
        const container = document.getElementById('api-health');
        container.innerHTML = '';
        
        Object.entries(apiMetrics).forEach(([apiName, metrics]) => {
            const card = document.createElement('div');
            card.className = `col-lg-4 col-md-6 mb-3`;
            
            const statusClass = `api-status-${metrics.health_status || 'healthy'}`;
            const statusIcon = this.getStatusIcon(metrics.health_status || 'healthy');
            
            card.innerHTML = `
                <div class="card ${statusClass}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="card-title mb-1">${apiName}</h6>
                                <p class="card-text mb-0">
                                    <small class="text-muted">
                                        ${statusIcon} ${(metrics.health_status || 'healthy').toUpperCase()}
                                    </small>
                                </p>
                            </div>
                            <div class="text-end">
                                <div class="h5 mb-0">${(metrics.success_rate * 100 || 100).toFixed(1)}%</div>
                                <small class="text-muted">Success Rate</small>
                            </div>
                        </div>
                        <div class="row mt-2">
                            <div class="col-6">
                                <small class="text-muted">Response Time</small>
                                <div class="fw-bold">${(metrics.avg_response_time_ms || 0).toFixed(0)}ms</div>
                            </div>
                            <div class="col-6">
                                <small class="text-muted">Requests/min</small>
                                <div class="fw-bold">${(metrics.requests_per_minute || 0).toFixed(1)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            container.appendChild(card);
        });
    }
    
    getStatusIcon(status) {
        const icons = {
            'healthy': '<i class="fas fa-check-circle text-success"></i>',
            'degraded': '<i class="fas fa-exclamation-triangle text-warning"></i>',
            'critical': '<i class="fas fa-exclamation-circle text-danger"></i>',
            'offline': '<i class="fas fa-times-circle text-danger"></i>'
        };
        return icons[status] || icons['healthy'];
    }
    
    updateProcessingMetrics(processing) {
        document.getElementById('papers-processed').textContent = 
            (processing.papers_processed || 0).toLocaleString();
        document.getElementById('papers-filtered').textContent = 
            (processing.papers_filtered || 0).toLocaleString();
        document.getElementById('papers-deduplicated').textContent = 
            (processing.papers_deduplicated || 0).toLocaleString();
        document.getElementById('processing-queue').textContent = 
            (processing.processing_queue_size || 0).toLocaleString();
    }
    
    updateStateMetrics(state) {
        document.getElementById('total-checkpoints').textContent = 
            (state.total_checkpoints || 0).toLocaleString();
        document.getElementById('checkpoint-size').textContent = 
            `${(state.checkpoint_size_mb || 0).toFixed(1)} MB`;
        
        if (state.last_checkpoint_time) {
            const lastCheckpoint = new Date(state.last_checkpoint_time);
            document.getElementById('last-checkpoint').textContent = lastCheckpoint.toLocaleTimeString();
        }
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
    }
    
    initializeCharts() {
        // Collection Rate Chart
        const collectionCtx = document.getElementById('collection-rate-chart').getContext('2d');
<<<<<<< HEAD
        this.charts.collectionRate = new Chart(collectionCtx, {
=======
        this.collectionRateChart = new Chart(collectionCtx, {
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
            type: 'line',
            data: {
                labels: [],
                datasets: [{
<<<<<<< HEAD
                    label: 'Papers/Minute',
                    data: [],
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
=======
                    label: 'Papers/min',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.1
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
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
<<<<<<< HEAD
                },
                plugins: {
                    legend: {
                        display: false
                    }
=======
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
                }
            }
        });
        
        // System Resources Chart
        const systemCtx = document.getElementById('system-resources-chart').getContext('2d');
<<<<<<< HEAD
        this.charts.systemResources = new Chart(systemCtx, {
=======
        this.systemResourcesChart = new Chart(systemCtx, {
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Memory %',
                        data: [],
<<<<<<< HEAD
                        borderColor: '#28a745',
                        backgroundColor: 'rgba(40, 167, 69, 0.1)',
                        borderWidth: 2,
                        fill: false
=======
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        tension: 0.1
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
                    },
                    {
                        label: 'CPU %',
                        data: [],
<<<<<<< HEAD
                        borderColor: '#17a2b8',
                        backgroundColor: 'rgba(23, 162, 184, 0.1)',
                        borderWidth: 2,
                        fill: false
=======
                        borderColor: 'rgb(54, 162, 235)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        tension: 0.1
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
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
    
<<<<<<< HEAD
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
=======
    addToHistory(metrics) {
        this.metricsHistory.push(metrics);
        
        // Keep only recent history
        if (this.metricsHistory.length > this.maxHistorySize) {
            this.metricsHistory = this.metricsHistory.slice(-this.maxHistorySize);
        }
    }
    
    updateCharts() {
        if (this.metricsHistory.length === 0) return;
        
        // Prepare data for charts
        const labels = this.metricsHistory.map(m => {
            const time = new Date(m.timestamp);
            return time.toLocaleTimeString();
        });
        
        const collectionRates = this.metricsHistory.map(m => 
            m.collection_progress?.papers_per_minute || 0
        );
        
        const memoryUsage = this.metricsHistory.map(m => 
            m.system_metrics?.memory_usage_percent || 0
        );
        
        const cpuUsage = this.metricsHistory.map(m => 
            m.system_metrics?.cpu_usage_percent || 0
        );
        
        // Update collection rate chart
        this.collectionRateChart.data.labels = labels;
        this.collectionRateChart.data.datasets[0].data = collectionRates;
        this.collectionRateChart.update('none');
        
        // Update system resources chart
        this.systemResourcesChart.data.labels = labels;
        this.systemResourcesChart.data.datasets[0].data = memoryUsage;
        this.systemResourcesChart.data.datasets[1].data = cpuUsage;
        this.systemResourcesChart.update('none');
    }
    
    showVenueDetails(venue, year) {
        // Show modal or alert with venue details
        console.log(`Showing details for ${venue} ${year}`);
        // TODO: Implement venue details modal
    }
    
    showAlert(alert) {
        const container = document.getElementById('alerts-container');
        
        const alertElement = document.createElement('div');
        alertElement.className = `alert alert-${this.getAlertClass(alert.severity)} alert-dismissible fade show`;
        alertElement.innerHTML = `
            <strong>${alert.rule_name}:</strong> ${alert.message}
            <small class="d-block mt-1 text-muted">
                ${new Date(alert.timestamp).toLocaleString()}
            </small>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        container.appendChild(alertElement);
        
        // Auto-remove alert after 10 seconds
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
        setTimeout(() => {
            if (alertElement.parentNode) {
                alertElement.remove();
            }
        }, 10000);
    }
    
<<<<<<< HEAD
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
=======
    getAlertClass(severity) {
        const classes = {
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
            'info': 'info',
            'warning': 'warning',
            'error': 'danger',
            'critical': 'danger'
        };
<<<<<<< HEAD
        return mapping[severity] || 'info';
=======
        return classes[severity] || 'info';
    }
    
    createElement(tag, className, textContent) {
        const element = document.createElement(tag);
        if (className) element.className = className;
        if (textContent) element.textContent = textContent;
        return element;
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
    }
}

// Initialize dashboard when page loads
<<<<<<< HEAD
document.addEventListener('DOMContentLoaded', () => {
=======
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Collection Dashboard...');
>>>>>>> c6f915c (Implement Real-Time Collection Dashboard (Issue #8) - Missing Files Added)
    window.dashboard = new CollectionDashboard();
});