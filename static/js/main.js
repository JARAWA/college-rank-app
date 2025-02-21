document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        new Tooltip(tooltip);
    });

    // Handle college comparison
    const compareCheckboxes = document.querySelectorAll('.compare-checkbox');
    compareCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', handleCompareChange);
    });

    // Export results
    const exportButton = document.getElementById('exportResults');
    if (exportButton) {
        exportButton.addEventListener('click', exportToExcel);
    }

    // Save favorites
    const favoriteButtons = document.querySelectorAll('.favorite-btn');
    favoriteButtons.forEach(btn => {
        btn.addEventListener('click', toggleFavorite);
    });

    // Initialize college details modal
    const collegeLinks = document.querySelectorAll('.college-details-link');
    collegeLinks.forEach(link => {
        link.addEventListener('click', showCollegeDetails);
    });

    // Search form handling
    const searchForm = document.querySelector('#searchForm');
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }
});

// College comparison handling
function handleCompareChange(e) {
    const selectedColleges = document.querySelectorAll('.compare-checkbox:checked');
    const compareButton = document.getElementById('compareButton');
    
    if (selectedColleges.length > 1) {
        compareButton.disabled = false;
    } else {
        compareButton.disabled = true;
    }
}

// Export to Excel functionality
function exportToExcel() {
    const table = document.querySelector('.custom-table');
    const wb = XLSX.utils.table_to_book(table, {sheet: "Colleges"});
    XLSX.writeFile(wb, 'college_results.xlsx');
}

// Toggle favorite colleges
function toggleFavorite(e) {
    const collegeId = e.target.dataset.collegeId;
    let favorites = JSON.parse(localStorage.getItem('favorites') || '[]');
    
    if (favorites.includes(collegeId)) {
        favorites = favorites.filter(id => id !== collegeId);
        e.target.classList.remove('favorite-active');
    } else {
        favorites.push(collegeId);
        e.target.classList.add('favorite-active');
    }
    
    localStorage.setItem('favorites', JSON.stringify(favorites));
}

// Show college details modal
function showCollegeDetails(e) {
    e.preventDefault();
    const collegeId = e.target.dataset.collegeId;
    
    // Fetch college details
    fetch(`/api/college/${collegeId}`)
        .then(response => response.json())
        .then(data => {
            const modal = document.getElementById('collegeModal');
            const modalContent = modal.querySelector('.modal-content');
            
            // Update modal content
            modalContent.innerHTML = `
                <h2>${data.name}</h2>
                <div class="college-details">
                    <p><strong>Location:</strong> ${data.location}</p>
                    <p><strong>NIRF Rank:</strong> ${data.nirfRank}</p>
                    <p><strong>Placement Rate:</strong> ${data.placementRate}%</p>
                    <p><strong>Average Package:</strong> ${data.avgPackage} LPA</p>
                </div>
                <button onclick="closeModal()" class="btn-primary">Close</button>
            `;
            
            modal.style.display = 'block';
        });
}

// Close modal
function closeModal() {
    const modal = document.getElementById('collegeModal');
    modal.style.display = 'none';
}

// Handle search form submission
async function handleSearch(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);
    
    // Show loading state
    document.getElementById('searchResults').innerHTML = '<div class="loader"></div>';
    
    try {
        const response = await fetch('/search', {
            method: 'POST',
            body: formData
        });
        
        const html = await response.text();
        document.getElementById('searchResults').innerHTML = html;
        
        // Initialize new interactive elements
        initializeNewElements();
    } catch (error) {
        console.error('Search failed:', error);
        document.getElementById('searchResults').innerHTML = '<p class="error">Search failed. Please try again.</p>';
    }
}

// Initialize new elements after search
function initializeNewElements() {
    // Re-initialize tooltips
    const tooltips = document.querySelectorAll('[data-tooltip]');
    tooltips.forEach(tooltip => {
        new Tooltip(tooltip);
    });
    
    // Re-initialize compare checkboxes
    const compareCheckboxes = document.querySelectorAll('.compare-checkbox');
    compareCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', handleCompareChange);
    });
}

// Tooltip class
class Tooltip {
    constructor(element) {
        this.element = element;
        this.text = element.getAttribute('data-tooltip');
        this.init();
    }
    
    init() {
        const tooltip = document.createElement('span');
        tooltip.className = 'tooltip-text';
        tooltip.textContent = this.text;
        this.element.appendChild(tooltip);
    }
}
