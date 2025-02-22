// Alpine.js Component for College Search
function collegeSearchForm() {
    return {
        formData: {
            rank: null,
            category: 'All',
            quota: 'All',
            branch: 'All'
        },
        isLoading: false,
        searchResults: [],
        error: null,

        async searchColleges() {
            this.isLoading = true;
            this.error = null;

            try {
                const response = await fetch('/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams(this.formData)
                });

                if (!response.ok) {
                    throw new Error('Search failed');
                }

                const html = await response.text();
                // Update page content with new results
                document.getElementById('search-results-container').innerHTML = html;
            } catch (error) {
                this.error = error.message;
                console.error('Search error:', error);
            } finally {
                this.isLoading = false;
            }
        },

        async exportResults() {
            try {
                const response = await fetch('/export', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/x-www-form-urlencoded',
                    },
                    body: new URLSearchParams(this.formData)
                });

                if (!response.ok) {
                    throw new Error('Export failed');
                }

                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = 'college_results.csv';
                document.body.appendChild(a);
                a.click();
                a.remove();
            } catch (error) {
                console.error('Export error:', error);
            }
        },

        showCollegeDetails(collegeId) {
            // Implement modal logic to show college details
            const modal = document.querySelector('[x-data="{ isOpen: false, modalContent: \'\' }"]');
            
            // Fetch college details
            fetch(`/api/college/${collegeId}`)
                .then(response => response.json())
                .then(data => {
                    // Populate modal content
                    modal.querySelector('[x-html="modalContent"]').innerHTML = `
                        <h2 class="text-xl font-bold mb-4">${data.name}</h2>
                        <div class="space-y-2">
                            <p><strong>Location:</strong> ${data.location}</p>
                            <p><strong>Branch:</strong> ${data.branch}</p>
                            <p><strong>Cutoff Rank:</strong> ${data.cutoffRank}</p>
                        </div>
                    `;
                    
                    // Open modal
                    Alpine.store('modal').open();
                });
        }
    };
}

// Global Alpine Store for Modal
document.addEventListener('alpine:init', () => {
    Alpine.store('modal', {
        isOpen: false,
        open() {
            this.isOpen = true;
        },
        close() {
            this.isOpen = false;
        }
    });
});

// Theme Toggle
function initThemeToggle() {
    const themeToggle = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;

    themeToggle.addEventListener('click', () => {
        htmlElement.classList.toggle('dark');
        localStorage.setItem('theme', htmlElement.classList.contains('dark') ? 'dark' : 'light');
    });

    // Check saved theme preference
    if (localStorage.getItem('theme') === 'dark') {
        htmlElement.classList.add('dark');
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', () => {
    initThemeToggle();
});
