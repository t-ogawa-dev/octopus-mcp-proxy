/**
 * サービス一覧画面
 */

async function loadServices(mcpServiceId) {
    let services = await AppApi.request('/api/apps');
    
    // MCPサービスIDでフィルタリング
    services = services.filter(s => s.mcp_service_id == mcpServiceId);
    
    const container = document.getElementById('services-list');
    
    if (services.length === 0) {
        container.innerHTML = `<div class="empty-state">${t('app_empty')}</div>`;
        return;
    }
    
    container.innerHTML = services.map(service => `
        <div class="list-item ${!service.is_enabled ? 'disabled' : ''}" data-service-id="${service.id}">
            <div class="list-item-main">
                <h3><a href="/mcp-services/${mcpServiceId}/apps/${service.id}">${AppDom.escapeHtml(service.name)}</a></h3>
                <div class="list-item-meta">
                    <span class="badge badge-${AppDom.escapeHtml(service.service_type)}">${AppDom.escapeHtml(service.service_type.toUpperCase())}</span>
                    ${!service.is_enabled ? `<span class="status-badge disabled">${t('status_disabled')}</span>` : `<span class="status-badge enabled">${t('status_enabled')}</span>`}
                    ${(service.access_control === 'restricted') ? `<span class="badge badge-access-restricted">${t('access_control_restricted')}</span>` : `<span class="badge badge-access-public">${t('access_control_public')}</span>`}
                    <span class="text-muted">${t('app_registered')}: ${new Date(service.created_at).toLocaleDateString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</span>
                </div>
                ${service.description ? `<p class="text-muted">${AppDom.escapeHtml(service.description)}</p>` : ''}
            </div>
            <div class="list-item-actions">
                <label class="toggle-switch">
                    <input type="checkbox" data-action="toggle" ${service.is_enabled ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
                <a href="/mcp-services/${mcpServiceId}/apps/${service.id}/capabilities" class="btn btn-sm btn-primary">${t('app_capabilities_button')}</a>
                <a href="/mcp-services/${mcpServiceId}/apps/${service.id}/edit" class="btn btn-sm btn-secondary">${t('button_edit')}</a>
                <button type="button" data-action="delete" class="btn btn-sm btn-danger">${t('button_delete')}</button>
            </div>
        </div>
    `).join('');
}

async function toggleApp(id, mcpServiceId) {
    try {
        await AppApi.request(`/api/apps/${id}/toggle`, {
            method: 'POST'
        });
        await loadServices(mcpServiceId);
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function deleteService(id, mcpServiceId) {
    const confirmed = await modal.confirmDelete(t('app_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/apps/${id}`, { method: 'DELETE' });
        await loadServices(mcpServiceId);
    } catch (error) {
        await modal.error(t('common_error') + ': ' + error.message);
    }
}

// 言語初期化完了後にサービス一覧を読み込む
(async () => {
    await initLanguageSwitcher();
    
    // URLからMCPサービスIDを取得
    const pathParts = window.location.pathname.split('/');
    const mcpServiceId = pathParts[2]; // /mcp-services/{id}/apps
    
    if (!mcpServiceId) {
        console.error('MCP Service ID not found in URL');
        return;
    }
    
    try {
        const mcpService = await AppApi.request(`/api/mcp-services/${mcpServiceId}`);
        
        // パンくずリストを更新
        const breadcrumb = document.getElementById('breadcrumb');
        breadcrumb.innerHTML = `
            <a href="/dashboard" data-i18n="breadcrumb_home">${t('breadcrumb_home')}</a>
            <span class="breadcrumb-separator">›</span>
            <a href="/mcp-services" data-i18n="mcp_service_list_title">${t('mcp_service_list_title')}</a>
            <span class="breadcrumb-separator">›</span>
            <a href="/mcp-services/${mcpServiceId}">${AppDom.escapeHtml(mcpService.name)}</a>
            <span class="breadcrumb-separator">›</span>
            <span class="breadcrumb-current" data-i18n="breadcrumb_app_list">${t('breadcrumb_app_list')}</span>
        `;
        
        // タイトルを更新
        document.getElementById('page-title').textContent = `${mcpService.name} - ${t('app_list_title')}`;
        document.getElementById('page-desc').textContent = mcpService.description || t('app_list_desc');
        
        // 新規作成ボタンにMCPサービスIDを追加
        const newButton = document.getElementById('new-app-button');
        newButton.href = `/mcp-services/${mcpServiceId}/apps/new`;
    } catch (e) {
        console.error('Failed to load MCP service:', e);
    }
    
    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        const serviceItem = actionElement?.closest('[data-service-id]');
        if (!serviceItem) return;
        if (actionElement.dataset.action === 'toggle') toggleApp(serviceItem.dataset.serviceId, mcpServiceId);
        if (actionElement.dataset.action === 'delete') deleteService(serviceItem.dataset.serviceId, mcpServiceId);
    });
    await loadServices(mcpServiceId);
})();
