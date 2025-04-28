document.addEventListener('DOMContentLoaded', function() {
    // Add script tags for XLSX and FileSaver if not already present
    if (typeof XLSX === 'undefined') {
        loadScript('https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js');
    }
    
    if (typeof saveAs === 'undefined') {
        loadScript('https://cdnjs.cloudflare.com/ajax/libs/FileSaver.js/2.0.5/FileSaver.min.js');
    }
    
    initializeForm();
    initializeToasts();
    setupEventListeners();
    initializeDarkMode();
});

// Form Handling
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
            <svg class="animate-spin h-5 w-5 mr-3 inline" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Searching...
        `;
        
        showLoadingOverlay();
        
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
        initializeToasts(); // Make sure toast container exists
        showToast('Search completed successfully', 'success');
        
    } catch (error) {
        console.error('Search error:', error);
        initializeToasts(); // Make sure toast container exists
        showToast('Failed to search colleges. Please try again.', 'error');
    } finally {
        submitButton.disabled = false;
        submitButton.innerHTML = originalButtonText;
        hideLoadingOverlay();
    }
}

// Table Sorting
function sortTable() {
    const field = document.getElementById('sortField').value;
    const order = document.getElementById('sortOrder').value;
    const tbody = document.querySelector('table tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));

    rows.sort((a, b) => {
        let aValue = getCellValue(a, field);
        let bValue = getCellValue(b, field);

        if (isNumeric(aValue) && isNumeric(bValue)) {
            aValue = parseFloat(aValue);
            bValue = parseFloat(bValue);
        }

        if (order === 'asc') {
            return aValue > bValue ? 1 : -1;
        } else {
            return aValue < bValue ? 1 : -1;
        }
    });

    tbody.innerHTML = '';
    rows.forEach(row => tbody.appendChild(row));
}

function getCellValue(row, field) {
    const cellMap = {
        'college_name': 0,
        'branch_name': 1,
        'category': 2,
        'quota_type': 3,
        'rank': 4,
        'percentile': 4
    };

    const cell = row.querySelector(`td:nth-child(${cellMap[field] + 1})`);
    let value = cell.textContent.trim();

    if (field === 'rank') {
        value = value.match(/Rank: (\d+)/)[1];
    } else if (field === 'percentile') {
        value = value.match(/Percentile: ([\d.]+)/)[1];
    } else {
        value = cell.querySelector('.text-sm').textContent.trim();
    }

    return value;
}

// Variables to store current results
let currentResults = [];

// Updated Export Functionality
async function exportToCSV() {
    try {
        initializeToasts(); // Make sure toast container exists
        showToast('Preparing export...', 'info');
        
        const form = document.getElementById('searchForm');
        const formData = new FormData(form);
        
        const response = await fetch('/export', {
            method: 'POST',
            body: formData
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
        initializeToasts(); // Make sure toast container exists
        showToast('Failed to export results', 'error');
    }
}

// New Download Handler for Excel
function handleDownload() {
    if (!currentResults || currentResults.length === 0) {
        initializeToasts();
        showToast('No data available to download', 'error');
        return;
    }
    try {
        const worksheet = XLSX.utils.json_to_sheet(currentResults);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, 'MHTCET Colleges');
        
        const excelBuffer = XLSX.write(workbook, { bookType: 'xlsx', type: 'array' });
        const blob = new Blob([excelBuffer], { 
            type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
        });
        
        saveAs(blob, `MHTCET_Colleges_${new Date().toISOString().split('T')[0]}.xlsx`);
        
        initializeToasts();
        showToast('Excel file downloaded successfully', 'success');
    } catch (error) {
        console.error('Download error:', error);
        initializeToasts();
        showToast('Failed to download Excel file', 'error');
    }
}

// Helper function for displaying errors (used in handleDownload)
function showError(message) {
    initializeToasts();
    showToast(message, 'error');
}

// Toast Notifications
function initializeToasts() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-4 right-4 z-50 space-y-2';
        document.body.appendChild(container);
    }
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) {
        initializeToasts();
    }
    
    const toast = document.createElement('div');
    
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        info: 'bg-blue-500',
        warning: 'bg-yellow-500'
    };
    
    toast.className = `${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg flex items-center`;
    
    const icons = {
        success: '<i class="fas fa-check-circle mr-2"></i>',
        error: '<i class="fas fa-exclamation-circle mr-2"></i>',
        info: '<i class="fas fa-info-circle mr-2"></i>',
        warning: '<i class="fas fa-exclamation-triangle mr-2"></i>'
    };
    
    toast.innerHTML = `${icons[type]}<span>${message}</span>`;
    
    document.getElementById('toast-container').appendChild(toast);
    
    // Animate in
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(1rem)';
    requestAnimationFrame(() => {
        toast.style.transition = 'all 0.3s ease';
        toast.style.opacity = '1';
        toast.style.transform = 'translateY(0)';
    });
    
    // Remove after delay
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(1rem)';
        setTimeout(() => {
            if (document.getElementById('toast-container').contains(toast)) {
                document.getElementById('toast-container').removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Loading Overlay
function showLoadingOverlay() {
    const overlay = document.createElement('div');
    overlay.id = 'loading-overlay';
    overlay.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50';
    overlay.innerHTML = `
        <div class="bg-white dark:bg-gray-800 rounded-lg p-4 flex items-center space-x-3">
            <div class="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
            <span class="text-gray-700 dark:text-gray-300">Loading...</span>
        </div>
    `;
    document.body.appendChild(overlay);
}

function hideLoadingOverlay() {
    const overlay = document.getElementById('loading-overlay');
    if (overlay) {
        overlay.remove();
    }
}

// Utility Functions
function isNumeric(value) {
    return !isNaN(parseFloat(value)) && isFinite(value);
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

// Function to dynamically load external scripts
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Event Listeners
function setupEventListeners() {
    // Sort controls
    const sortField = document.getElementById('sortField');
    const sortOrder = document.getElementById('sortOrder');
    if (sortField && sortOrder) {
        sortField.addEventListener('change', sortTable);
        sortOrder.addEventListener('change', sortTable);
    }

    // Form inputs
    const formInputs = document.querySelectorAll('input, select');
    formInputs.forEach(input => {
        input.addEventListener('change', debounce(() => {
            localStorage.setItem(`form_${input.id}`, input.value);
        }, 500));
    });
    
    // Download button (Excel export)
    const downloadButton = document.getElementById('downloadButton');
    if (downloadButton) {
        downloadButton.addEventListener('click', () => {
            // Extract data from table before downloading
            extractTableData();
            handleDownload();
        });
    }
    
    // Extract data initially if results are present
    if (document.querySelector('table tbody tr')) {
        extractTableData();
    }
}

// Dark Mode
function initializeDarkMode() {
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        document.documentElement.classList.add('dark');
    }

    const darkModeToggle = document.getElementById('darkModeToggle');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', () => {
            document.documentElement.classList.toggle('dark');
            localStorage.setItem('darkMode', document.documentElement.classList.contains('dark'));
        });
    }
}

// Form State Persistence
function restoreFormState() {
    const formInputs = document.querySelectorAll('input, select');
    formInputs.forEach(input => {
        const savedValue = localStorage.getItem(`form_${input.id}`);
        if (savedValue) {
            input.value = savedValue;
        }
    });
}

// Extract and update current results from the table
function extractTableData() {
    const tableRows = document.querySelectorAll('table tbody tr');
    const extractedResults = [];
    
    if (tableRows && tableRows.length > 0) {
        tableRows.forEach(row => {
            const columns = row.querySelectorAll('td');
            if (columns && columns.length >= 5) {
                const result = {
                    college_name: columns[0].querySelector('.text-sm').textContent.trim(),
                    college_code: columns[0].querySelector('.text-xs').textContent.replace('Code:', '').trim(),
                    branch_name: columns[1].querySelector('.text-sm').textContent.trim(),
                    branch_code: columns[1].querySelector('.text-xs').textContent.replace('Code:', '').trim(),
                    category: columns[2].querySelector('.text-sm').textContent.trim(),
                    category_code: columns[2].querySelector('.text-xs').textContent.replace('Code:', '').trim(),
                    quota_type: columns[3].querySelector('.text-sm').textContent.trim(),
                    allocation_type: columns[3].querySelector('.text-xs').textContent.trim(),
                    rank: columns[4].querySelector('.text-sm').textContent.replace('Rank:', '').trim(),
                    percentile: columns[4].querySelector('.text-xs').textContent.replace('Percentile:', '').trim()
                };
                extractedResults.push(result);
            }
        });
    }
    
    currentResults = extractedResults;
    return extractedResults;
}

// Update current results
function updateCurrentResults(results) {
    currentResults = results;
}

// Initialize on load
window.addEventListener('load', restoreFormState);
