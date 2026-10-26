// templates/capability_detail.js - Capability Detail Page

let capability = null;
let template = null;

async function loadCapability() {
    try {
        // Load template first
        template = await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}`);
        document.getElementById('breadcrumb-template').textContent = template.name;
        
        // Load capability
        capability = await AppApi.request(`/api/template-capabilities/${CAPABILITY_ID}`);
        
        // Update page
        document.getElementById('capability-name').textContent = capability.name;
        document.getElementById('capability-description').textContent = capability.description || '';
        document.getElementById('breadcrumb-capability').textContent = capability.name;
        
        // Basic info
        document.getElementById('detail-name').textContent = capability.name;
        document.getElementById('detail-type').textContent = capability.capability_type;
        document.getElementById('detail-url').textContent = capability.url || '-';
        
        // Headers
        const headersContainer = document.getElementById('headers-list');
        let headers = {};
        if (capability.headers) {
            headers = typeof capability.headers === 'string' 
                ? JSON.parse(capability.headers) 
                : capability.headers;
        }
        if (Object.keys(headers).length === 0) {
            headersContainer.innerHTML = `<div class="empty-state" data-i18n="capability_no_headers">${t('capability_no_headers')}</div>`;
        } else {
            headersContainer.innerHTML = Object.entries(headers).map(([key, value]) => `
                <div class="header-item">
                    <span class="header-key">${AppDom.escapeHtml(key)}</span>
                    <span class="header-value">${AppDom.escapeHtml(value)}</span>
                </div>
            `).join('');
        }
        
        // Body params
        const paramsContainer = document.getElementById('body-params-list');
        let params = {};
        if (capability.body_params) {
            params = typeof capability.body_params === 'string' 
                ? JSON.parse(capability.body_params) 
                : capability.body_params;
        }
        if (Object.keys(params).length === 0) {
            paramsContainer.innerHTML = `<div class="empty-state" data-i18n="capability_no_params">${t('capability_no_params')}</div>`;
        } else {
            paramsContainer.innerHTML = Object.entries(params).map(([key, value]) => `
                <div class="param-item">
                    <span class="param-key">${AppDom.escapeHtml(key)}</span>
                    <span class="param-value">${AppDom.escapeHtml(JSON.stringify(value))}</span>
                </div>
            `).join('');
        }
        
        // Template content
        const templateSection = document.getElementById('template-section');
        if (capability.template_content) {
            document.getElementById('template-content').textContent = capability.template_content;
        } else {
            templateSection.style.display = 'none';
        }
        
        // Hide edit/delete buttons for builtin templates
        if (template.template_type === 'builtin') {
            document.getElementById('edit-btn').style.display = 'none';
            document.getElementById('delete-btn').style.display = 'none';
        }
        
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function deleteCapability() {
    const confirmed = await modal.confirmDelete(t('capability_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/template-capabilities/${CAPABILITY_ID}`, {
            method: 'DELETE'
        });
        window.location.href = `/mcp-templates/${TEMPLATE_ID}/capabilities?message=${encodeURIComponent('削除しました')}`;
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Initialize
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'delete-capability') deleteCapability();
        if (action === 'back') window.history.back();
    });
    await loadCapability();
})();
