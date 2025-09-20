/**
 * Filter Presets and Saved Searches
 * Predefined filter combinations for common search scenarios
 */

class FilterPresets {
    constructor(filterManager) {
        this.filterManager = filterManager;
        this.presets = this.getDefaultPresets();
        this.savedSearches = this.loadSavedSearches();
        this.init();
    }
    
    init() {
        this.renderPresets();
        this.setupEventListeners();
    }
    
    getDefaultPresets() {
        return {
            'constitutional_cases': {
                name: 'Constitutional Cases',
                description: 'Search for constitutional law cases',
                filters: {
                    legal_issue: ['Constitutional'],
                    status: ['Decided'],
                    court: ['Supreme Court', 'High Court']
                },
                icon: '⚖️'
            },
            'criminal_appeals': {
                name: 'Criminal Appeals',
                description: 'Search for criminal appeal cases',
                filters: {
                    appeal: ['Appeal'],
                    section: ['PPC', 'CrPC'],
                    status: ['Decided']
                },
                icon: '🔍'
            },
            'recent_decisions': {
                name: 'Recent Decisions',
                description: 'Search for recent court decisions',
                filters: {
                    year: [2023, 2024],
                    status: ['Decided']
                },
                icon: '📅'
            },
            'pending_cases': {
                name: 'Pending Cases',
                description: 'Search for pending cases',
                filters: {
                    status: ['Pending']
                },
                icon: '⏳'
            },
            'supreme_court_cases': {
                name: 'Supreme Court Cases',
                description: 'Search for Supreme Court cases only',
                filters: {
                    court: ['Supreme Court']
                },
                icon: '🏛️'
            },
            'high_court_cases': {
                name: 'High Court Cases',
                description: 'Search for High Court cases only',
                filters: {
                    court: ['High Court']
                },
                icon: '🏛️'
            },
            'civil_cases': {
                name: 'Civil Cases',
                description: 'Search for civil law cases',
                filters: {
                    section: ['CPC'],
                    case_type: ['Petition', 'Application']
                },
                icon: '📋'
            },
            'family_law': {
                name: 'Family Law Cases',
                description: 'Search for family law related cases',
                filters: {
                    legal_issue: ['Family', 'Marriage', 'Divorce', 'Custody']
                },
                icon: '👨‍👩‍👧‍👦'
            },
            'property_disputes': {
                name: 'Property Disputes',
                description: 'Search for property related cases',
                filters: {
                    legal_issue: ['Property', 'Land', 'Real Estate']
                },
                icon: '🏠'
            },
            'commercial_cases': {
                name: 'Commercial Cases',
                description: 'Search for commercial law cases',
                filters: {
                    legal_issue: ['Commercial', 'Business', 'Contract']
                },
                icon: '💼'
            }
        };
    }
    
    renderPresets() {
        const presetsContainer = document.getElementById('filterPresets');
        if (!presetsContainer) return;
        
        presetsContainer.innerHTML = `
            <div class="presets-header">
                <h3>Quick Filters</h3>
                <p>Select a preset to quickly apply common filter combinations</p>
            </div>
            <div class="presets-grid">
                ${Object.entries(this.presets).map(([key, preset]) => `
                    <div class="preset-card" data-preset="${key}">
                        <div class="preset-icon">${preset.icon}</div>
                        <div class="preset-content">
                            <h4>${preset.name}</h4>
                            <p>${preset.description}</p>
                        </div>
                        <button class="apply-preset-btn" data-preset="${key}">
                            Apply
                        </button>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    setupEventListeners() {
        // Preset click handlers
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('apply-preset-btn')) {
                const presetKey = e.target.dataset.preset;
                this.applyPreset(presetKey);
            }
        });
        
        // Save current search
        const saveSearchBtn = document.getElementById('saveSearchBtn');
        if (saveSearchBtn) {
            saveSearchBtn.addEventListener('click', () => {
                this.saveCurrentSearch();
            });
        }
        
        // Load saved searches
        const savedSearchesContainer = document.getElementById('savedSearches');
        if (savedSearchesContainer) {
            this.renderSavedSearches();
        }
    }
    
    applyPreset(presetKey) {
        const preset = this.presets[presetKey];
        if (!preset) return;
        
        // Apply preset filters
        this.filterManager.setFilters(preset.filters);
        
        // Show success message
        this.showMessage(`Applied preset: ${preset.name}`, 'success');
        
        // Perform search with preset
        this.filterManager.performSearch();
    }
    
    saveCurrentSearch() {
        const searchName = prompt('Enter a name for this search:');
        if (!searchName) return;
        
        const currentFilters = this.filterManager.getFilters();
        const searchQuery = document.getElementById('searchInput')?.value || '';
        
        const savedSearch = {
            id: Date.now().toString(),
            name: searchName,
            query: searchQuery,
            filters: currentFilters,
            createdAt: new Date().toISOString()
        };
        
        this.savedSearches.push(savedSearch);
        this.saveSavedSearches();
        this.renderSavedSearches();
        
        this.showMessage(`Search "${searchName}" saved successfully!`, 'success');
    }
    
    renderSavedSearches() {
        const container = document.getElementById('savedSearches');
        if (!container) return;
        
        if (this.savedSearches.length === 0) {
            container.innerHTML = `
                <div class="saved-searches-header">
                    <h3>Saved Searches</h3>
                    <p>No saved searches yet. Create one by clicking "Save Search" after applying filters.</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="saved-searches-header">
                <h3>Saved Searches</h3>
                <p>Your saved search combinations</p>
            </div>
            <div class="saved-searches-list">
                ${this.savedSearches.map(search => `
                    <div class="saved-search-item">
                        <div class="saved-search-content">
                            <h4>${search.name}</h4>
                            <p class="saved-search-query">${search.query || 'No query'}</p>
                            <div class="saved-search-filters">
                                ${this.renderSavedSearchFilters(search.filters)}
                            </div>
                            <small class="saved-search-date">
                                Saved: ${new Date(search.createdAt).toLocaleDateString()}
                            </small>
                        </div>
                        <div class="saved-search-actions">
                            <button class="load-saved-search-btn" data-search-id="${search.id}">
                                Load
                            </button>
                            <button class="delete-saved-search-btn" data-search-id="${search.id}">
                                Delete
                            </button>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
        
        // Add event listeners for saved search actions
        container.querySelectorAll('.load-saved-search-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const searchId = e.target.dataset.searchId;
                this.loadSavedSearch(searchId);
            });
        });
        
        container.querySelectorAll('.delete-saved-search-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const searchId = e.target.dataset.searchId;
                this.deleteSavedSearch(searchId);
            });
        });
    }
    
    renderSavedSearchFilters(filters) {
        const activeFilters = Object.entries(filters).filter(([key, values]) => values.length > 0);
        
        if (activeFilters.length === 0) {
            return '<span class="no-filters">No filters applied</span>';
        }
        
        return activeFilters.map(([key, values]) => `
            <span class="saved-filter-tag">
                ${this.filterManager.getFilterDisplayName(key)}: ${values.join(', ')}
            </span>
        `).join('');
    }
    
    loadSavedSearch(searchId) {
        const search = this.savedSearches.find(s => s.id === searchId);
        if (!search) return;
        
        // Set search query
        const searchInput = document.getElementById('searchInput');
        if (searchInput) {
            searchInput.value = search.query;
        }
        
        // Apply filters
        this.filterManager.setFilters(search.filters);
        
        // Perform search
        this.filterManager.performSearch();
        
        this.showMessage(`Loaded search: ${search.name}`, 'success');
    }
    
    deleteSavedSearch(searchId) {
        if (!confirm('Are you sure you want to delete this saved search?')) {
            return;
        }
        
        this.savedSearches = this.savedSearches.filter(s => s.id !== searchId);
        this.saveSavedSearches();
        this.renderSavedSearches();
        
        this.showMessage('Saved search deleted', 'info');
    }
    
    loadSavedSearches() {
        try {
            const saved = localStorage.getItem('legalCaseSearch_savedSearches');
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Error loading saved searches:', error);
            return [];
        }
    }
    
    saveSavedSearches() {
        try {
            localStorage.setItem('legalCaseSearch_savedSearches', JSON.stringify(this.savedSearches));
        } catch (error) {
            console.error('Error saving searches:', error);
        }
    }
    
    showMessage(message, type = 'info') {
        const messageContainer = document.getElementById('messageContainer');
        if (!messageContainer) return;
        
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        
        messageContainer.appendChild(messageEl);
        
        // Remove message after 3 seconds
        setTimeout(() => {
            messageEl.remove();
        }, 3000);
    }
    
    // Public methods
    addCustomPreset(key, preset) {
        this.presets[key] = preset;
        this.renderPresets();
    }
    
    removePreset(key) {
        delete this.presets[key];
        this.renderPresets();
    }
    
    exportSavedSearches() {
        const dataStr = JSON.stringify(this.savedSearches, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = 'saved-searches.json';
        link.click();
        
        URL.revokeObjectURL(url);
    }
    
    importSavedSearches(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const imported = JSON.parse(e.target.result);
                this.savedSearches = [...this.savedSearches, ...imported];
                this.saveSavedSearches();
                this.renderSavedSearches();
                this.showMessage('Saved searches imported successfully!', 'success');
            } catch (error) {
                this.showMessage('Error importing saved searches', 'error');
            }
        };
        reader.readAsText(file);
    }
}

// Initialize presets when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    if (window.filterManager) {
        window.filterPresets = new FilterPresets(window.filterManager);
    }
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FilterPresets;
}
