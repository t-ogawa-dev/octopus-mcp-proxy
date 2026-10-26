// services/capabilities.js - Service Capabilities List
const pathParts = window.location.pathname.split('/');
const mcpServiceId = Number.parseInt(pathParts[2], 10);
const serviceId = Number.parseInt(pathParts[4], 10);
let isMcpType = false;
let baseUrl = '';

async function loadCapabilities() {
    // Validate serviceId before making API call
    if (isNaN(serviceId) || serviceId <= 0) {
        console.error('Invalid service ID:', serviceId, 'from URL:', window.location.pathname);
        const container = document.getElementById('capabilities-list');
        container.innerHTML = `<div class="error-state">エラー: サービスIDが無効です（URL: ${AppDom.escapeHtml(window.location.pathname)}）</div>`;
        return;
    }
    
    try {
        const response = await fetch(`/api/apps/${serviceId}/capabilities`);
        
        // Check if response is JSON
        const contentType = response.headers.get('content-type');
        if (!contentType || !contentType.includes('application/json')) {
            console.error('Expected JSON response but got:', contentType);
            const text = await response.text();
            console.error('Response text:', text.substring(0, 200));
            throw new Error(`サーバーエラー: JSONではないレスポンスが返されました (${response.status})`);
        }
        
        const capabilities = await response.json();
        
        // Check for error in JSON response
        if (!response.ok) {
            throw new Error(capabilities.error || `サーバーエラー: ${response.status}`);
        }
    
    const container = document.getElementById('capabilities-list');
    
    if (capabilities.length === 0) {
        container.innerHTML = `<div class="empty-state">${t('capability_empty')}</div>`;
        return;
    }
    
    container.innerHTML = capabilities.map(cap => {
        // Build full URL display: baseUrl + endpoint_path (only for tool types)
        let urlDisplay = '';
        if (cap.capability_type === 'tool' || cap.capability_type === 'mcp_tool') {
            urlDisplay = AppDom.escapeHtml(cap.url || 'N/A');
            if (baseUrl && cap.url && !cap.url.startsWith('http')) {
                // If cap.url is a relative path, combine with baseUrl
                const separator = baseUrl.endsWith('/') || cap.url.startsWith('/') ? '' : '/';
                urlDisplay = `<span style="color: #666;">${AppDom.escapeHtml(baseUrl)}</span>${separator}<span style="font-weight: 600;">${AppDom.escapeHtml(cap.url)}</span>`;
            }
        }
        
        return `
        <div class="list-item ${!cap.is_enabled ? 'disabled' : ''}">
            <div class="list-item-main">
                <h3><a href="/capabilities/${Number(cap.id)}">${AppDom.escapeHtml(cap.name)}</a></h3>
                <div class="list-item-meta">
                    <span class="badge badge-${AppDom.escapeHtml(cap.capability_type)}">${AppDom.escapeHtml(cap.capability_type.toUpperCase())}</span>
                    ${!cap.is_enabled ? `<span class="status-badge disabled">${t('status_disabled')}</span>` : `<span class="status-badge enabled">${t('status_enabled')}</span>`}
                    ${(cap.access_control === 'restricted') ? `<span class="badge badge-access-restricted">${t('access_control_restricted')}</span>` : `<span class="badge badge-access-public">${t('access_control_public')}</span>`}
                    ${urlDisplay ? `<span class="text-muted" style="font-family: monospace; font-size: 0.9em;">${urlDisplay}</span>` : ''}
                </div>
                ${cap.description ? `<p class="text-muted">${AppDom.escapeHtml(cap.description)}</p>` : ''}
            </div>
            <div class="list-item-actions">
                <label class="toggle-switch">
                    <input type="checkbox" data-action="toggle-capability" data-capability-id="${cap.id}" ${cap.is_enabled ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
                <a href="/capabilities/${cap.id}/edit" class="btn btn-sm btn-secondary">${t('button_edit')}</a>
                ${!isMcpType ? `<button type="button" data-action="delete-capability" data-capability-id="${cap.id}" class="btn btn-sm btn-danger">${t('button_delete')}</button>` : ''}
            </div>
        </div>
    `;
    }).join('');
    } catch (error) {
        console.error('Failed to load capabilities:', error);
        const container = document.getElementById('capabilities-list');
        container.innerHTML = `<div class="error-state">エラー: ${AppDom.escapeHtml(error.message)}</div>`;
    }
}

async function toggleCapability(id) {
    try {
        await AppApi.request(`/api/capabilities/${id}/toggle`, {
            method: 'POST'
        });
        await loadCapabilities();
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function deleteCapability(id) {
    const confirmed = await modal.confirmDelete(t('capability_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/capabilities/${id}`, { method: 'DELETE' });
        await loadCapabilities();
    } catch (error) {
        await modal.error(t('common_error') + ': ' + error.message);
    }
}

// Initialize language and load capabilities
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const element = event.target.closest('[data-action]');
        if (!element) return;
        const id = element.dataset.capabilityId;
        if (element.dataset.action === 'delete-capability') deleteCapability(id);
    });
    document.addEventListener('change', (event) => {
        const element = event.target.closest('[data-action="toggle-capability"]');
        if (element) toggleCapability(element.dataset.capabilityId);
    });
    
    // Get parent app information to check if it's MCP type and get base URL
    try {
        const appResponse = await fetch(`/api/apps/${serviceId}`);
        const app = await appResponse.json();
        isMcpType = app.service_type === 'mcp';
        baseUrl = app.mcp_url || '';
        
        // Update breadcrumb with MCP service name and app name
        const mcpServiceResponse = await fetch(`/api/mcp-services/${mcpServiceId}`);
        const mcpService = await mcpServiceResponse.json();
        document.getElementById('mcp-service-link').textContent = mcpService.name;
        
        // Update app detail link with app name (by href since it has data-i18n)
        const breadcrumb = document.querySelector('.breadcrumb');
        const appDetailLink = breadcrumb.querySelector(`a[href="/mcp-services/${mcpServiceId}/apps/${serviceId}"]`);
        if (appDetailLink) {
            appDetailLink.textContent = app.name;
        }
        
        // Hide "New Capability" button for MCP type
        if (isMcpType) {
            const newCapabilityBtn = document.querySelector('a[href*="/capabilities/new"]');
            if (newCapabilityBtn) {
                newCapabilityBtn.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('Failed to fetch app info:', e);
    }
    
    loadCapabilities();
})();
