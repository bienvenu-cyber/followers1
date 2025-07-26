// API base URL
const API_BASE_URL = 'http://localhost:8000/api';

// Charts
let successRateChart = null;
let creationTimeChart = null;
let accountsPerHourChart = null;

// Auto-refresh interval (in milliseconds)
const REFRESH_INTERVAL = 5000;
let refreshInterval;

// Initialize the dashboard
document.addEventListener('DOMContentLoaded', function() {
    initCharts();
    fetchAllData();
    
    // Set up auto-refresh
    refreshInterval = setInterval(fetchAllData, REFRESH_INTERVAL);
    
    // Manual refresh button
    document.getElementById('refreshBtn').addEventListener('click', fetchAllData);
});

// Initialize charts
function initCharts() {
    // Success Rate Chart
    const successRateCtx = document.getElementById('successRateChart').getContext('2d');
    successRateChart = new Chart(successRateCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Success Rate (%)',
                data: [],
                borderColor: '#28a745',
                backgroundColor: 'rgba(40, 167, 69, 0.1)',
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
                    max: 100,
                    title: {
                        display: true,
                        text: 'Success Rate (%)'
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
    
    // Creation Time Chart
    const creationTimeCtx = document.getElementById('creationTimeChart').getContext('2d');
    creationTimeChart = new Chart(creationTimeCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Average Creation Time (seconds)',
                data: [],
                borderColor: '#17a2b8',
                backgroundColor: 'rgba(23, 162, 184, 0.1)',
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
                        text: 'Time (seconds)'
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
    
    // Accounts Per Hour Chart
    const accountsPerHourCtx = document.getElementById('accountsPerHourChart').getContext('2d');
    accountsPerHourChart = new Chart(accountsPerHourCtx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Accounts Per Hour',
                data: [],
                borderColor: '#6f42c1',
                backgroundColor: 'rgba(111, 66, 193, 0.1)',
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
                        text: 'Accounts/Hour'
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

// Fetch all data
function fetchAllData() {
    fetchGlobalStats();
    fetchCurrentCycle();
    fetchPerformanceHistory();
    fetchServicePerformance();
}

// Fetch global statistics
function fetchGlobalStats() {
    fetch(`${API_BASE_URL}/statistics/global`)
        .then(response => response.json())
        .then(data => {
            updateGlobalStats(data);
            updateErrorsList(data.error_counts);
            updateUptime(data.uptime);
        })
        .catch(error => console.error('Error fetching global stats:', error));
}

// Fetch current cycle
function fetchCurrentCycle() {
    fetch(`${API_BASE_URL}/statistics/current_cycle`)
        .then(response => {
            if (!response.ok && response.status === 404) {
                // No active cycle
                document.getElementById('noCycleMessage').classList.remove('d-none');
                document.getElementById('cycleStats').classList.add('d-none');
                return null;
            }
            return response.json();
        })
        .then(data => {
            if (data) {
                updateCurrentCycle(data);
            }
        })
        .catch(error => {
            if (error.name !== 'SyntaxError') {
                console.error('Error fetching current cycle:', error);
            }
        });
}

// Fetch performance history
function fetchPerformanceHistory() {
    fetch(`${API_BASE_URL}/statistics/history/performance`)
        .then(response => response.json())
        .then(data => {
            updatePerformanceCharts(data);
        })
        .catch(error => console.error('Error fetching performance history:', error));
}

// Fetch service performance
function fetchServicePerformance() {
    fetch(`${API_BASE_URL}/statistics/services`)
        .then(response => response.json())
        .then(data => {
            updateServicePerformance(data);
        })
        .catch(error => console.error('Error fetching service performance:', error));
}

// Update global statistics
function updateGlobalStats(data) {
    document.getElementById('totalAttempts').textContent = data.total_attempts;
    document.getElementById('successfulCreations').textContent = data.successful_creations;
    document.getElementById('failedCreations').textContent = data.failed_creations;
    document.getElementById('successRate').textContent = `${data.success_rate.toFixed(2)}%`;
    document.getElementById('avgCreationTime').textContent = `${data.average_creation_time.toFixed(2)}s`;
    document.getElementById('accountsPerHour').textContent = data.accounts_per_hour.toFixed(2);
    
    // Update success rate color
    const successRateElement = document.getElementById('successRate');
    if (data.success_rate >= 70) {
        successRateElement.className = 'stat-value success-rate';
    } else if (data.success_rate >= 40) {
        successRateElement.className = 'stat-value text-warning';
    } else {
        successRateElement.className = 'stat-value failure-rate';
    }
}

// Update current cycle
function updateCurrentCycle(data) {
    document.getElementById('noCycleMessage').classList.add('d-none');
    document.getElementById('cycleStats').classList.remove('d-none');
    
    document.getElementById('cycleId').textContent = data.cycle_id;
    document.getElementById('cycleAttempts').textContent = data.total_attempts;
    document.getElementById('cycleSuccessful').textContent = data.successful_creations;
    document.getElementById('cycleFailed').textContent = data.failed_creations;
    
    // Calculate runtime
    const startTime = new Date(data.start_time);
    const now = new Date();
    const runtimeSeconds = Math.floor((now - startTime) / 1000);
    document.getElementById('cycleRuntime').textContent = `Running for ${formatSeconds(runtimeSeconds)}`;
    
    // Update success rate progress bar
    const successRate = data.success_rate;
    document.getElementById('cycleSuccessRate').style.width = `${successRate}%`;
    document.getElementById('cycleSuccessRateText').textContent = `${successRate.toFixed(2)}%`;
    
    // Update progress bar color
    const progressBar = document.getElementById('cycleSuccessRate');
    if (successRate >= 70) {
        progressBar.className = 'progress-bar bg-success';
    } else if (successRate >= 40) {
        progressBar.className = 'progress-bar bg-warning';
    } else {
        progressBar.className = 'progress-bar bg-danger';
    }
}

// Update error list
function updateErrorsList(errorCounts) {
    const errorsList = document.getElementById('errorsList');
    errorsList.innerHTML = '';
    
    if (!errorCounts || Object.keys(errorCounts).length === 0) {
        errorsList.innerHTML = `
            <li class="list-group-item text-center text-muted">
                <i class="bi bi-check-circle me-2"></i>
                No errors recorded
            </li>
        `;
        return;
    }
    
    // Sort errors by count
    const sortedErrors = Object.entries(errorCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5); // Show top 5 errors
    
    sortedErrors.forEach(([errorType, count]) => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.innerHTML = `
            <span>
                <i class="bi bi-exclamation-triangle-fill text-danger me-2"></i>
                ${errorType}
            </span>
            <span class="badge bg-danger rounded-pill">${count}</span>
        `;
        errorsList.appendChild(li);
    });
}

// Update performance charts
function updatePerformanceCharts(data) {
    // Update Success Rate Chart
    if (data.success_rate && data.success_rate.length > 0) {
        const labels = data.success_rate.map(item => {
            const date = new Date(item.timestamp);
            return date.toLocaleTimeString();
        });
        const values = data.success_rate.map(item => item.value);
        
        successRateChart.data.labels = labels;
        successRateChart.data.datasets[0].data = values;
        successRateChart.update();
    }
    
    // Update Creation Time Chart
    if (data.creation_time && data.creation_time.length > 0) {
        const labels = data.creation_time.map(item => {
            const date = new Date(item.timestamp);
            return date.toLocaleTimeString();
        });
        const values = data.creation_time.map(item => item.value);
        
        creationTimeChart.data.labels = labels;
        creationTimeChart.data.datasets[0].data = values;
        creationTimeChart.update();
    }
    
    // Update Accounts Per Hour Chart
    if (data.accounts_per_hour && data.accounts_per_hour.length > 0) {
        const labels = data.accounts_per_hour.map(item => {
            const date = new Date(item.timestamp);
            return date.toLocaleTimeString();
        });
        const values = data.accounts_per_hour.map(item => item.value);
        
        accountsPerHourChart.data.labels = labels;
        accountsPerHourChart.data.datasets[0].data = values;
        accountsPerHourChart.update();
    }
}

// Update service performance
function updateServicePerformance(data) {
    // Group services by type
    const servicesByType = {
        'email': [],
        'proxy': [],
        'browser': []
    };
    
    for (const [key, service] of Object.entries(data)) {
        const type = service.service_type;
        if (servicesByType[type]) {
            servicesByType[type].push(service);
        }
    }
    
    // Update email services
    updateServiceList('emailServicesList', servicesByType.email);
    
    // Update proxy services
    updateServiceList('proxyServicesList', servicesByType.proxy);
    
    // Update browser services
    updateServiceList('browserServicesList', servicesByType.browser);
}

// Update a service list
function updateServiceList(elementId, services) {
    const element = document.getElementById(elementId);
    
    if (!services || services.length === 0) {
        element.innerHTML = `
            <div class="text-center py-3 text-muted">
                <i class="bi bi-info-circle me-2"></i>
                No services data available
            </div>
        `;
        return;
    }
    
    // Sort services by success rate
    services.sort((a, b) => b.success_rate - a.success_rate);
    
    element.innerHTML = '';
    
    services.forEach(service => {
        const serviceDiv = document.createElement('div');
        serviceDiv.className = 'service-item';
        
        const successRateColor = service.success_rate >= 70 ? 'success' : 
                                 service.success_rate >= 40 ? 'warning' : 'danger';
        
        serviceDiv.innerHTML = `
            <div class="d-flex justify-content-between align-items-center">
                <div>
                    <h6 class="mb-1">${service.service_name}</h6>
                    <small class="text-muted">
                        ${service.total_uses} uses • 
                        Avg response: ${service.average_response_time.toFixed(2)}s
                        ${service.last_used ? '• Last used: ' + new Date(service.last_used).toLocaleString() : ''}
                    </small>
                </div>
                <div class="text-end">
                    <span class="badge bg-${successRateColor}">${service.success_rate.toFixed(2)}%</span>
                </div>
            </div>
            <div class="progress mt-2">
                <div class="progress-bar bg-${successRateColor}" 
                     role="progressbar" 
                     style="width: ${service.success_rate}%">
                </div>
            </div>
        `;
        
        element.appendChild(serviceDiv);
    });
}

// Update uptime display
function updateUptime(uptimeSeconds) {
    const uptime = formatSeconds(uptimeSeconds);
    document.getElementById('uptime').textContent = `Uptime: ${uptime}`;
}

// Format seconds to human readable format
function formatSeconds(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    } else {
        return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
}