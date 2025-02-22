document.addEventListener('DOMContentLoaded', function() {
    // Initialize components
    initializeForm();
    initializeToasts();
    setupEventListeners();
});

function initializeForm() {
    const searchForm = document.getElementById('searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', handleFormSubmit);
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitButton = form.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.innerHTML;
    
    try {
        // Show loading state
        submitButton.disabled = true;
        submitButton.innerHTML = `
            <svg class="animate-spin h-5 w-5 mr-3" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Searching...
        `;
        
        // Show loading overlay
        document.body.classList.add('loading');
        
        const formData = new FormData(form);
        const response = await fetch(form.action, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            throw new Error('Search failed');
        }
        
        const html = await response.text();
        document.documentElement.innerHTML = html;
        
        // Reinitialize components after page update
        initializeForm();
        showToast('Search completed successfully', 'success');
        
    } catch (error) {
        console.error('Search error:', error);
        showToast('Failed to search colleges. Please try again.', 'error');
    } finally {
        // Reset button state
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        
        // Hide loading overlay
        document.body.classList.remove('loading');
    }
}

function initializeToasts() {
    // Create toast container if it doesn't exist
    if (!document.getElementById('toast-container')) {
        const toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'fixed bottom-4 right-4 z-50';
        document.body.appendChild(toastContainer);
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };
    
    toast.className = `${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg mb-2 animate-fade-in`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    // Remove toast after 3 seconds
    setTimeout(() => {
        toast.classList.add('animate-fade-out');
        setTimeout(() => container.removeChild(toast), 300);
    }, 3000);
}

function setupEventListeners() {
    // Export button handler
    const exportButton = document.getElementById('exportResultsBtn');
    if (exportButton) {
        exportButton.addEventListener('click', handleExport);
    }
    
    // Sort handlers
    const sortButtons = document.querySelectorAll('[data-sort]');
    sortButtons.forEach(button => {
        button.addEventListener('click', handleSort);
    });
    
    // Filter handlers
    const filterInputs = document.querySelectorAll('[data-filter]');
    filterInputs.forEach(input => {
        input.addEventListener('input', debounce(handleFilter, 300));
    });
}

async function handleExport() {
    try {
        showToast('Preparing export...', 'info');
        
        const response = await fetch('/export', {
            method: 'POST',
            body: new FormData(document.getElementById('searchForm'))
        });
        
        if (!response.ok) throw new Error('Export failed');
        
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'college_results.csv';
        document.body.appendChild(a);
        a.click();
        a.remove();
        
        showToast('Export completed successfully', 'success');
    } catch (error) {
        console.error('Export error:', error);
        showToast('Failed to export results', 'error');
    }
}

function handleSort(event) {
    const column = event.target.dataset.sort;
    const currentOrder = event.target.dataset.order || 'asc';
    const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
    
    // Update sort indicators
    document.querySelectorAll('[data-sort]').forEach(el => {
        el.dataset.order = el === event.target ? newOrder : '';
    });
    
    sortTable(column, newOrder);
}

function sortTable(column, order) {
    const table = document.querySelector('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        const aValue = a.querySelector(`td[data-column="${column}"]`).textContent;
        const bValue = b.querySelector(`td[data-column="${column}"]`).textContent;
        
        return order === 'asc' 
            ? aValue.localeCompare(bValue, undefined, {numeric: true})
            : bValue.localeCompare(aValue, undefined, {numeric: true});
    });
    
    tbody.innerHTML = '';
    rows.forEach(row => tbody.appendChild(row));
}

function handleFilter(event) {
    const column = event.target.dataset.filter;
    const value = event.target.value.toLowerCase();
    
    const rows = document.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cell = row.querySelector(`td[data-column="${column}"]`);
        const text = cell.textContent.toLowerCase();
        row.style.display = text.includes(value) ? '' : 'none';
    });
}

function debounce(func, wait) {
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

// Dark mode toggle
if (localStorage.getItem('darkMode') === 'true') {
    document.documentElement.classList.add('dark');
}
