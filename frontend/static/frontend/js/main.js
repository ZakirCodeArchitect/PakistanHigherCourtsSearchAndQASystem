/**
 * Main JavaScript for Pakistan Higher Courts Search & QA System
 * Handles common functionality across all pages
 */

// Global configuration
const CONFIG = {
    API_BASE_URL: '/api',
    FRONTEND_API_URL: '/frontend/api',
    SEARCH_ENDPOINT: '/search/',
    SUGGESTIONS_ENDPOINT: '/suggestions/',
    STATUS_ENDPOINT: '/status/',
    DEBOUNCE_DELAY: 300,
    MAX_SUGGESTIONS: 10
};

// Utility functions
const Utils = {
    /**
     * Debounce function to limit API calls
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    /**
     * Format date to readable format
     */
    formatDate: function(dateString) {
        if (!dateString) return 'N/A';
        
        try {
            const date = new Date(dateString);
            return date.toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'short',
                day: 'numeric'
            });
        } catch (error) {
            return dateString;
        }
    },

    /**
     * Format number with commas
     */
    formatNumber: function(num) {
        if (num === null || num === undefined) return '--';
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },

    /**
     * Get CSRF token from cookies
     */
    getCSRFToken: function() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    },

    /**
     * Show notification toast
     */
    showNotification: function(message, type = 'info', duration = 5000) {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast-notification toast-${type}`;
        toast.innerHTML = `
            <div class="toast-content">
                <i class="fas fa-${this.getToastIcon(type)} me-2"></i>
                <span>${message}</span>
                <button class="toast-close" onclick="this.parentElement.parentElement.remove()">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;

        // Add to page
        document.body.appendChild(toast);

        // Show animation
        setTimeout(() => toast.classList.add('show'), 100);

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    },

    /**
     * Get icon for toast type
     */
    getToastIcon: function(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-triangle',
            warning: 'exclamation-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    },

    /**
     * Validate email format
     */
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    /**
     * Copy text to clipboard
     */
    copyToClipboard: async function(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('Copied to clipboard!', 'success', 2000);
        } catch (error) {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            this.showNotification('Copied to clipboard!', 'success', 2000);
        }
    },

    /**
     * Generate unique ID
     */
    generateId: function() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }
};

// API service
const APIService = {
    /**
     * Make API request
     */
    request: async function(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': Utils.getCSRFToken()
            },
            credentials: 'same-origin'
        };

        const finalOptions = { ...defaultOptions, ...options };
        
        try {
            const response = await fetch(url, finalOptions);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    },

    /**
     * GET request
     */
    get: function(url, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const fullUrl = queryString ? `${url}?${queryString}` : url;
        
        return this.request(fullUrl, { method: 'GET' });
    },

    /**
     * POST request
     */
    post: function(url, data = {}) {
        return this.request(url, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },

    /**
     * PUT request
     */
    put: function(url, data = {}) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },

    /**
     * DELETE request
     */
    delete: function(url) {
        return this.request(url, { method: 'DELETE' });
    }
};

// Search service
const SearchService = {
    /**
     * Perform search
     */
    search: async function(query, options = {}) {
        const searchParams = {
            q: query,
            mode: options.mode || 'hybrid',
            filters: options.filters || {},
            offset: options.offset || 0,
            limit: options.limit || 10,
            return_facets: options.return_facets || false,
            highlight: options.highlight || false
        };

        try {
            return await APIService.post(CONFIG.FRONTEND_API_URL + CONFIG.SEARCH_ENDPOINT, searchParams);
        } catch (error) {
            console.error('Search failed:', error);
            throw error;
        }
    },

    /**
     * Get suggestions
     */
    getSuggestions: async function(query, type = 'auto') {
        try {
            return await APIService.get(CONFIG.FRONTEND_API_URL + CONFIG.SUGGESTIONS_ENDPOINT, {
                q: query,
                type: type
            });
        } catch (error) {
            console.error('Suggestions failed:', error);
            throw error;
        }
    },

    /**
     * Get system status
     */
    getStatus: async function() {
        try {
            return await APIService.get(CONFIG.FRONTEND_API_URL + CONFIG.STATUS_ENDPOINT);
        } catch (error) {
            console.error('Status check failed:', error);
            throw error;
        }
    }
};

// UI components
const UIComponents = {
    /**
     * Initialize tooltips
     */
    initTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    /**
     * Initialize popovers
     */
    initPopovers: function() {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    },

    /**
     * Show loading spinner
     */
    showLoading: function(element, text = 'Loading...') {
        if (!element) return;
        
        element.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary mb-3" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
                <p class="text-muted">${text}</p>
            </div>
        `;
    },

    /**
     * Hide loading spinner
     */
    hideLoading: function(element) {
        if (!element) return;
        element.innerHTML = '';
    },

    /**
     * Show error message
     */
    showError: function(element, message) {
        if (!element) return;
        
        element.innerHTML = `
            <div class="alert alert-danger" role="alert">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${message}
            </div>
        `;
    },

    /**
     * Show empty state
     */
    showEmptyState: function(element, message = 'No data available', icon = 'inbox') {
        if (!element) return;
        
        element.innerHTML = `
            <div class="text-center py-5">
                <i class="fas fa-${icon} fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">${message}</h5>
            </div>
        `;
    }
};

// Event handlers
const EventHandlers = {
    /**
     * Handle form submissions
     */
    handleFormSubmit: function(form, callback) {
        if (!form) return;
        
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const submitBtn = form.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            
            // Show loading state
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Processing...';
            
            try {
                await callback(form);
            } catch (error) {
                console.error('Form submission failed:', error);
                Utils.showNotification('An error occurred. Please try again.', 'error');
            } finally {
                // Restore button state
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalText;
            }
        });
    },

    /**
     * Handle search input
     */
    handleSearchInput: function(input, callback, delay = CONFIG.DEBOUNCE_DELAY) {
        if (!input) return;
        
        const debouncedCallback = Utils.debounce(callback, delay);
        input.addEventListener('input', debouncedCallback);
    },

    /**
     * Handle keyboard shortcuts
     */
    handleKeyboardShortcuts: function() {
        document.addEventListener('keydown', function(e) {
            // Ctrl/Cmd + K for search focus
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.querySelector('#searchQuery, .search-input');
                if (searchInput) {
                    searchInput.focus();
                }
            }
            
            // Escape to close modals
            if (e.key === 'Escape') {
                const modals = document.querySelectorAll('.modal.show');
                modals.forEach(modal => {
                    const modalInstance = bootstrap.Modal.getInstance(modal);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                });
            }
        });
    }
};

// Analytics and tracking
const Analytics = {
    /**
     * Track page view
     */
    trackPageView: function(pageName) {
        if (typeof gtag !== 'undefined') {
            gtag('config', 'GA_MEASUREMENT_ID', {
                page_title: pageName,
                page_location: window.location.href
            });
        }
        
        // Custom tracking
        this.logEvent('page_view', { page_name: pageName });
    },

    /**
     * Track search query
     */
    trackSearch: function(query, resultsCount, searchType) {
        this.logEvent('search_query', {
            query: query,
            results_count: resultsCount,
            search_type: searchType
        });
    },

    /**
     * Track user action
     */
    trackAction: function(action, details = {}) {
        this.logEvent('user_action', {
            action: action,
            ...details
        });
    },

    /**
     * Log event (placeholder for analytics implementation)
     */
    logEvent: function(eventName, parameters = {}) {
        console.log('Analytics Event:', eventName, parameters);
        
        // Here you can implement actual analytics tracking
        // For example: Google Analytics, Mixpanel, etc.
    }
};

// Performance monitoring
const Performance = {
    /**
     * Measure page load time
     */
    measurePageLoad: function() {
        window.addEventListener('load', function() {
            const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
            console.log(`Page load time: ${loadTime}ms`);
            
            // Track performance metrics
            if (loadTime > 3000) {
                console.warn('Page load time is slow:', loadTime + 'ms');
            }
        });
    },

    /**
     * Measure API response time
     */
    measureAPIResponse: function(startTime) {
        const responseTime = Date.now() - startTime;
        console.log(`API response time: ${responseTime}ms`);
        
        // Track slow API calls
        if (responseTime > 1000) {
            console.warn('Slow API response:', responseTime + 'ms');
        }
        
        return responseTime;
    }
};

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    console.log('Pakistan Higher Courts Search & QA System - Frontend Initialized');
    
    // Initialize UI components
    UIComponents.initTooltips();
    UIComponents.initPopovers();
    
    // Initialize event handlers
    EventHandlers.handleKeyboardShortcuts();
    
    // Initialize performance monitoring
    Performance.measurePageLoad();
    
    // Track page view
    const pageName = document.title || 'Unknown Page';
    Analytics.trackPageView(pageName);
    
    // Add global error handler
    window.addEventListener('error', function(e) {
        console.error('Global error:', e.error);
        Utils.showNotification('An unexpected error occurred. Please refresh the page.', 'error');
    });
    
    // Add unhandled promise rejection handler
    window.addEventListener('unhandledrejection', function(e) {
        console.error('Unhandled promise rejection:', e.reason);
        Utils.showNotification('An unexpected error occurred. Please try again.', 'error');
    });
});

// Export for use in other scripts
window.PakistanCourts = {
    Utils,
    APIService,
    SearchService,
    UIComponents,
    EventHandlers,
    Analytics,
    Performance,
    CONFIG
};
