/**
 * Search Integration Service
 * Integrates filters with existing search functionality
 */

class SearchIntegration {
    constructor() {
        this.currentSearchParams = new URLSearchParams();
        this.searchHistory = [];
        this.maxHistoryItems = 10;
        this.init();
    }
    
    init() {
        this.setupURLSync();
        this.setupSearchHistory();
        this.setupKeyboardShortcuts();
        this.loadFromURL();
    }
    
    setupURLSync() {
        // Update URL when filters change
        document.addEventListener('filterChange', (event) => {
            this.updateURL(event.detail);
        });
        
        // Listen for browser back/forward
        window.addEventListener('popstate', (event) => {
            this.loadFromURL();
        });
    }
    
    setupSearchHistory() {
        // Load search history from localStorage
        this.searchHistory = this.loadSearchHistory();
        this.renderSearchHistory();
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (event) => {
            // Ctrl/Cmd + K to focus search
            if ((event.ctrlKey || event.metaKey) && event.key === 'k') {
                event.preventDefault();
                const searchInput = document.getElementById('searchInput');
                if (searchInput) {
                    searchInput.focus();
                    searchInput.select();
                }
            }
            
            // Ctrl/Cmd + Shift + F to focus filters
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key === 'F') {
                event.preventDefault();
                this.toggleFiltersPanel();
            }
        });
    }
    
    updateURL(filters) {
        const url = new URL(window.location);
        
        // Clear existing filter parameters
        const filterKeys = [
            'court', 'status', 'year', 'judge', 'section', 'citation',
            'party', 'advocate', 'case_type', 'bench_type', 'appeal',
            'petitioner', 'legal_issue'
        ];
        
        filterKeys.forEach(key => {
            url.searchParams.delete(key);
        });
        
        // Add current filters
        Object.entries(filters).forEach(([key, values]) => {
            if (values.length > 0) {
                url.searchParams.set(key, values.join(','));
            }
        });
        
        // Add search query
        const searchInput = document.getElementById('searchInput');
        if (searchInput && searchInput.value.trim()) {
            url.searchParams.set('q', searchInput.value.trim());
        }
        
        // Update URL without page reload
        window.history.pushState({}, '', url);
    }
    
    loadFromURL() {
        const url = new URL(window.location);
        const filters = {};
        
        // Load filters from URL
        const filterKeys = [
            'court', 'status', 'year', 'judge', 'section', 'citation',
            'party', 'advocate', 'case_type', 'bench_type', 'appeal',
            'petitioner', 'legal_issue'
        ];
        
        filterKeys.forEach(key => {
            const value = url.searchParams.get(key);
            if (value) {
                filters[key] = value.split(',').map(v => v.trim()).filter(v => v);
            } else {
                filters[key] = [];
            }
        });
        
        // Load search query
        const searchQuery = url.searchParams.get('q');
        if (searchQuery) {
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.value = searchQuery;
            }
        }
        
        // Apply filters
        if (window.filterManager) {
            window.filterManager.setFilters(filters);
        }
        
        // Perform search if there's a query or filters
        if (searchQuery || Object.values(filters).some(values => values.length > 0)) {
            if (window.filterManager) {
                window.filterManager.performSearch();
            }
        }
    }
    
    addToSearchHistory(searchParams) {
        const historyItem = {
            id: Date.now().toString(),
            query: searchParams.get('q') || '',
            filters: this.extractFiltersFromParams(searchParams),
            timestamp: new Date().toISOString(),
            resultCount: 0 // Will be updated after search
        };
        
        // Remove duplicate if exists
        this.searchHistory = this.searchHistory.filter(item => 
            item.query !== historyItem.query || 
            JSON.stringify(item.filters) !== JSON.stringify(historyItem.filters)
        );
        
        // Add to beginning
        this.searchHistory.unshift(historyItem);
        
        // Limit history size
        if (this.searchHistory.length > this.maxHistoryItems) {
            this.searchHistory = this.searchHistory.slice(0, this.maxHistoryItems);
        }
        
        this.saveSearchHistory();
        this.renderSearchHistory();
    }
    
    extractFiltersFromParams(params) {
        const filters = {};
        const filterKeys = [
            'court', 'status', 'year', 'judge', 'section', 'citation',
            'party', 'advocate', 'case_type', 'bench_type', 'appeal',
            'petitioner', 'legal_issue'
        ];
        
        filterKeys.forEach(key => {
            const value = params.get(key);
            filters[key] = value ? value.split(',').map(v => v.trim()) : [];
        });
        
        return filters;
    }
    
    loadSearchHistory() {
        try {
            const saved = localStorage.getItem('legalCaseSearch_history');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Error loading search history:', error);
            return [];
        }
    }
    
    saveSearchHistory() {
        try {
            localStorage.setItem('legalCaseSearch_history', JSON.stringify(this.searchHistory));
        } catch (error) {
            console.error('Error saving search history:', error);
        }
    }
    
    renderSearchHistory() {
        const container = document.getElementById('searchHistory');
        if (!container) return;
        
        if (this.searchHistory.length === 0) {
            container.innerHTML = `
                <div class="history-header">
                    <h3>Search History</h3>
                    <p>No recent searches</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="history-header">
                <h3>Search History</h3>
                <button class="clear-history-btn" onclick="searchIntegration.clearSearchHistory()">
                    Clear All
                </button>
            </div>
            <div class="history-list">
                ${this.searchHistory.map(item => `
                    <div class="history-item" data-history-id="${item.id}">
                        <div class="history-content">
                            <div class="history-query">${item.query || 'No query'}</div>
                            <div class="history-filters">
                                ${this.renderHistoryFilters(item.filters)}
                            </div>
                            <div class="history-meta">
                                <span class="history-time">${this.formatTime(item.timestamp)}</span>
                                ${item.resultCount > 0 ? `<span class="history-count">${item.resultCount} results</span>` : ''}
                            </div>
                        </div>
                        <div class="history-actions">
                            <button class="load-history-btn" onclick="searchIntegration.loadFromHistory('${item.id}')">
                                Load
                            </button>
                            <button class="delete-history-btn" onclick="searchIntegration.deleteFromHistory('${item.id}')">
                                Delete
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    renderHistoryFilters(filters) {
        const activeFilters = Object.entries(filters).filter(([key, values]) => values.length > 0);
        
        if (activeFilters.length === 0) {
            return '<span class="no-filters">No filters</span>';
        }
        
        return activeFilters.map(([key, values]) => `
            <span class="history-filter-tag">
                ${this.getFilterDisplayName(key)}: ${values.join(', ')}
            </span>
        `).join('');
    }
    
    getFilterDisplayName(facetType) {
        const displayNames = {
            court: 'Court',
            status: 'Status',
            year: 'Year',
            judge: 'Judge',
            section: 'Section',
            citation: 'Citation',
            party: 'Party',
            advocate: 'Advocate',
            case_type: 'Type',
            bench_type: 'Bench',
            appeal: 'Appeal',
            petitioner: 'Petitioner',
            legal_issue: 'Issue'
        };
        return displayNames[facetType] || facetType;
    }
    
    formatTime(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;
        
        return date.toLocaleDateString();
    }
    
    loadFromHistory(historyId) {
        const item = this.searchHistory.find(h => h.id === historyId);
        if (!item) return;
        
        // Set search query
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = item.query;
        }
        
        // Apply filters
        if (window.filterManager) {
            window.filterManager.setFilters(item.filters);
        }
        
        // Perform search
        if (window.filterManager) {
            window.filterManager.performSearch();
        }
    }
    
    deleteFromHistory(historyId) {
        this.searchHistory = this.searchHistory.filter(h => h.id !== historyId);
        this.saveSearchHistory();
        this.renderSearchHistory();
    }
    
    clearSearchHistory() {
        if (confirm('Are you sure you want to clear all search history?')) {
            this.searchHistory = [];
            this.saveSearchHistory();
            this.renderSearchHistory();
        }
    }
    
    toggleFiltersPanel() {
        const filtersSidebar = document.querySelector('.filters-sidebar');
        if (filtersSidebar) {
            filtersSidebar.style.display = filtersSidebar.style.display === 'none' ? 'block' : 'none';
        }
    }
    
    // Export search configuration
    exportSearchConfig() {
        const config = {
            query: document.getElementById('searchInput')?.value || '',
            filters: window.filterManager ? window.filterManager.getFilters() : {},
            timestamp: new Date().toISOString()
        };
        
        const dataStr = JSON.stringify(config, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = 'search-config.json';
        link.click();
        
        URL.revokeObjectURL(url);
    }
    
    // Import search configuration
    importSearchConfig(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const config = JSON.parse(e.target.result);
                
                // Set search query
                const searchInput = document.getElementById('searchInput');
                if (searchInput && config.query) {
                    searchInput.value = config.query;
                }
                
                // Apply filters
                if (window.filterManager && config.filters) {
                    window.filterManager.setFilters(config.filters);
                }
                
                // Perform search
                if (window.filterManager) {
                    window.filterManager.performSearch();
                }
                
                this.showMessage('Search configuration imported successfully!', 'success');
            } catch (error) {
                this.showMessage('Error importing search configuration', 'error');
            }
        };
        reader.readAsText(file);
    }
    
    showMessage(message, type = 'info') {
        const messageContainer = document.getElementById('messageContainer');
        if (!messageContainer) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        
        messageContainer.appendChild(messageEl);
        
        setTimeout(() => {
            messageEl.remove();
        }, 3000);
    }
    
    // Public methods
    getCurrentSearchParams() {
        return new URLSearchParams(window.location.search);
    }
    
    getSearchHistory() {
        return [...this.searchHistory];
    }
    
    clearAllData() {
        this.searchHistory = [];
        this.saveSearchHistory();
        this.renderSearchHistory();
        
        if (window.filterManager) {
            window.filterManager.clearAllFilters();
        }
        
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = '';
        }
        
        // Clear URL parameters
        window.history.pushState({}, '', window.location.pathname);
    }
}

// Initialize search integration when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.searchIntegration = new SearchIntegration();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SearchIntegration;
}
