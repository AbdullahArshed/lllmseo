// Dashboard JavaScript functionality
class BrandTracker {
    constructor() {
        this.ws = null;
        this.isMonitoring = false;
        this.currentBrand = null;
        this.currentPage = 0;
        this.pageSize = 20;
        this.allMentions = [];
        this.filteredMentions = [];
        
        this.init();
    }

    init() {
        this.connectWebSocket();
        this.loadInitialData();
        this.setupEventListeners();
        this.loadPlatforms();
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus('connected');
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus('disconnected');
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }

    updateConnectionStatus(status) {
        const indicator = document.getElementById('connectionIndicator');
        const text = document.getElementById('connectionText');
        
        indicator.className = 'connection-indicator';
        
        switch (status) {
            case 'connected':
                indicator.classList.add('connection-connected');
                text.textContent = 'Connected';
                break;
            case 'disconnected':
                indicator.classList.add('connection-disconnected');
                text.textContent = 'Disconnected';
                break;
            case 'connecting':
                indicator.classList.add('connection-connecting');
                text.textContent = 'Connecting...';
                break;
            case 'error':
                indicator.classList.add('connection-disconnected');
                text.textContent = 'Connection Error';
                break;
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'mention':
                this.addMentionToDisplay(data.data);
                this.updateStats();
                break;
            case 'status':
                this.updateMonitoringStatus(data.data.is_active, data.data.brand);
                break;
            case 'error':
                this.showError(data.data.message);
                break;
            case 'ping':
                // Respond to ping with pong
                if (this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'pong' }));
                }
                break;
        }
    }

    async loadInitialData() {
        await Promise.all([
            this.loadMentions(),
            this.updateStats(),
            this.loadMonitoringStatus()
        ]);
    }

    async loadMentions() {
        try {
            const response = await fetch(`/api/mentions/?limit=${this.pageSize}`);
            const mentions = await response.json();
            
            this.allMentions = mentions;
            this.applyFilters();
            this.displayMentions();
        } catch (error) {
            console.error('Error loading mentions:', error);
            this.showError('Failed to load mentions');
        }
    }

    async loadMoreMentions() {
        try {
            const offset = this.currentPage * this.pageSize;
            const response = await fetch(`/api/mentions/?limit=${this.pageSize}&offset=${offset}`);
            const mentions = await response.json();
            
            if (mentions.length > 0) {
                this.allMentions.push(...mentions);
                this.applyFilters();
                this.displayMentions();
                this.currentPage++;
            } else {
                document.getElementById('loadMoreBtn').style.display = 'none';
            }
        } catch (error) {
            console.error('Error loading more mentions:', error);
        }
    }

    async loadPlatforms() {
        try {
            const response = await fetch('/api/stats/platforms');
            const data = await response.json();
            
            const platformFilter = document.getElementById('platformFilter');
            data.platforms.forEach(platform => {
                const option = document.createElement('option');
                option.value = platform;
                option.textContent = platform;
                platformFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading platforms:', error);
        }
    }

    async updateStats() {
        try {
            const response = await fetch('/api/stats/');
            const stats = await response.json();
            
            document.getElementById('totalMentions').textContent = stats.total_mentions;
            document.getElementById('recentMentions').textContent = stats.recent_mentions;
            
            // Update connection count from WebSocket manager
            const wsResponse = await fetch('/api/monitoring/status');
            const wsData = await wsResponse.json();
            document.getElementById('connectionCount').textContent = '1'; // Simplified for now
        } catch (error) {
            console.error('Error updating stats:', error);
        }
    }

    async loadMonitoringStatus() {
        try {
            const response = await fetch('/api/monitoring/status');
            const status = await response.json();
            
            this.updateMonitoringStatus(status.is_active, status.current_brand);
        } catch (error) {
            console.error('Error loading monitoring status:', error);
        }
    }

    setupEventListeners() {
        // Search functionality
        document.getElementById('searchInput').addEventListener('input', 
            this.debounce(() => this.applyFilters(), 300)
        );
        
        // Filter functionality
        document.getElementById('platformFilter').addEventListener('change', 
            () => this.applyFilters()
        );
        document.getElementById('sentimentFilter').addEventListener('change', 
            () => this.applyFilters()
        );

        // Enter key for brand input
        document.getElementById('brandInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.startMonitoring();
            }
        });
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    applyFilters() {
        const searchTerm = document.getElementById('searchInput').value.toLowerCase();
        const platformFilter = document.getElementById('platformFilter').value;
        const sentimentFilter = document.getElementById('sentimentFilter').value;

        this.filteredMentions = this.allMentions.filter(mention => {
            const matchesSearch = !searchTerm || 
                mention.mention_text.toLowerCase().includes(searchTerm) ||
                mention.brand_name.toLowerCase().includes(searchTerm) ||
                (mention.triggering_prompt && mention.triggering_prompt.toLowerCase().includes(searchTerm));
            
            const matchesPlatform = !platformFilter || mention.platform === platformFilter;
            const matchesSentiment = !sentimentFilter || mention.sentiment_score === sentimentFilter;

            return matchesSearch && matchesPlatform && matchesSentiment;
        });

        this.displayMentions();
    }

    displayMentions() {
        const container = document.getElementById('mentionsContainer');
        
        if (this.filteredMentions.length === 0) {
            container.innerHTML = '<div class="no-mentions">No mentions found matching your criteria.</div>';
            return;
        }

        container.innerHTML = '';
        this.filteredMentions.forEach((mention, index) => {
            const mentionElement = this.createMentionElement(mention, index);
            container.appendChild(mentionElement);
        });

        // Show load more button if there might be more mentions
        const loadMoreBtn = document.getElementById('loadMoreBtn');
        if (this.allMentions.length >= this.pageSize) {
            loadMoreBtn.style.display = 'block';
        }
    }

    createMentionElement(mention, index) {
        const mentionElement = document.createElement('div');
        mentionElement.className = 'mention-item';
        mentionElement.style.animationDelay = `${index * 0.1}s`;
        
        const timestamp = new Date(mention.timestamp).toLocaleString();
        const sentimentClass = mention.sentiment_score ? 
            `sentiment-${mention.sentiment_score}` : 'sentiment-neutral';
        
        mentionElement.innerHTML = `
            <div class="mention-header">
                <div>
                    <span class="platform-badge">${mention.platform}</span>
                    ${mention.sentiment_score ? 
                        `<span class="sentiment-badge ${sentimentClass}">${mention.sentiment_score}</span>` : ''
                    }
                </div>
                <span class="timestamp">${timestamp}</span>
            </div>
            <div class="mention-text">${this.highlightSearchTerms(mention.mention_text)}</div>
            ${mention.triggering_prompt ? `
                <div class="triggering-prompt">
                    <strong>Triggering Prompt:</strong> "${this.highlightSearchTerms(mention.triggering_prompt)}"
                </div>
            ` : ''}
        `;
        
        return mentionElement;
    }

    highlightSearchTerms(text) {
        const searchTerm = document.getElementById('searchInput').value.trim();
        if (!searchTerm) return text;
        
        const regex = new RegExp(`(${searchTerm})`, 'gi');
        return text.replace(regex, '<mark>$1</mark>');
    }

    addMentionToDisplay(mention) {
        this.allMentions.unshift(mention);
        this.applyFilters();
        
        // Show notification
        this.showNotification(`New mention from ${mention.platform}!`);
    }

    showNotification(message) {
        // Simple notification system
        const notification = document.createElement('div');
        notification.className = 'notification';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #48bb78;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 3000);
    }

    showError(message) {
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #e53e3e;
            color: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            z-index: 1000;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => document.body.removeChild(notification), 300);
        }, 5000);
    }

    updateMonitoringStatus(active, brand) {
        const statusText = document.getElementById('statusText');
        const brandInput = document.getElementById('brandInput');
        
        this.isMonitoring = active;
        this.currentBrand = brand;
        
        if (active && brand) {
            statusText.innerHTML = `
                <span class="status-indicator status-active"></span>
                Monitoring "${brand}" across 7 AI platforms
            `;
            brandInput.value = brand;
        } else {
            statusText.innerHTML = `
                <span class="status-indicator status-inactive"></span>
                Not monitoring
            `;
        }
    }

    async startMonitoring() {
        const brandName = document.getElementById('brandInput').value.trim();
        if (!brandName) {
            alert('Please enter a brand name');
            return;
        }

        try {
            const response = await fetch('/api/monitoring/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({brand_name: brandName})
            });
            
            const data = await response.json();
            if (data.success) {
                this.showNotification(`Started monitoring ${brandName}`);
                await this.loadMentions(); // Refresh mentions
            } else {
                this.showError(data.error || 'Failed to start monitoring');
            }
        } catch (error) {
            console.error('Error starting monitoring:', error);
            this.showError('Failed to start monitoring');
        }
    }

    async stopMonitoring() {
        try {
            const response = await fetch('/api/monitoring/stop', {method: 'POST'});
            const data = await response.json();
            
            if (data.success) {
                this.showNotification('Monitoring stopped');
            } else {
                this.showError(data.error || 'Failed to stop monitoring');
            }
        } catch (error) {
            console.error('Error stopping monitoring:', error);
            this.showError('Failed to stop monitoring');
        }
    }

    async searchMentions() {
        const searchTerm = document.getElementById('searchInput').value.trim();
        if (!searchTerm) {
            await this.loadMentions();
            return;
        }

        try {
            const response = await fetch(`/api/mentions/search/?q=${encodeURIComponent(searchTerm)}`);
            const mentions = await response.json();
            
            this.allMentions = mentions;
            this.applyFilters();
        } catch (error) {
            console.error('Error searching mentions:', error);
            this.showError('Search failed');
        }
    }
}

// Global functions for HTML onclick handlers
let tracker;

function startMonitoring() {
    tracker.startMonitoring();
}

function stopMonitoring() {
    tracker.stopMonitoring();
}

function searchMentions() {
    tracker.searchMentions();
}

function loadMoreMentions() {
    tracker.loadMoreMentions();
}

// Initialize the tracker when the page loads
document.addEventListener('DOMContentLoaded', () => {
    tracker = new BrandTracker();
});

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    
    @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
    
    mark {
        background: #ffd700;
        padding: 1px 2px;
        border-radius: 2px;
    }
`;
document.head.appendChild(style);