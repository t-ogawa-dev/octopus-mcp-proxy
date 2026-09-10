/**
 * MCPサービス一覧画面
 */

async function loadMcpServices() {
    const services = await AppApi.request('/api/mcp-services');
    
    const container = document.getElementById('services-list');
    
    if (services.length === 0) {
        container.innerHTML = `<div class="empty-state">${t('mcp_service_empty')}</div>`;
        return;
    }
    
    container.innerHTML = services.map(service => {
        // Get current host from window.location
        const currentHost = window.location.host;
        const protocol = window.location.protocol;
        
        let endpoint;
        if (service.routing_type === 'path') {
            endpoint = `${protocol}//${currentHost}/${service.identifier}/mcp`;
        } else {
            // For subdomain routing
            const hostWithoutPort = currentHost.split(':')[0];
            const port = currentHost.includes(':') ? ':' + currentHost.split(':')[1] : '';
            const hostParts = hostWithoutPort.split('.');
            
            let subdomainHost;
            if (hostParts.length >= 4 || (hostParts.length === 3 && !['com', 'net', 'org', 'io', 'dev', 'app'].includes(hostParts[hostParts.length-1]))) {
                // Has subdomain: replace first part
                hostParts[0] = service.identifier;
                subdomainHost = hostParts.join('.') + port;
            } else if (hostParts.length === 3) {
                // 3 parts with common TLD: replace first
                hostParts[0] = service.identifier;
                subdomainHost = hostParts.join('.') + port;
            } else {
                // 2 or less parts: add prefix
                subdomainHost = `${service.identifier}.${currentHost}`;
            }
            endpoint = `${protocol}//${subdomainHost}/mcp`;
        }
        
        const escapedName = AppDom.escapeHtml(service.name);
        const escapedIdentifier = AppDom.escapeHtml(service.identifier);
        const escapedEndpoint = AppDom.escapeHtml(endpoint);
        const escapedDescription = AppDom.escapeHtml(service.description);

        return `
        <div class="list-item ${!service.is_enabled ? 'disabled' : ''}" data-service-id="${service.id}">
            <div class="list-item-main">
                <h3><a href="/mcp-services/${service.id}">${escapedName}</a></h3>
                <div class="list-item-meta">
                    <span class="badge">${t('mcp_service_identifier')}: ${escapedIdentifier}</span>
                    ${!service.is_enabled ? `<span class="status-badge disabled">${t('status_disabled')}</span>` : `<span class="status-badge enabled">${t('status_enabled')}</span>`}
                    ${(service.access_control === 'restricted') ? `<span class="badge badge-access-restricted">${t('access_control_restricted')}</span>` : `<span class="badge badge-access-public">${t('access_control_public')}</span>`}
                    <span class="text-muted">${t('mcp_service_apps_count')}: ${service.apps_count || 0}</span>
                </div>
                <p class="text-muted" style="font-size: 12px; margin-top: 5px;">Endpoint: <code>${escapedEndpoint}</code></p>
                ${service.description ? `<p class="text-muted">${escapedDescription}</p>` : ''}
            </div>
            <div class="list-item-actions">
                <label class="toggle-switch">
                    <input type="checkbox" data-action="toggle" ${service.is_enabled ? 'checked' : ''}>
                    <span class="toggle-slider"></span>
                </label>
                <a href="/mcp-services/${service.id}/apps" class="btn btn-sm btn-primary">${t('mcp_service_apps_button')}</a>
                <a href="/mcp-services/${service.id}/edit" class="btn btn-sm btn-secondary">${t('button_edit')}</a>
                <button type="button" data-action="delete" class="btn btn-sm btn-danger">${t('button_delete')}</button>
            </div>
        </div>
        `;
    }).join('');
}

async function toggleMcpService(id) {
    try {
        await AppApi.request(`/api/mcp-services/${id}/toggle`, {
            method: 'POST'
        });
        await loadMcpServices();
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function deleteMcpService(id) {
    const confirmed = await modal.confirmDelete(t('mcp_service_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/mcp-services/${id}`, { method: 'DELETE' });
        await loadMcpServices();
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Import Modal Functions
let selectedFile = null;

function openImportModal() {
    // Bootstrapのbackdropを削除（Bootstrapモーダルが誤って作成されている場合）
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    document.getElementById('import-modal').style.display = 'flex';
    document.getElementById('import-error').style.display = 'none';
    clearFile();
}

function closeImportModal() {
    document.getElementById('import-modal').style.display = 'none';
    clearFile();
}

function clearFile() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    document.getElementById('file-info').style.display = 'none';
    document.querySelector('.drop-zone-content').style.display = 'flex';
    document.getElementById('import-btn').disabled = true;
}

function handleFileSelect(file) {
    if (!file || (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml'))) {
        showImportError(currentLanguage === 'ja' ? 'YAMLファイルを選択してください' : 'Please select a YAML file');
        return;
    }
    
    selectedFile = file;
    document.querySelector('.file-info-name').textContent = file.name;
    document.getElementById('file-info').style.display = 'flex';
    document.querySelector('.drop-zone-content').style.display = 'none';
    document.getElementById('import-btn').disabled = false;
    document.getElementById('import-error').style.display = 'none';
}

function showImportError(message) {
    const errorDiv = document.getElementById('import-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

async function confirmImport() {
    if (!selectedFile) return;
    
    try {
        const fileContent = await selectedFile.text();
        
        const result = await AppApi.request('/api/mcp-services/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-yaml' },
            body: fileContent
        });
        
        closeImportModal();
        
        // Show success message with identifier change warning if applicable
        let message = currentLanguage === 'ja' ? 'インポートしました' : 'Imported successfully';
        if (result.identifier_changed) {
            message += currentLanguage === 'ja' 
                ? ` 識別子が重複していたため、新しい識別子「${result.mcp_service.identifier}」が割り当てられました。`
                : ` Identifier was changed to "${result.mcp_service.identifier}" due to conflict.`;
        }
        await modal.success(message);
        
        await loadMcpServices();
    } catch (error) {
        console.error('Import error:', error);
        showImportError(error.message || (currentLanguage === 'ja' ? 'インポートに失敗しました' : 'Import failed'));
    }
}

function setupEventListeners() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        if (!actionElement) return;

        const action = actionElement.dataset.action;
        const serviceItem = actionElement.closest('[data-service-id]');
        const serviceId = serviceItem?.dataset.serviceId;

        if (action === 'open-import') openImportModal();
        if (action === 'close-import') closeImportModal();
        if (action === 'select-file') fileInput.click();
        if (action === 'clear-file') clearFile();
        if (action === 'confirm-import') confirmImport();
        if (action === 'delete' && serviceId) deleteMcpService(serviceId);
    });

    document.addEventListener('change', (event) => {
        const actionElement = event.target.closest('[data-action="toggle"]');
        if (!actionElement) return;

        const serviceItem = actionElement.closest('[data-service-id]');
        if (serviceItem) toggleMcpService(serviceItem.dataset.serviceId);
    });

    if (dropZone) {
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        
        const file = e.dataTransfer.files[0];
        handleFileSelect(file);
    });
    }

    if (fileInput) {
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        handleFileSelect(file);
    });
    }
}

// 言語初期化完了後にMCPサービス一覧を読み込む
(async () => {
    await initLanguageSwitcher();
    setupEventListeners();
    await loadMcpServices();
})();
