/**
 * MCPサービス編集画面
 * アクセス制御: トグルON=制限あり(restricted), OFF=制限なし(public)
 */

const mcpServiceId = parseInt(window.location.pathname.split('/')[2]);
let currentAccessControl = 'restricted'; // デフォルトはrestricted

// Update access control UI
function updateAccessControlUI(isRestricted) {
    const permissionsSection = document.getElementById('permissions-section');
    
    if (isRestricted) {
        permissionsSection.style.display = 'block';
    } else {
        permissionsSection.style.display = 'none';
    }
}

// Update routing hint
function updateRoutingHint() {
    const routingType = document.getElementById('routing_type').value;
    const identifier = document.getElementById('identifier').value || '{identifier}';
    const hintElement = document.getElementById('routing-hint');
    
    // Get current host from window.location
    const currentHost = window.location.host; // includes port if present
    const protocol = window.location.protocol; // http: or https:
    
    if (routingType === 'path') {
        hintElement.textContent = `パス方式: ${protocol}//${currentHost}/${identifier}/mcp`;
    } else {
        // For subdomain routing
        const hostWithoutPort = currentHost.split(':')[0];
        const port = currentHost.includes(':') ? ':' + currentHost.split(':')[1] : '';
        const hostParts = hostWithoutPort.split('.');
        
        let subdomainHost;
        // Check if it's a multi-level TLD or already has subdomain
        // Examples: auc.co.jp (2+1), www.auc.co.jp (1+2+1), auc-mcp.ngrok.io (1+2)
        if (hostParts.length >= 4 || (hostParts.length === 3 && !['com', 'net', 'org', 'io', 'dev', 'app'].includes(hostParts[hostParts.length-1]))) {
            // Has subdomain: replace first part (e.g., www.auc.co.jp -> sample.auc.co.jp)
            hostParts[0] = identifier;
            subdomainHost = hostParts.join('.') + port;
        } else if (hostParts.length === 3) {
            // 3 parts with common TLD: replace first (e.g., auc-mcp.ngrok.io -> sample.ngrok.io)
            hostParts[0] = identifier;
            subdomainHost = hostParts.join('.') + port;
        } else {
            // 2 or less parts: add prefix (e.g., auc.com -> sample.auc.com)
            subdomainHost = `${identifier}.${currentHost}`;
        }
        hintElement.textContent = `サブドメイン方式: ${protocol}//${subdomainHost}/mcp`;
    }
}

// Load MCP Service data
async function loadMcpService() {
    const response = await fetch(`/api/mcp-services/${mcpServiceId}`);
    const service = await response.json();
    
    // Update breadcrumb with service name
    const detailLink = document.querySelector('a[href="/mcp-services/' + mcpServiceId + '"]');
    if (detailLink && service.name) {
        detailLink.textContent = service.name;
    }
    
    document.getElementById('name').value = service.name;
    document.getElementById('identifier').value = service.identifier;
    document.getElementById('routing_type').value = service.routing_type || 'subdomain';
    document.getElementById('description').value = service.description || '';
    
    // Update routing hint
    updateRoutingHint();
    
    // Set access control
    currentAccessControl = service.access_control || 'restricted';
    const isRestricted = currentAccessControl === 'restricted';
    document.getElementById('access-control-toggle').checked = isRestricted;
    updateAccessControlUI(isRestricted);
}

// Load account permissions
async function loadPermissions() {
    const response = await fetch(`/api/mcp-services/${mcpServiceId}/permissions`);
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
    
    const response = await fetch(`/api/mcp-services/${mcpServiceId}/permissions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ account_ids: enabledAccountIds })
    });
    
    if (!response.ok) {
        throw new Error('Failed to save permissions');
    }
}

(async () => {
    await initLanguageSwitcher();
    await loadMcpService();
    await loadPermissions();

    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'move-enabled') moveToEnabled();
        if (action === 'move-all-enabled') moveAllToEnabled();
        if (action === 'move-disabled') moveToDisabled();
        if (action === 'move-all-disabled') moveAllToDisabled();
    });
    
    // Routing type change handler
    document.getElementById('routing_type').addEventListener('change', updateRoutingHint);
    document.getElementById('identifier').addEventListener('input', updateRoutingHint);
    
    // Access control toggle handler
    document.getElementById('access-control-toggle').addEventListener('change', async (e) => {
        const isRestricted = e.target.checked;
        updateAccessControlUI(isRestricted);
        currentAccessControl = isRestricted ? 'restricted' : 'public';
    });
    
    // Form submit handler
    document.getElementById('mcp-service-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        try {
            // Update basic info
            const formData = new FormData(e.target);
            const data = {
                name: formData.get('name'),
                identifier: formData.get('identifier'),
                routing_type: formData.get('routing_type'),
                description: formData.get('description')
            };
            
            const response = await fetch(`/api/mcp-services/${mcpServiceId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || t('error_unknown'));
            }
            
            // Update access control
            const accessControlResponse = await fetch(`/api/mcp-services/${mcpServiceId}/access-control`, {
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
            
            window.location.href = `/mcp-services/${mcpServiceId}`;
        } catch (error) {
            await modal.error(t('mcp_service_update_failed') + ': ' + error.message);
        }
    });
})();
