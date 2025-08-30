// Syrian Archive - Main JavaScript

// ===== GLOBAL VARIABLES =====
const SyrianArchive = {
    init: function() {
        this.initializeComponents();
        this.bindEvents();
        this.setupFormValidations();
        this.initializeTooltips();
        this.setupImagePreview();
        this.initializeConfirmations();
    },

    // ===== COMPONENT INITIALIZATION =====
    initializeComponents: function() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });

        // Initialize Bootstrap popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });

        // Auto-hide alerts after 5 seconds
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            });
        }, 5000);
    },

    // ===== EVENT BINDING =====
    bindEvents: function() {
        // Smooth scrolling for anchor links
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });

        // Loading states for buttons
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', function() {
                const submitBtn = this.querySelector('button[type="submit"]');
                if (submitBtn) {
                    submitBtn.disabled = true;
                    const originalText = submitBtn.innerHTML;
                    submitBtn.innerHTML = '<span class="loading-spinner"></span> Processing...';
                    
                    // Re-enable after 10 seconds as fallback
                    setTimeout(() => {
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = originalText;
                    }, 10000);
                }
            });
        });

        // Search functionality enhancement
        const searchInputs = document.querySelectorAll('input[type="search"], .search-input');
        searchInputs.forEach(input => {
            let searchTimeout;
            input.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => {
                    this.closest('form')?.submit();
                }, 500);
            });
        });

        // Dynamic table row highlighting
        document.querySelectorAll('.table tbody tr').forEach(row => {
            row.addEventListener('mouseenter', function() {
                this.style.backgroundColor = '#f8f9fa';
            });
            row.addEventListener('mouseleave', function() {
                this.style.backgroundColor = '';
            });
        });
    },

    // ===== FORM VALIDATIONS =====
    setupFormValidations: function() {
        // Real-time validation for forms
        document.querySelectorAll('.needs-validation').forEach(form => {
            form.addEventListener('submit', function(event) {
                if (!form.checkValidity()) {
                    event.preventDefault();
                    event.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // Password strength indicator
        const passwordInputs = document.querySelectorAll('input[type="password"]');
        passwordInputs.forEach(input => {
            if (input.name.includes('password1') || input.name.includes('new_password')) {
                this.addPasswordStrengthIndicator(input);
            }
        });

        // File upload validation
        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', function() {
                this.validateFileUpload();
            });
        });
    },

    // ===== PASSWORD STRENGTH =====
    addPasswordStrengthIndicator: function(input) {
        const strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'password-strength mt-2';
        strengthIndicator.innerHTML = `
            <div class="progress" style="height: 5px;">
                <div class="progress-bar" role="progressbar" style="width: 0%"></div>
            </div>
            <small class="text-muted">Password strength: <span class="strength-text">Weak</span></small>
        `;
        input.parentNode.appendChild(strengthIndicator);

        input.addEventListener('input', function() {
            const password = this.value;
            const strength = SyrianArchive.calculatePasswordStrength(password);
            const progressBar = strengthIndicator.querySelector('.progress-bar');
            const strengthText = strengthIndicator.querySelector('.strength-text');

            progressBar.style.width = strength.percentage + '%';
            progressBar.className = `progress-bar ${strength.class}`;
            strengthText.textContent = strength.text;
        });
    },

    calculatePasswordStrength: function(password) {
        let score = 0;
        if (password.length >= 8) score += 25;
        if (password.match(/[a-z]/)) score += 25;
        if (password.match(/[A-Z]/)) score += 25;
        if (password.match(/[0-9]/)) score += 25;
        if (password.match(/[^a-zA-Z0-9]/)) score += 25;

        if (score <= 25) return { percentage: 25, class: 'bg-danger', text: 'Weak' };
        if (score <= 50) return { percentage: 50, class: 'bg-warning', text: 'Fair' };
        if (score <= 75) return { percentage: 75, class: 'bg-info', text: 'Good' };
        return { percentage: 100, class: 'bg-success', text: 'Strong' };
    },

    // ===== TOOLTIPS =====
    initializeTooltips: function() {
        // Add tooltips to truncated text
        document.querySelectorAll('.text-truncate').forEach(element => {
            if (element.scrollWidth > element.clientWidth) {
                element.setAttribute('data-bs-toggle', 'tooltip');
                element.setAttribute('title', element.textContent);
                new bootstrap.Tooltip(element);
            }
        });
    },

    // ===== IMAGE PREVIEW =====
    setupImagePreview: function() {
        document.querySelectorAll('input[type="file"][accept*="image"]').forEach(input => {
            input.addEventListener('change', function() {
                const file = this.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        let preview = input.parentNode.querySelector('.image-preview');
                        if (!preview) {
                            preview = document.createElement('div');
                            preview.className = 'image-preview mt-3';
                            input.parentNode.appendChild(preview);
                        }
                        preview.innerHTML = `
                            <img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">
                            <p class="small text-muted mt-2">${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)</p>
                        `;
                    };
                    reader.readAsDataURL(file);
                }
            });
        });
    },

    // ===== CONFIRMATIONS =====
    initializeConfirmations: function() {
        // Confirmation dialogs for dangerous actions
        document.querySelectorAll('[data-confirm]').forEach(element => {
            element.addEventListener('click', function(e) {
                const message = this.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                    return false;
                }
            });
        });

        // Delete confirmations
        document.querySelectorAll('.btn-danger, .delete-btn').forEach(button => {
            if (button.textContent.toLowerCase().includes('delete') || 
                button.textContent.toLowerCase().includes('remove')) {
                button.addEventListener('click', function(e) {
                    if (!this.hasAttribute('data-confirm')) {
                        const itemType = this.getAttribute('data-item-type') || 'item';
                        const confirmMessage = `Are you sure you want to delete this ${itemType}? This action cannot be undone.`;
                        if (!confirm(confirmMessage)) {
                            e.preventDefault();
                            return false;
                        }
                    }
                });
            }
        });
    },

    // ===== UTILITY FUNCTIONS =====
    showNotification: function(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(alertDiv);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alertDiv.parentNode) {
                alertDiv.remove();
            }
        }, 5000);
    },

    copyToClipboard: function(text) {
        navigator.clipboard.writeText(text).then(() => {
            this.showNotification('Copied to clipboard!', 'success');
        }).catch(() => {
            this.showNotification('Failed to copy to clipboard', 'danger');
        });
    },

    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }
};

// ===== FILE UPLOAD VALIDATION =====
HTMLInputElement.prototype.validateFileUpload = function() {
    const file = this.files[0];
    if (!file) return;

    const maxSize = this.getAttribute('data-max-size') || 10 * 1024 * 1024; // 10MB default
    const allowedTypes = this.getAttribute('accept')?.split(',').map(type => type.trim()) || [];

    // Size validation
    if (file.size > maxSize) {
        SyrianArchive.showNotification(
            `File size (${SyrianArchive.formatFileSize(file.size)}) exceeds maximum allowed size (${SyrianArchive.formatFileSize(maxSize)})`,
            'danger'
        );
        this.value = '';
        return false;
    }

    // Type validation
    if (allowedTypes.length > 0) {
        const fileType = file.type;
        const fileExtension = '.' + file.name.split('.').pop().toLowerCase();
        const isValidType = allowedTypes.some(type => 
            type === fileType || type === fileExtension
        );

        if (!isValidType) {
            SyrianArchive.showNotification(
                `File type not allowed. Allowed types: ${allowedTypes.join(', ')}`,
                'danger'
            );
            this.value = '';
            return false;
        }
    }

    return true;
};

// ===== ADMIN DASHBOARD ENHANCEMENTS =====
const AdminDashboard = {
    init: function() {
        this.setupStatCards();
        this.setupQuickActions();
        this.setupDataTables();
    },

    setupStatCards: function() {
        document.querySelectorAll('.stats-card').forEach(card => {
            card.addEventListener('click', function() {
                const link = this.getAttribute('data-link');
                if (link) {
                    window.location.href = link;
                }
            });
        });
    },

    setupQuickActions: function() {
        // Bulk actions for admin tables
        const selectAllCheckbox = document.querySelector('#select-all');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', function() {
                const checkboxes = document.querySelectorAll('.item-checkbox');
                checkboxes.forEach(checkbox => {
                    checkbox.checked = this.checked;
                });
                AdminDashboard.updateBulkActions();
            });
        }

        document.querySelectorAll('.item-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                AdminDashboard.updateBulkActions();
            });
        });
    },

    updateBulkActions: function() {
        const checkedBoxes = document.querySelectorAll('.item-checkbox:checked');
        const bulkActions = document.querySelector('.bulk-actions');
        if (bulkActions) {
            bulkActions.style.display = checkedBoxes.length > 0 ? 'block' : 'none';
        }
    },

    setupDataTables: function() {
        // Enhanced table sorting
        document.querySelectorAll('.sortable th').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const table = this.closest('table');
                const columnIndex = Array.from(this.parentNode.children).indexOf(this);
                AdminDashboard.sortTable(table, columnIndex);
            });
        });
    },

    sortTable: function(table, columnIndex) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        const isAscending = table.getAttribute('data-sort-direction') !== 'asc';

        rows.sort((a, b) => {
            const aText = a.cells[columnIndex].textContent.trim();
            const bText = b.cells[columnIndex].textContent.trim();
            
            if (isAscending) {
                return aText.localeCompare(bText, undefined, { numeric: true });
            } else {
                return bText.localeCompare(aText, undefined, { numeric: true });
            }
        });

        rows.forEach(row => tbody.appendChild(row));
        table.setAttribute('data-sort-direction', isAscending ? 'asc' : 'desc');
    }
};

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    SyrianArchive.init();
    
    // Initialize admin dashboard if on admin page
    if (document.body.classList.contains('admin-page') || 
        window.location.pathname.includes('/admin-panel/')) {
        AdminDashboard.init();
    }
});

// ===== GLOBAL ERROR HANDLING =====
window.addEventListener('error', function(e) {
    console.error('JavaScript Error:', e.error);
});

// ===== EXPORT FOR GLOBAL ACCESS =====
window.SyrianArchive = SyrianArchive;
window.AdminDashboard = AdminDashboard;