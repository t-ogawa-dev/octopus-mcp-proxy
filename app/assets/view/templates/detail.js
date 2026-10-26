// templates/detail.js - Template Detail Page

let template = null;

async function loadTemplate() {
    try {
        template = await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}`);
        
        // Update page
        document.getElementById('template-name').textContent = `${template.icon || '📦'} ${template.name}`;
        document.getElementById('template-description').textContent = template.description || '';
        document.getElementById('breadcrumb-name').textContent = template.name;
        
        // Basic info
        document.getElementById('detail-name').textContent = template.name;
        document.getElementById('detail-service-type').textContent = template.service_type.toUpperCase();
        document.getElementById('detail-category').textContent = template.category || '-';
        document.getElementById('detail-icon').textContent = template.icon || '-';
        
        // MCP URL / API Base URL
        if (template.mcp_url) {
            const urlItem = document.getElementById('mcp-url-item');
            const urlLabel = urlItem.querySelector('.detail-label');
            const urlValue = document.getElementById('detail-mcp-url');
            
            // Change label based on service type
            if (template.service_type === 'api') {
                urlLabel.textContent = 'API ベースURL';
            } else {
                urlLabel.textContent = 'MCP エンドポイントURL';
            }
            
            urlItem.style.display = 'flex';
            const safeMcpUrl = AppDom.safeHttpUrl(template.mcp_url);
            urlValue.textContent = template.mcp_url;
            if (safeMcpUrl) {
                urlValue.innerHTML = `<a href="${AppDom.escapeHtml(safeMcpUrl)}" target="_blank" rel="noopener noreferrer">${AppDom.escapeHtml(template.mcp_url)}</a>`;
            }
        }
        
        // Official URL
        if (template.official_url) {
            document.getElementById('official-url-item').style.display = 'flex';
            const officialUrlElement = document.getElementById('detail-official-url');
            const safeOfficialUrl = AppDom.safeHttpUrl(template.official_url);
            officialUrlElement.textContent = template.official_url;
            if (safeOfficialUrl) {
                officialUrlElement.innerHTML = `<a href="${AppDom.escapeHtml(safeOfficialUrl)}" target="_blank" rel="noopener noreferrer">${AppDom.escapeHtml(template.official_url)}</a>`;
            }
        }
        
        // Headers
        const headersContainer = document.getElementById('headers-list');
        let headers = {};
        if (template.common_headers) {
            // Check if it's already an object or needs parsing
            headers = typeof template.common_headers === 'string' 
                ? JSON.parse(template.common_headers) 
                : template.common_headers;
        }
        if (Object.keys(headers).length === 0) {
            headersContainer.innerHTML = '<div class="empty-state">共通ヘッダーが設定されていません</div>';
        } else {
            headersContainer.innerHTML = Object.entries(headers).map(([key, value]) => `
                <div class="header-item">
                    <span class="header-key">${AppDom.escapeHtml(key)}</span>
                    <span class="header-value">${AppDom.escapeHtml(value)}</span>
                </div>
            `).join('');
        }
        
        // For API templates, show capabilities section
        if (template.service_type === 'api') {
            document.getElementById('capabilities-section').style.display = 'block';
            await loadCapabilities();
        } else {
            document.getElementById('capabilities-section').style.display = 'none';
        }
        
        // Hide edit/delete/export buttons for builtin templates
        if (template.template_type === 'builtin') {
            document.getElementById('edit-btn').style.display = 'none';
            document.getElementById('delete-btn').style.display = 'none';
            document.getElementById('export-btn').style.display = 'none';
        }
        
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function loadCapabilities() {
    try {
        const capabilities = await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}/capabilities`);
        
        const container = document.getElementById('capabilities-list');
        
        if (capabilities.length === 0) {
            container.innerHTML = '<div class="empty-state">Capabilityが定義されていません</div>';
            return;
        }
        
        container.innerHTML = capabilities.map(cap => {
            const method = cap.method || 'GET';
            const methodClass = method.toLowerCase();
            
            return `
                <div class="capability-card">
                    <div class="capability-header">
                        <span class="capability-type-badge">${AppDom.escapeHtml(cap.capability_type)}</span>
                        <span class="http-method ${methodClass}">${AppDom.escapeHtml(method)}</span>
                        <span class="capability-name">${AppDom.escapeHtml(cap.name)}</span>
                    </div>
                    ${cap.endpoint_path ? `<div class="capability-endpoint">${AppDom.escapeHtml(cap.endpoint_path)}</div>` : ''}
                    ${cap.description ? `<div class="capability-description">${AppDom.escapeHtml(cap.description)}</div>` : ''}
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('Failed to load capabilities:', e);
    }
}

async function exportTemplate() {
    try {
        const response = await fetch(`/api/mcp-templates/${TEMPLATE_ID}/export`);
        
        // Get YAML content as text
        const yamlContent = await response.text();
        
        // Extract filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'template.yaml';
        if (contentDisposition) {
            const matches = /filename="(.+)"/.exec(contentDisposition);
            if (matches) filename = matches[1];
        }
        
        // Download as YAML file
        const blob = new Blob([yamlContent], {type: 'application/x-yaml'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function deleteTemplate() {
    const confirmed = await modal.confirmDelete(t('mcp_template_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}`, {
            method: 'DELETE'
        });
        await modal.success(t('mcp_template_deleted') || 'テンプレートを削除しました');
        window.location.href = '/mcp-templates';
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Initialize
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'export-template') exportTemplate();
        if (action === 'delete-template') deleteTemplate();
    });
    await loadTemplate();
})();
