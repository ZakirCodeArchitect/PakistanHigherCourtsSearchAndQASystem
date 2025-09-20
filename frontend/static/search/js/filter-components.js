/**
 * Filter Components for Legal Case Search
 * Integrates with existing search interface
 */

class FilterManager {
    constructor() {
        this.filters = {
            court: [],
            status: [],
            year: [],
            judge: [],
            section: [],
            citation: [],
            party: [],
            advocate: [],
            case_type: [],
            bench_type: [],
            appeal: [],
            petitioner: [],
            legal_issue: []
        };
        
        this.suggestions = {};
        this.isLoading = false;
        this.onFilterChange = null;
        
        this.init();
    }
    
    init() {
        console.log('Initializing FilterManager...');
        this.setupEventListeners();
        this.loadFilterSuggestions();
    }
    
    setupEventListeners() {
        // Listen for filter changes
        document.addEventListener('filterChange', (event) => {
            this.handleFilterChange(event.detail);
        });
    }
    
    handleFilterChange(filters) {
        console.log('Filter change detected:', filters);
        // This method can be overridden by external code
        if (this.onFilterChange) {
            this.onFilterChange(filters);
        }
    }
    
    async loadFilterSuggestions() {
        try {
            this.isLoading = true;
            this.updateLoadingState(true);
            
            console.log('Loading filter suggestions...');
            const response = await fetch('/api/search/search/?suggestions=true');
            console.log('Filter suggestions response:', response);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('Filter suggestions data:', data);
            
            if (data.suggestions) {
                this.suggestions = data.suggestions;
                this.renderFilterSuggestions();
            } else {
                console.warn('No suggestions in response:', data);
                // Create mock suggestions for testing
                this.createMockSuggestions();
            }
        } catch (error) {
            console.error('Error loading filter suggestions:', error);
            this.showError('Failed to load filter suggestions: ' + error.message);
            // Create mock suggestions for testing
            this.createMockSuggestions();
        } finally {
            this.isLoading = false;
            this.updateLoadingState(false);
        }
    }
    
    createMockSuggestions() {
        console.log('Creating mock suggestions for testing...');
        this.suggestions = {
            court: [
                { value: 'Supreme Court', count: 150, selected: false },
                { value: 'High Court', count: 300, selected: false },
                { value: 'District Court', count: 200, selected: false }
            ],
            status: [
                { value: 'Decided', count: 400, selected: false },
                { value: 'Pending', count: 100, selected: false },
                { value: 'Dismissed', count: 50, selected: false }
            ],
            year: [
                { value: '2023', count: 200, selected: false },
                { value: '2024', count: 150, selected: false },
                { value: '2022', count: 100, selected: false }
            ],
            judge: [
                { value: 'Justice Ali', count: 50, selected: false },
                { value: 'Justice Khan', count: 45, selected: false },
                { value: 'Justice Ahmed', count: 40, selected: false }
            ],
            section: [
                { value: 'PPC 302', count: 30, selected: false },
                { value: 'CrPC 497', count: 25, selected: false },
                { value: 'Constitution Article 25', count: 20, selected: false }
            ],
            citation: [
                { value: 'PLD 2023 SC 123', count: 15, selected: false },
                { value: '2023 SCMR 456', count: 12, selected: false },
                { value: 'PLJ 2023 LHC 789', count: 10, selected: false }
            ],
            party: [
                { value: 'State', count: 200, selected: false },
                { value: 'Pakistan', count: 150, selected: false },
                { value: 'Government', count: 100, selected: false }
            ],
            advocate: [
                { value: 'Mr. Ali', count: 30, selected: false },
                { value: 'Ms. Khan', count: 25, selected: false },
                { value: 'Mr. Ahmed', count: 20, selected: false }
            ],
            case_type: [
                { value: 'Criminal Appeal', count: 100, selected: false },
                { value: 'Constitutional Petition', count: 80, selected: false },
                { value: 'Civil Suit', count: 60, selected: false }
            ],
            bench_type: [
                { value: 'Single Bench', count: 200, selected: false },
                { value: 'Division Bench', count: 150, selected: false },
                { value: 'Full Bench', count: 50, selected: false }
            ],
            appeal: [
                { value: 'Appeal', count: 120, selected: false },
                { value: 'Revision', count: 80, selected: false },
                { value: 'Review', count: 40, selected: false }
            ],
            petitioner: [
                { value: 'Petitioner A', count: 25, selected: false },
                { value: 'Petitioner B', count: 20, selected: false },
                { value: 'Petitioner C', count: 15, selected: false }
            ],
            legal_issue: [
                { value: 'Constitutional Rights', count: 60, selected: false },
                { value: 'Criminal Procedure', count: 80, selected: false },
                { value: 'Family Law', count: 40, selected: false }
            ]
        };
        this.renderFilterSuggestions();
    }
    
    renderFilterSuggestions() {
        console.log('Rendering filter suggestions...');
        const filterContainer = document.getElementById('filterContainer');
        if (!filterContainer) {
            console.error('Filter container not found!');
            return;
        }
        
        console.log('Filter container found:', filterContainer);
        console.log('Suggestions data:', this.suggestions);
        
        // Clear existing content
        filterContainer.innerHTML = '';
        
        // Create filter sections for each facet type
        Object.entries(this.suggestions).forEach(([facetType, suggestions]) => {
            console.log(`Creating filter section for ${facetType}:`, suggestions);
            const filterSection = this.createFilterSection(facetType, suggestions);
            filterContainer.appendChild(filterSection);
        });
        
        console.log('Filter sections created and added to container');
        
        // Show the filter container if it was hidden
        if (filterContainer && filterContainer.style.display === 'none') {
            console.log('Showing filter container...');
            filterContainer.style.display = 'block';
        }
    }
    
    createFilterSection(facetType, suggestions) {
        console.log(`Creating filter section for ${facetType} with ${suggestions.length} suggestions`);
        
        const section = document.createElement('div');
        section.className = 'filter-section';
        section.innerHTML = `
            <div class="filter-header">
                <h6>${this.getFilterDisplayName(facetType)}</h6>
                <button class="filter-toggle" data-facet="${facetType}">
                    <span class="toggle-icon">▼</span>
                </button>
            </div>
            <div class="filter-content" id="filter-${facetType}">
                <div class="filter-search">
                    <input type="text" 
                           class="form-control form-control-sm filter-search-input" 
                           placeholder="Search ${this.getFilterDisplayName(facetType)}..."
                           data-facet="${facetType}">
                </div>
                <div class="filter-options" id="options-${facetType}">
                    ${this.renderFilterOptions(facetType, suggestions)}
                </div>
                <div class="filter-actions">
                    <button class="btn btn-sm btn-outline-primary select-all-btn" data-facet="${facetType}">Select All</button>
                    <button class="btn btn-sm btn-outline-secondary clear-all-btn" data-facet="${facetType}">Clear All</button>
                </div>
            </div>
        `;
        
        // Add event listeners
        this.addFilterSectionListeners(section, facetType);
        
        console.log(`Filter section created for ${facetType}`);
        return section;
    }
    
    renderFilterOptions(facetType, suggestions) {
        console.log(`Rendering filter options for ${facetType}:`, suggestions);
        
        if (!suggestions || suggestions.length === 0) {
            console.warn(`No suggestions for ${facetType}`);
            return '<div class="text-muted">No options available</div>';
        }
        
        const optionsHtml = suggestions.map(suggestion => `
            <div class="form-check filter-option">
                <input class="form-check-input" type="checkbox" 
                       value="${suggestion.value}" 
                       data-facet="${facetType}"
                       id="filter-${facetType}-${suggestion.value.replace(/\s+/g, '-')}"
                       ${suggestion.selected ? 'checked' : ''}>
                <label class="form-check-label" for="filter-${facetType}-${suggestion.value.replace(/\s+/g, '-')}">
                    <span class="option-text">${suggestion.value}</span>
                    <span class="option-count">(${suggestion.count})</span>
                </label>
            </div>
        `).join('');
        
        console.log(`Generated ${suggestions.length} options for ${facetType}`);
        return optionsHtml;
    }
    
    addFilterSectionListeners(section, facetType) {
        // Toggle section visibility
        const toggleBtn = section.querySelector('.filter-toggle');
        const content = section.querySelector('.filter-content');
        
        toggleBtn.addEventListener('click', () => {
            const isVisible = content.style.display !== 'none';
            content.style.display = isVisible ? 'none' : 'block';
            toggleBtn.querySelector('.toggle-icon').textContent = isVisible ? '▶' : '▼';
        });
        
        // Filter search
        const searchInput = section.querySelector('.filter-search-input');
        searchInput.addEventListener('input', (e) => {
            this.filterOptions(facetType, e.target.value);
        });
        
        // Checkbox changes
        const checkboxes = section.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateFilterValue(facetType);
            });
        });
        
        // Select all button
        const selectAllBtn = section.querySelector('.select-all-btn');
        selectAllBtn.addEventListener('click', () => {
            this.selectAllOptions(facetType);
        });
        
        // Clear all button
        const clearAllBtn = section.querySelector('.clear-all-btn');
        clearAllBtn.addEventListener('click', () => {
            this.clearAllOptions(facetType);
        });
    }
    
    filterOptions(facetType, searchTerm) {
        const optionsContainer = document.getElementById(`options-${facetType}`);
        const options = optionsContainer.querySelectorAll('.filter-option');
        
        options.forEach(option => {
            const text = option.querySelector('.option-text').textContent.toLowerCase();
            const matches = text.includes(searchTerm.toLowerCase());
            option.style.display = matches ? 'block' : 'none';
        });
    }
    
    updateFilterValue(facetType) {
        const checkboxes = document.querySelectorAll(`input[data-facet="${facetType}"]:checked`);
        this.filters[facetType] = Array.from(checkboxes).map(cb => cb.value);
        
        // Trigger filter change event
        this.triggerFilterChange();
    }
    
    selectAllOptions(facetType) {
        const checkboxes = document.querySelectorAll(`input[data-facet="${facetType}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = true;
        });
        this.updateFilterValue(facetType);
    }
    
    clearAllOptions(facetType) {
        const checkboxes = document.querySelectorAll(`input[data-facet="${facetType}"]`);
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        this.updateFilterValue(facetType);
    }
    
    triggerFilterChange() {
        if (this.onFilterChange) {
            this.onFilterChange(this.filters);
        }
        
        // Dispatch custom event
        const event = new CustomEvent('filterChange', {
            detail: this.filters
        });
        document.dispatchEvent(event);
    }
    
    getFilterDisplayName(facetType) {
        const displayNames = {
            court: 'Court',
            status: 'Status',
            year: 'Year',
            judge: 'Judge',
            section: 'Legal Section',
            citation: 'Citation',
            party: 'Party',
            advocate: 'Advocate',
            case_type: 'Case Type',
            bench_type: 'Bench Type',
            appeal: 'Appeal',
            petitioner: 'Petitioner',
            legal_issue: 'Legal Issue'
        };
        return displayNames[facetType] || facetType;
    }
    
    buildQueryString() {
        const params = new URLSearchParams();
        
        // Add search query
        const searchInput = document.getElementById('searchQuery');
        if (searchInput && searchInput.value.trim()) {
            params.append('q', searchInput.value.trim());
        }
        
        // Add filters
        Object.entries(this.filters).forEach(([key, values]) => {
            if (values.length > 0) {
                params.append(key, values.join(','));
            }
        });
        
        // Add other parameters
        params.append('return_facets', 'true');
        params.append('highlight', 'true');
        
        return params.toString();
    }
    
    // Public methods for external use
    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        this.updateFilterDisplay();
    }
    
    getFilters() {
        return { ...this.filters };
    }
    
    clearAllFilters() {
        this.filters = {
            court: [], status: [], year: [], judge: [], section: [],
            citation: [], party: [], advocate: [], case_type: [],
            bench_type: [], appeal: [], petitioner: [], legal_issue: []
        };
        
        // Uncheck all checkboxes
        document.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.checked = false;
        });
        
        this.triggerFilterChange();
    }
    
    updateFilterDisplay() {
        Object.entries(this.filters).forEach(([facetType, values]) => {
            const checkboxes = document.querySelectorAll(`input[data-facet="${facetType}"]`);
            checkboxes.forEach(checkbox => {
                checkbox.checked = values.includes(checkbox.value);
            });
        });
    }
    
    updateLoadingState(isLoading) {
        console.log('Filter loading state:', isLoading);
        
        const filterContainer = document.getElementById('filterContainer');
        if (filterContainer) {
            if (isLoading) {
                filterContainer.innerHTML = `
                    <div class="filter-loading">
                        <div class="spinner-border text-primary" role="status">
                            <span class="visually-hidden">Loading...</span>
                        </div>
                        <p class="mt-2">Loading filter options...</p>
                    </div>
                `;
            }
        }
    }
    
    showError(message) {
        console.error('Filter error:', message);
        
        // Show error in the filter container
        const filterContainer = document.getElementById('filterContainer');
        if (filterContainer) {
            filterContainer.innerHTML = `
                <div class="filter-error">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
            `;
        }
    }
}

// Initialize filter manager when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.filterManager = new FilterManager();
});

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FilterManager;
}