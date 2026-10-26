// services/edit.js - Service Edit Page
const pathParts = window.location.pathname.split('/');
const mcpServiceId = Number.parseInt(pathParts[2], 10); // /mcp-services/{id}/apps/{app_id}/edit
const serviceId = Number.parseInt(pathParts[4], 10);
let headerIndex = 0;
let currentAccessControl = 'public'; // デフォルトはpublic（制限なし）
let currentServiceType = 'api'; // Current service type (readonly after creation)

// Update access control UI
function updateAccessControlUI(isRestricted) {
    const permissionsSection = document.getElementById('permissions-section');
    
    if (isRestricted) {
        permissionsSection.style.display = 'block';
    } else {
        permissionsSection.style.display = 'none';
    }
}

function showServiceTypeSection() {
    const serviceType = document.querySelector('input[name="service_type"]:checked').value;
    const mcpUrlSection = document.getElementById('mcp-url-section');
    const mcpUrlInput = document.getElementById('mcp_url');
    const mcpUrlLabel = document.querySelector('#mcp-url-label span:first-child');
    const mcpUrlRequired = document.getElementById('mcp-url-required');
    const mcpUrlHint = document.getElementById('mcp-url-hint');
    const testConnectionBtn = document.getElementById('test-connection-btn');
    
    if (serviceType === 'mcp') {
        mcpUrlSection.style.display = 'block';
        mcpUrlInput.setAttribute('required', 'required');
        mcpUrlLabel.textContent = 'MCP接続URL';
        mcpUrlRequired.textContent = '*';
        mcpUrlHint.textContent = 'MCPサーバーのSSEエンドポイントURLを入力してください';
        mcpUrlInput.placeholder = 'http://localhost:3000/sse';
        testConnectionBtn.style.display = 'block';
    } else {
        // API type
        mcpUrlSection.style.display = 'block';
        mcpUrlInput.removeAttribute('required');
        mcpUrlLabel.textContent = 'API ベースURL';
        mcpUrlRequired.textContent = '';
        mcpUrlHint.textContent = 'APIの共通ベースURL（任意）例: https://api.example.com/v1/';
        mcpUrlInput.placeholder = 'https://api.example.com/v1/';
        testConnectionBtn.style.display = 'none';
    }
}

function addHeaderRow(key = '', value = '') {
    const container = document.getElementById('headers-container');
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    row.innerHTML = `
        <input type="text" placeholder="${t('form_key_placeholder')}" value="${key}" 
               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <input type="text" placeholder="${t('form_value_placeholder')}" value="${value}" 
               style="flex: 2; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button type="button" data-action="remove-row" class="btn btn-sm btn-danger">${t('button_delete')}</button>
    `;
    container.appendChild(row);
    headerIndex++;
}

async function testConnection() {
    const mcpUrl = document.getElementById('mcp_url').value.trim();
    const resultDiv = document.getElementById('connection-test-result');
    
    if (!mcpUrl) {
        resultDiv.style.display = 'block';
        resultDiv.style.padding = '12px';
        resultDiv.style.borderRadius = '6px';
        resultDiv.style.backgroundColor = '#fee';
        resultDiv.style.border = '1px solid #fcc';
        resultDiv.style.color = '#c33';
        resultDiv.textContent = t('app_mcp_url_required') || 'MCP接続URLを入力してください';
        return;
    }
    
    // Collect common headers
    const commonHeaders = {};
    const headerRows = document.querySelectorAll('#headers-container .key-value-row');
    headerRows.forEach(row => {
        const inputs = row.querySelectorAll('input[type="text"]');
        const key = inputs[0].value.trim();
        const value = inputs[1].value.trim();
        if (key) {
            commonHeaders[key] = value;
        }
    });
    
    // Show loading state
    resultDiv.style.display = 'block';
    resultDiv.style.padding = '12px';
    resultDiv.style.borderRadius = '6px';
    resultDiv.style.backgroundColor = '#f0f9ff';
    resultDiv.style.border = '1px solid #bae6fd';
    resultDiv.style.color = '#0369a1';
    resultDiv.textContent = t('app_testing_connection') || '接続テスト中...';
    
    try {
        const response = await fetch('/api/apps/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mcp_url: mcpUrl,
                common_headers: commonHeaders
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Success
            resultDiv.style.backgroundColor = '#d1fae5';
            resultDiv.style.border = '1px solid #10b981';
            resultDiv.style.color = '#065f46';
            resultDiv.textContent = '✓ ' + (t('app_connection_success') || '接続成功');
        } else {
            // Failure
            resultDiv.style.backgroundColor = '#fee';
            resultDiv.style.border = '1px solid #fcc';
            resultDiv.style.color = '#c33';
            resultDiv.textContent = '✗ ' + (result.error || t('app_connection_failed') || '接続失敗');
        }
    } catch (e) {
        // Error
        resultDiv.style.backgroundColor = '#fee';
        resultDiv.style.border = '1px solid #fcc';
        resultDiv.style.color = '#c33';
        resultDiv.textContent = '✗ ' + (t('app_connection_error') || '接続エラー') + ': ' + e.message;
    }
}

async function loadService() {
    const response = await fetch(`/api/apps/${serviceId}`);
    const service = await response.json();
    
    // Update breadcrumb with MCP service name and app name
    try {
        const mcpServiceResponse = await fetch(`/api/mcp-services/${mcpServiceId}`);
        const mcpService = await mcpServiceResponse.json();
        document.getElementById('mcp-service-link').textContent = mcpService.name;
        
        // Update app detail link with app name
        const appDetailLink = document.querySelector('a[href*="/apps/' + serviceId + '"]:not([data-i18n])');
        if (appDetailLink) {
            appDetailLink.textContent = service.name;
        }
    } catch (e) {
        console.error('Failed to fetch MCP service info:', e);
    }
    
    document.getElementById('name').value = service.name;
    document.getElementById('description').value = service.description || '';
    
    // Set service type (readonly)
    currentServiceType = service.service_type || 'api';
    document.querySelector(`input[name="service_type"][value="${currentServiceType}"]`).checked = true;
    
    // Show service type section before setting value
    showServiceTypeSection();
    
    // Set mcp_url for both MCP and API types
    if (service.mcp_url) {
        document.getElementById('mcp_url').value = service.mcp_url;
    }
    
    // Load headers for both API and MCP types
    const headers = service.common_headers || {};
    if (Object.keys(headers).length === 0) {
        addHeaderRow(); // Add empty row if no headers
    } else {
        Object.entries(headers).forEach(([key, value]) => {
            addHeaderRow(key, value);
        });
    }
    
    // If MCP type, make MCP URL and headers read-only
    if (currentServiceType === 'mcp') {
        const mcpUrlInput = document.getElementById('mcp_url');
        mcpUrlInput.readOnly = true;
        mcpUrlInput.style.backgroundColor = '#f5f5f5';
        mcpUrlInput.style.cursor = 'not-allowed';
        
        // Show readonly hint for MCP URL
        const mcpUrlHint = document.getElementById('mcp-url-readonly-hint');
        if (mcpUrlHint) {
            mcpUrlHint.style.display = 'block';
        }
        
        // Make all header inputs read-only
        const headerRows = document.querySelectorAll('#headers-container .key-value-row');
        headerRows.forEach(row => {
            const inputs = row.querySelectorAll('input[type="text"]');
            inputs.forEach(input => {
                input.readOnly = true;
                input.style.backgroundColor = '#f5f5f5';
                input.style.cursor = 'not-allowed';
            });
            // Hide delete button
            const deleteBtn = row.querySelector('button');
            if (deleteBtn) {
                deleteBtn.style.display = 'none';
            }
        });
        
        // Show readonly hint for common headers
        const headersHint = document.getElementById('common-headers-readonly-hint');
        if (headersHint) {
            headersHint.style.display = 'block';
        }
        
        // Hide "Add Header" button
        const addHeaderBtn = document.querySelector('button[data-action="add-header"]');
        if (addHeaderBtn) {
            addHeaderBtn.style.display = 'none';
        }
        
        // Hide "Test Connection" button
        const testBtn = document.querySelector('button[data-action="test-connection"]');
        if (testBtn) {
            testBtn.style.display = 'none';
        }
    }
    
    // Set access control (default: public for apps)
    currentAccessControl = service.access_control || 'public';
    const isRestricted = currentAccessControl === 'restricted';
    document.getElementById('access-control-toggle').checked = isRestricted;
    updateAccessControlUI(isRestricted);
}

// Load account permissions
async function loadPermissions() {
    const response = await fetch(`/api/apps/${serviceId}/permissions`);
    const data = await response.json();
    
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    
    enabledSelect.innerHTML = data.enabled.map(account => 
        `<option value="${account.id}">${account.name}</option>`
    ).join('');
    
    disabledSelect.innerHTML = data.disabled.map(account => 
        `<option value="${account.id}">${account.name}</option>`
    ).join('');
    
    updateCounts();
}

function moveToEnabled() {
    const disabledSelect = document.getElementById('disabled-accounts');
    const enabledSelect = document.getElementById('enabled-accounts');
    const selected = Array.from(disabledSelect.selectedOptions);
    
    selected.forEach(option => {
        enabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function moveAllToEnabled() {
    const disabledSelect = document.getElementById('disabled-accounts');
    const enabledSelect = document.getElementById('enabled-accounts');
    
    Array.from(disabledSelect.options).forEach(option => {
        enabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function moveToDisabled() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    const selected = Array.from(enabledSelect.selectedOptions);
    
    selected.forEach(option => {
        disabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function moveAllToDisabled() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    
    Array.from(enabledSelect.options).forEach(option => {
        disabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function updateCounts() {
    const enabledCount = document.getElementById('enabled-accounts').options.length;
    const disabledCount = document.getElementById('disabled-accounts').options.length;
    
    document.getElementById('enabled-count').textContent = enabledCount;
    document.getElementById('disabled-count').textContent = disabledCount;
}

// Save permissions
async function savePermissions() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const enabledAccountIds = Array.from(enabledSelect.options).map(opt => parseInt(opt.value));
    
    const response = await fetch(`/api/apps/${serviceId}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_ids: enabledAccountIds })
    });
    
    if (!response.ok) {
        throw new Error('Failed to save permissions');
    }
}

// Initialize and setup
(async () => {
    await initLanguageSwitcher();
    await loadService();
    await loadPermissions();

    document.addEventListener('click', (event) => {
        const element = event.target.closest('[data-action]');
        if (!element) return;
        const action = element.dataset.action;
        if (action === 'remove-row') element.closest('.key-value-row')?.remove();
        if (action === 'add-header') addHeaderRow();
        if (action === 'test-connection') testConnection();
        if (action === 'test-stdio') testStdioConnection();
        if (action === 'move-enabled') moveToEnabled();
        if (action === 'move-all-enabled') moveAllToEnabled();
        if (action === 'move-disabled') moveToDisabled();
        if (action === 'move-all-disabled') moveAllToDisabled();
    });
    
    // Access control toggle handler
    document.getElementById('access-control-toggle').addEventListener('change', async (e) => {
        const isRestricted = e.target.checked;
        updateAccessControlUI(isRestricted);
        currentAccessControl = isRestricted ? 'restricted' : 'public';
    });
    
    // Setup form submit handler
    document.getElementById('service-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        try {
            const formData = new FormData(e.target);
            const data = {
                name: formData.get('name'),
                description: formData.get('description'),
                service_type: currentServiceType, // Use saved value since radio is disabled
                common_headers: {}
            };
            
            // Get mcp_url for both MCP and API types
            const mcpUrlValue = formData.get('mcp_url');
            if (mcpUrlValue && mcpUrlValue.trim()) {
                data.mcp_url = mcpUrlValue.trim();
            }
            
            // Collect headers for both API and MCP types
            const headerRows = document.querySelectorAll('#headers-container .key-value-row');
            headerRows.forEach(row => {
                const inputs = row.querySelectorAll('input[type="text"]');
                const key = inputs[0].value.trim();
                const value = inputs[1].value.trim();
                if (key) {
                    data.common_headers[key] = value;
                }
            });
            
            // Update basic info
            const response = await fetch(`/api/apps/${serviceId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || t('error_unknown'));
            }
            
            // Update access control
            const accessControlResponse = await fetch(`/api/apps/${serviceId}/access-control`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ access_control: currentAccessControl })
            });
            
            if (!accessControlResponse.ok) {
                throw new Error('Failed to update access control');
            }
            
            // Save permissions if restricted
            if (currentAccessControl === 'restricted') {
                await savePermissions();
            }
            
            window.location.href = `/mcp-services/${mcpServiceId}/apps/${serviceId}`;
        } catch (error) {
            await modal.error(t('app_update_failed') + ': ' + error.message);
        }
    });
})();
