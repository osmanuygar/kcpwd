// kcpwd UI - Complete JavaScript Application
// Version 0.6.1 - FIXED: Proper API response handling

// ==================== Global State ====================
let authToken = null;
let allPasswords = [];
let currentViewKey = null;
let currentDeleteKey = null;

// ==================== Authentication ====================

async function authenticate() {
    const secret = document.getElementById('secret-input').value;

    if (!secret) {
        showToast('Please enter UI secret', 'error');
        return;
    }

    showLoading('Authenticating...');

    try {
        const response = await fetch('/api/auth', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({secret})
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Authentication failed');
        }

        authToken = data.token;
        localStorage.setItem('kcpwd_token', authToken);

        // Hide auth, show main
        document.getElementById('auth-form').classList.add('hidden');
        document.getElementById('main-content').classList.remove('hidden');
        document.getElementById('session-info').classList.remove('hidden');

        showToast('✓ Logged in successfully', 'success');

        // Load initial data
        await Promise.all([
            loadInfo(),
            loadPasswords(),
            loadStats()
        ]);

    } catch (error) {
        showToast('Authentication failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function logout() {
    if (!confirm('Are you sure you want to logout?')) {
        return;
    }

    try {
        if (authToken) {
            await fetch('/api/logout', {
                method: 'POST',
                headers: {'Authorization': `Bearer ${authToken}`}
            });
        }
    } catch (error) {
        console.error('Logout error:', error);
    }

    authToken = null;
    localStorage.removeItem('kcpwd_token');

    document.getElementById('auth-form').classList.remove('hidden');
    document.getElementById('main-content').classList.add('hidden');
    document.getElementById('session-info').classList.add('hidden');

    showToast('Logged out', 'info');
}

// Try to restore session on load
window.addEventListener('DOMContentLoaded', () => {
    const savedToken = localStorage.getItem('kcpwd_token');
    if (savedToken) {
        authToken = savedToken;
        // Try to use it
        loadInfo().then(() => {
            document.getElementById('auth-form').classList.add('hidden');
            document.getElementById('main-content').classList.remove('hidden');
            document.getElementById('session-info').classList.remove('hidden');
            loadPasswords();
            loadStats();
        }).catch(() => {
            // Token expired
            localStorage.removeItem('kcpwd_token');
            authToken = null;
        });
    }
});

// ==================== API Calls ====================

async function apiCall(endpoint, options = {}) {
    if (!authToken) {
        throw new Error('Not authenticated');
    }

    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        }
    };

    const response = await fetch(endpoint, {...defaultOptions, ...options});

    if (response.status === 401) {
        // Token expired
        logout();
        throw new Error('Session expired');
    }

    // FIXED: Handle both success and error responses properly
    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
        data = await response.json();
    } else {
        // Non-JSON response
        const text = await response.text();
        data = {detail: text || 'Unknown error'};
    }

    if (!response.ok) {
        // FIXED: Don't throw here, let calling function handle success:true/false
        throw new Error(data.detail || data.message || data.error || 'Request failed');
    }

    return data;
}

// ==================== Load Data ====================

async function loadInfo() {
    try {
        const data = await apiCall('/api/info');

        const info = `Platform: ${data.platform.name} | Backend: ${data.backend.description}`;
        document.getElementById('backend-info').textContent = info;

        document.getElementById('session-status').textContent =
            `✓ Session Active (${data.session.active_sessions} sessions)`;

        // Store platform details for tools tab
        window.platformInfo = data;
        updatePlatformDetails();

    } catch (error) {
        console.error('Load info error:', error);
    }
}

async function loadPasswords() {
    try {
        const data = await apiCall('/api/passwords');

        allPasswords = [
            ...data.regular.map(key => ({key, type: 'regular'})),
            ...data.master_protected.map(key => ({key, type: 'master'}))
        ];

        displayPasswords(allPasswords);

    } catch (error) {
        console.error('Load passwords error:', error);
        showToast('Failed to load passwords', 'error');
    }
}

async function loadStats() {
    try {
        const data = await apiCall('/api/stats');

        document.getElementById('stats-info').textContent =
            `Total: ${data.total} passwords (${data.regular} regular, ${data.master_protected} master-protected)`;

        // Update stats in tools tab
        updateStatsDetails(data);

    } catch (error) {
        console.error('Load stats error:', error);
    }
}

// ==================== Display Functions ====================

function displayPasswords(passwords) {
    const listEl = document.getElementById('password-list');

    if (passwords.length === 0) {
        listEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔐</div>
                <h3>No passwords found</h3>
                <p>Add your first password to get started</p>
            </div>
        `;
        return;
    }

    listEl.innerHTML = passwords.map(pwd => `
        <div class="password-item ${pwd.type === 'master' ? 'master' : ''}">
            <div class="password-item-info">
                <strong>${escapeHtml(pwd.key)}</strong>
                ${pwd.type === 'master' ? '<span class="password-item-badge">🔒 Master</span>' : ''}
            </div>
            <div class="password-item-actions">
                <button class="btn-primary btn-small btn-icon" onclick="viewPassword('${escapeHtml(pwd.key)}', ${pwd.type === 'master'})">
                    👁️ View
                </button>
                <button class="btn-danger btn-small btn-icon" onclick="showDeleteModal('${escapeHtml(pwd.key)}')">
                    🗑️ Delete
                </button>
            </div>
        </div>
    `).join('');
}

function filterPasswords() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();

    if (!searchTerm) {
        displayPasswords(allPasswords);
        return;
    }

    const filtered = allPasswords.filter(pwd =>
        pwd.key.toLowerCase().includes(searchTerm)
    );

    displayPasswords(filtered);
}

// ==================== Add Password ====================

function toggleMasterPassword(prefix) {
    const checkbox = document.getElementById(`${prefix}-master`);
    const input = document.getElementById(`${prefix}-master-pass`);

    if (checkbox.checked) {
        input.classList.remove('hidden');
    } else {
        input.classList.add('hidden');
        input.value = '';
    }
}

async function checkAddPasswordStrength() {
    const password = document.getElementById('add-password').value;

    if (!password) {
        document.getElementById('add-strength-indicator').classList.add('hidden');
        return;
    }

    try {
        const data = await apiCall(`/api/check-strength?password=${encodeURIComponent(password)}`);

        document.getElementById('add-strength-indicator').classList.remove('hidden');

        const fillEl = document.getElementById('add-strength-fill');
        const strengthClass = data.strength.toLowerCase().replace(' ', '-');
        fillEl.className = `strength-fill ${strengthClass}`;

        document.getElementById('add-strength-score').textContent = `${data.score}/100`;

        const levelEl = document.getElementById('add-strength-level');
        levelEl.textContent = data.strength;
        levelEl.className = `level ${strengthClass}`;

    } catch (error) {
        console.error('Strength check error:', error);
    }
}

async function addPassword() {
    const key = document.getElementById('add-key').value.trim();
    const password = document.getElementById('add-password').value;
    const useMaster = document.getElementById('add-master').checked;
    const masterPassword = useMaster ? document.getElementById('add-master-pass').value : null;

    if (!key) {
        showToast('Please enter a key', 'error');
        return;
    }

    if (!password) {
        showToast('Please enter a password', 'error');
        return;
    }

    if (useMaster && !masterPassword) {
        showToast('Please enter master password', 'error');
        return;
    }

    if (useMaster && masterPassword.length < 8) {
        showToast('Master password must be at least 8 characters', 'error');
        return;
    }

    showLoading('Saving password...');

    try {
        // FIXED: Properly handle API response
        const data = await apiCall('/api/passwords', {
            method: 'POST',
            body: JSON.stringify({
                key,
                password,
                use_master: useMaster,
                master_password: masterPassword
            })
        });

        // FIXED: Check success field if present, or assume success if no error thrown
        if (data.success !== false) {
            showToast(`✓ Password '${key}' saved successfully`, 'success');

            clearAddForm();
            await loadPasswords();
            await loadStats();

            switchTab('list');
        } else {
            throw new Error(data.message || 'Failed to save password');
        }

    } catch (error) {
        showToast('Failed to save password: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function clearAddForm() {
    document.getElementById('add-key').value = '';
    document.getElementById('add-password').value = '';
    document.getElementById('add-master').checked = false;
    document.getElementById('add-master-pass').value = '';
    document.getElementById('add-master-pass').classList.add('hidden');
    document.getElementById('add-strength-indicator').classList.add('hidden');
}

// ==================== View Password ====================

function viewPassword(key, isMaster) {
    currentViewKey = key;

    document.getElementById('view-key').textContent = key;
    document.getElementById('view-master-badge').classList.toggle('hidden', !isMaster);
    document.getElementById('view-master-input').classList.toggle('hidden', !isMaster);
    document.getElementById('view-password-container').classList.add('hidden');
    document.getElementById('view-retrieve-btn').classList.remove('hidden');
    document.getElementById('view-copy-btn').classList.add('hidden');
    document.getElementById('view-password').type = 'password';

    document.getElementById('view-modal').classList.remove('hidden');
}

async function retrievePassword() {
    const key = currentViewKey;
    const isMaster = !document.getElementById('view-master-badge').classList.contains('hidden');
    const masterPassword = isMaster ? document.getElementById('view-master-input').value : null;

    if (isMaster && !masterPassword) {
        showToast('Please enter master password', 'error');
        return;
    }

    showLoading('Retrieving password...');

    try {
        const data = await apiCall('/api/passwords/retrieve', {
            method: 'POST',
            body: JSON.stringify({
                key,
                use_master: isMaster,
                master_password: masterPassword
            })
        });

        document.getElementById('view-password').value = data.password;
        document.getElementById('view-password-container').classList.remove('hidden');
        document.getElementById('view-retrieve-btn').classList.add('hidden');
        document.getElementById('view-copy-btn').classList.remove('hidden');

    } catch (error) {
        showToast('Failed to retrieve: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function copyViewPassword() {
    const password = document.getElementById('view-password').value;
    copyToClipboard(password);
    showToast('✓ Password copied to clipboard', 'success');
}

function closeViewModal(event) {
    if (event && event.target !== event.currentTarget) {
        return;
    }

    document.getElementById('view-modal').classList.add('hidden');
    document.getElementById('view-master-input').value = '';
    document.getElementById('view-password').value = '';
    currentViewKey = null;
}

// ==================== Delete Password ====================

function showDeleteModal(key) {
    currentDeleteKey = key;
    document.getElementById('delete-key').textContent = key;
    document.getElementById('delete-modal').classList.remove('hidden');
}

async function confirmDelete() {
    const key = currentDeleteKey;

    showLoading('Deleting password...');

    try {
        await apiCall(`/api/passwords/${encodeURIComponent(key)}`, {
            method: 'DELETE'
        });

        showToast(`✓ Password '${key}' deleted`, 'success');

        closeDeleteModal();
        await loadPasswords();
        await loadStats();

    } catch (error) {
        showToast('Failed to delete: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function closeDeleteModal(event) {
    if (event && event.target !== event.currentTarget) {
        return;
    }

    document.getElementById('delete-modal').classList.add('hidden');
    currentDeleteKey = null;
}

// ==================== Generate Password ====================

function syncLengthSlider() {
    const slider = document.getElementById('gen-length-slider');
    const input = document.getElementById('gen-length');
    input.value = slider.value;
}

function updateLengthDisplay() {
    const input = document.getElementById('gen-length');
    const slider = document.getElementById('gen-length-slider');

    if (input.value <= 64) {
        slider.value = input.value;
    }
}

async function generatePassword() {
    const data = {
        length: parseInt(document.getElementById('gen-length').value),
        use_uppercase: document.getElementById('gen-upper').checked,
        use_lowercase: document.getElementById('gen-lower').checked,
        use_digits: document.getElementById('gen-digits').checked,
        use_symbols: document.getElementById('gen-symbols').checked,
        exclude_ambiguous: document.getElementById('gen-ambiguous').checked
    };

    // Validate at least one type
    if (!data.use_uppercase && !data.use_lowercase && !data.use_digits && !data.use_symbols) {
        showToast('Please select at least one character type', 'error');
        return;
    }

    showLoading('Generating password...');

    try {
        const result = await apiCall('/api/generate', {
            method: 'POST',
            body: JSON.stringify(data)
        });

        document.getElementById('generated-password').value = result.password;
        document.getElementById('generated-password').type = 'password';
        document.getElementById('generated-result').classList.remove('hidden');

        // Display strength
        const strengthClass = result.strength.level.toLowerCase().replace(' ', '-');
        const fillEl = document.getElementById('gen-strength-fill');
        fillEl.className = `strength-fill ${strengthClass}`;

        document.getElementById('gen-strength-score').textContent = `${result.strength.score}/100`;

        const levelEl = document.getElementById('gen-strength-level');
        levelEl.textContent = result.strength.level;
        levelEl.className = `level ${strengthClass}`;

        // Display feedback if any
        if (result.strength.feedback && result.strength.feedback.length > 0) {
            document.getElementById('gen-feedback').classList.remove('hidden');
            document.getElementById('gen-feedback-list').innerHTML =
                result.strength.feedback.map(fb => `<li>${escapeHtml(fb)}</li>`).join('');
        } else {
            document.getElementById('gen-feedback').classList.add('hidden');
        }

    } catch (error) {
        showToast('Failed to generate: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function copyGeneratedPassword() {
    const password = document.getElementById('generated-password').value;
    copyToClipboard(password);
    showToast('✓ Password copied to clipboard', 'success');
}

function showSaveGeneratedModal() {
    document.getElementById('save-modal').classList.remove('hidden');
}

function closeSaveModal(event) {
    if (event && event.target !== event.currentTarget) {
        return;
    }

    document.getElementById('save-modal').classList.add('hidden');
    document.getElementById('save-key').value = '';
    document.getElementById('save-master').checked = false;
    document.getElementById('save-master-pass').value = '';
    document.getElementById('save-master-pass').classList.add('hidden');
}

async function saveGeneratedPassword() {
    const key = document.getElementById('save-key').value.trim();
    const password = document.getElementById('generated-password').value;
    const useMaster = document.getElementById('save-master').checked;
    const masterPassword = useMaster ? document.getElementById('save-master-pass').value : null;

    if (!key) {
        showToast('Please enter a key', 'error');
        return;
    }

    if (useMaster && !masterPassword) {
        showToast('Please enter master password', 'error');
        return;
    }

    showLoading('Saving password...');

    try {
        await apiCall('/api/passwords', {
            method: 'POST',
            body: JSON.stringify({
                key,
                password,
                use_master: useMaster,
                master_password: masterPassword
            })
        });

        showToast(`✓ Password saved as '${key}'`, 'success');

        closeSaveModal();
        await loadPasswords();
        await loadStats();

    } catch (error) {
        showToast('Failed to save: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

// ==================== Tools ====================

async function exportPasswords() {
    const includePasswords = document.getElementById('export-passwords').checked;

    if (includePasswords) {
        if (!confirm('⚠️ This will export passwords in PLAIN TEXT. Continue?')) {
            return;
        }
    }

    showLoading('Exporting...');

    try {
        const data = await apiCall(`/api/export?include_passwords=${includePasswords}`);

        // Create download
        const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `kcpwd-backup-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);

        showToast('✓ Passwords exported successfully', 'success');

    } catch (error) {
        showToast('Export failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

async function importPasswords() {
    const fileInput = document.getElementById('import-file');
    const file = fileInput.files[0];

    if (!file) {
        showToast('Please select a file', 'error');
        return;
    }

    const overwrite = document.getElementById('import-overwrite').checked;

    showLoading('Importing...');

    try {
        const text = await file.text();
        const data = JSON.parse(text);

        const result = await apiCall('/api/import', {
            method: 'POST',
            body: JSON.stringify({
                data: data,
                overwrite: overwrite
            })
        });

        showToast(`✓ Imported ${result.imported_count} passwords`, 'success');

        if (result.skipped_keys && result.skipped_keys.length > 0) {
            showToast(`Skipped ${result.skipped_keys.length} existing passwords`, 'warning');
        }

        await loadPasswords();
        await loadStats();

        // Clear file input
        fileInput.value = '';

    } catch (error) {
        showToast('Import failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function updateStatsDetails(data) {
    const html = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
            <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #3b82f6;">${data.total}</div>
                <div style="color: #666; margin-top: 5px;">Total Passwords</div>
            </div>
            <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #10b981;">${data.regular}</div>
                <div style="color: #666; margin-top: 5px;">Regular</div>
            </div>
            <div style="background: #fffbeb; padding: 20px; border-radius: 8px; text-align: center;">
                <div style="font-size: 2rem; font-weight: bold; color: #f59e0b;">${data.master_protected}</div>
                <div style="color: #666; margin-top: 5px;">Master Protected</div>
            </div>
        </div>
        <div style="margin-top: 20px; padding: 15px; background: #f9fafb; border-radius: 8px;">
            <p><strong>Backend:</strong> ${data.backend}</p>
        </div>
    `;

    document.getElementById('stats-details').innerHTML = html;
}

function updatePlatformDetails() {
    if (!window.platformInfo) return;

    const info = window.platformInfo;
    const html = `
        <div style="display: grid; gap: 15px;">
            <div>
                <strong>Platform:</strong> ${info.platform.name}
                ${info.platform.supported ? '<span style="color: #10b981;">✓ Supported</span>' : '<span style="color: #ef4444;">✗ Not Supported</span>'}
            </div>
            <div>
                <strong>Backend Type:</strong> ${info.backend.type}
            </div>
            <div>
                <strong>Backend Name:</strong> ${info.backend.name || 'Unknown'}
            </div>
            <div>
                <strong>Description:</strong> ${info.backend.description}
            </div>
            <div>
                <strong>Clipboard:</strong>
                ${info.platform.clipboard ? '<span style="color: #10b981;">✓ Available</span>' : '<span style="color: #f59e0b;">⚠️ Not Available</span>'}
                ${info.platform.clipboard_tool ? `<br><small>Tool: ${info.platform.clipboard_tool}</small>` : ''}
            </div>
        </div>
    `;

    document.getElementById('platform-details').innerHTML = html;
}

// ==================== Utility Functions ====================

function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`${tabName}-tab`).classList.remove('hidden');

    // Load data if needed
    if (tabName === 'list') {
        loadPasswords();
    } else if (tabName === 'tools') {
        loadStats();
    }
}

async function refreshAll() {
    showLoading('Refreshing...');

    try {
        await Promise.all([
            loadInfo(),
            loadPasswords(),
            loadStats()
        ]);

        showToast('✓ Refreshed successfully', 'success');
    } catch (error) {
        showToast('Refresh failed: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);

    if (input.type === 'password') {
        input.type = 'text';
    } else {
        input.type = 'password';
    }
}

function copyToClipboard(text) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text);
    } else {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showLoading(message = 'Loading...') {
    document.getElementById('loading-overlay').classList.remove('hidden');
    document.querySelector('.loading-text').textContent = message;
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.add('hidden');
}

// ==================== Toast Notifications ====================

let toastTimeout = null;

function showToast(message, type = 'success') {
    // Clear existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }

    if (toastTimeout) {
        clearTimeout(toastTimeout);
    }

    // Create toast
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icon = {
        'success': '✓',
        'error': '✗',
        'warning': '⚠️',
        'info': 'ℹ️'
    }[type] || 'ℹ️';

    toast.innerHTML = `
        <span class="toast-icon">${icon}</span>
        <div class="toast-content">${escapeHtml(message)}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    document.body.appendChild(toast);

    // Auto remove after 5 seconds
    toastTimeout = setTimeout(() => {
        toast.remove();
    }, 5000);
}

// ==================== Keyboard Shortcuts ====================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        const searchInput = document.getElementById('search-input');
        if (searchInput && !searchInput.closest('.hidden')) {
            searchInput.focus();
        }
    }

    // Escape: Close modals
    if (e.key === 'Escape') {
        closeViewModal();
        closeSaveModal();
        closeDeleteModal();
    }
});

// ==================== Auto-refresh ====================

let autoRefreshInterval = null;

function startAutoRefresh() {
    if (autoRefreshInterval) return;

    autoRefreshInterval = setInterval(async () => {
        try {
            await loadPasswords();
        } catch (error) {
            console.error('Auto-refresh error:', error);
        }
    }, 30000); // 30 seconds
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

// Start auto-refresh when authenticated
window.addEventListener('DOMContentLoaded', () => {
    const observer = new MutationObserver(() => {
        const mainContent = document.getElementById('main-content');
        if (!mainContent.classList.contains('hidden')) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });

    observer.observe(document.getElementById('main-content'), {
        attributes: true,
        attributeFilter: ['class']
    });
});

// ==================== Error Handler ====================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showToast('An unexpected error occurred', 'error');
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred', 'error');
});

// ==================== Development Helpers ====================

if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    console.log('%c🔐 kcpwd Web UI - Development Mode', 'color: #667eea; font-size: 14px; font-weight: bold;');
    console.log('%cVersion: 0.6.3', 'color: #666;');

    // Expose API for debugging
    window.kcpwdAPI = {
        authToken: () => authToken,
        passwords: () => allPasswords,
        platformInfo: () => window.platformInfo,
        apiCall: apiCall,
        version: '0.6.2'
    };

    console.log('%cDebug API available at window.kcpwdAPI', 'color: #10b981;');
}

console.log('✓ kcpwd UI loaded successfully');