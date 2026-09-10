// templates/list.js - Template List Page
let currentTab = 'api';
let selectedTemplateId = null;
let selectedMcpServiceId = null;
let createdAppId = null;

function showFlashMessage(message) {
    const flashDiv = document.getElementById('flash-message');
    flashDiv.textContent = message;
    flashDiv.style.display = 'block';
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        flashDiv.style.display = 'none';
    }, 5000);
}

async function loadTemplates(type) {
    let apiType = type;
    let containerId;
    
    if (type === 'api' || type === 'mcp') {
        apiType = 'builtin';
        containerId = `${type}-templates`;
    } else {
        containerId = 'custom-templates';
    }
    
    let templates = await AppApi.request(`/api/mcp-templates?type=${encodeURIComponent(apiType)}`);
    
    // Filter by service_type for builtin templates
    if (type === 'api') {
        templates = templates.filter(t => t.service_type === 'api');
    } else if (type === 'mcp') {
        templates = templates.filter(t => t.service_type === 'mcp');
    }
    
    const container = document.getElementById(containerId);
    
    if (templates.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📦</div>
                <p data-i18n="mcp_template_empty">${t('mcp_template_empty')}</p>
            </div>
        `;
        return;
    }
    
    // For API templates, fetch capability counts
    const capabilityCounts = {};
    if (type === 'api') {
        for (const template of templates) {
            try {
                const capabilities = await AppApi.request(`/api/mcp-templates/${template.id}/capabilities`);
                capabilityCounts[template.id] = capabilities.length;
            } catch (e) {
                console.error(`Failed to load capabilities for template ${template.id}:`, e);
            }
        }
    }
    
    container.innerHTML = templates.map(template => {
        const officialUrl = template.official_url || '';
        const officialLink = /^https?:\/\//i.test(officialUrl)
            ? `<a href="${AppDom.escapeHtml(officialUrl)}" target="_blank" rel="noopener noreferrer" class="template-link" data-action="official-link" title="公式サイト">🔗</a>`
            : '';
        
        const capabilityBadge = type === 'api' && capabilityCounts[template.id] ? 
            `<span class="capability-badge">${capabilityCounts[template.id]} APIs</span>` : '';
        
        return `
            <div class="template-card" data-template-id="${template.id}">
                <div class="template-header">
                    <div class="template-icon">${AppDom.escapeHtml(template.icon || '📦')}</div>
                    <div class="template-info">
                        <div class="template-name">${AppDom.escapeHtml(template.name)} ${officialLink}</div>
                        <div class="template-category">${AppDom.escapeHtml(template.category || 'General')} ${capabilityBadge}</div>
                    </div>
                </div>
                <div class="template-description">${AppDom.escapeHtml(template.description || '')}</div>
                ${template.mcp_url ? `<div class="template-url">${AppDom.escapeHtml(template.mcp_url)}</div>` : ''}
                <div class="template-meta">
                    <div class="template-actions">
                        <button type="button" class="btn-small btn-use" data-action="use-template" data-i18n="mcp_template_use_button">${t('mcp_template_use_button')}</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function useTemplate(templateId) {
    selectedTemplateId = templateId;
    
    // Load MCP services
    loadMcpServicesForModal();
    
    // Bootstrapのbackdropを削除
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    // Show modal
    const modal = document.getElementById('use-template-modal');
    const errorDiv = document.getElementById('modal-error');
    
    modal.style.display = 'flex';
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';
}

async function loadMcpServicesForModal() {
    const select = document.getElementById('modal-mcp-service');
    
    try {
        const services = await AppApi.request('/api/mcp-services');
        
        if (services.length === 0) {
            select.innerHTML = '<option value="" disabled>' + t('mcp_template_no_services') + '</option>';
            return;
        }
        
        select.innerHTML = services
            .filter(service => service.is_enabled)
            .map(service => 
                `<option value="${service.id}">${service.name} (${service.identifier})</option>`
            ).join('');
    } catch (e) {
        select.innerHTML = '<option value="" disabled>Failed to load services</option>';
    }
}

function closeModal() {
    const modal = document.getElementById('use-template-modal');
    const errorDiv = document.getElementById('modal-error');
    modal.style.display = 'none';
    errorDiv.style.display = 'none';
    errorDiv.textContent = '';
    selectedTemplateId = null;
}

function showModalError(message) {
    const errorDiv = document.getElementById('modal-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function showSuccessModal(serviceName) {
    // Bootstrapのbackdropを削除
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    const modal = document.getElementById('success-modal');
    const message = document.getElementById('success-message');
    message.textContent = serviceName;
    modal.style.display = 'flex';
}

function closeSuccessModal() {
    const modal = document.getElementById('success-modal');
    modal.style.display = 'none';
}

function goToAppDetail() {
    if (selectedMcpServiceId && createdAppId) {
        window.location.href = `/mcp-services/${selectedMcpServiceId}/apps/${createdAppId}`;
    } else if (selectedMcpServiceId) {
        window.location.href = `/mcp-services/${selectedMcpServiceId}/apps`;
    } else {
        window.location.href = '/mcp-services';
    }
}

function confirmTemplateUse() {
    const select = document.getElementById('modal-mcp-service');
    const mcpServiceId = select.value;
    
    if (!mcpServiceId) {
        showModalError(t('mcp_template_select_service_required'));
        return;
    }
    
    // Save IDs before applying
    const templateId = selectedTemplateId;
    selectedMcpServiceId = mcpServiceId;
    applyTemplate(templateId, mcpServiceId);
}

// Close modal when clicking outside
window.onclick = function(event) {
    const useModal = document.getElementById('use-template-modal');
    const successModal = document.getElementById('success-modal');
    if (event.target === useModal) {
        closeModal();
    }
    // Success modal should not close on outside click
}

// Handle Enter key in modal
document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('modal-subdomain');
    if (input) {
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                confirmTemplateUse();
            }
        });
    }
});


async function applyTemplate(templateId, mcpServiceId) {
    try {
        const result = await AppApi.request(`/api/mcp-templates/${templateId}/prepare-app`, {
            method: 'POST',
            body: JSON.stringify({mcp_service_id: mcpServiceId})
        });

        sessionStorage.setItem('app_template_data', JSON.stringify(result.template_data));
        window.location.href = result.redirect_url + '?from=template';
    } catch (e) {
        console.error('Apply template exception:', e);
        showModalError(t('app_register_failed') + ': ' + e.message);
    }
}

async function exportTemplate(templateId, event) {
    event.stopPropagation();
    
    try {
        const response = await fetch(`/api/mcp-templates/${templateId}/export`);
        
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

function editTemplate(templateId, event) {
    event.stopPropagation();
    window.location.href = `/mcp-templates/${templateId}/edit`;
}

function viewCapabilities(templateId, event) {
    event.stopPropagation();
    window.location.href = `/mcp-templates/${templateId}/capabilities`;
}

async function deleteTemplate(templateId, event) {
    event.stopPropagation();
    
    const confirmed = await modal.confirmDelete(t('mcp_template_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/mcp-templates/${templateId}`, {method: 'DELETE'});
        showFlashMessage('削除しました');
        await loadTemplates('custom');
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Tab switching
document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
        const tabName = tab.dataset.tab;
        
        // Update active tab
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        // Show/hide content
        document.getElementById('api-tab').style.display = tabName === 'api' ? 'block' : 'none';
        document.getElementById('mcp-tab').style.display = tabName === 'mcp' ? 'block' : 'none';
        document.getElementById('custom-tab').style.display = tabName === 'custom' ? 'block' : 'none';
        
        currentTab = tabName;
        loadTemplates(tabName);
    });
});

document.addEventListener('click', (event) => {
    const actionElement = event.target.closest('[data-action]');
    const action = actionElement?.dataset.action;

    if (action === 'check-updates') checkTemplateUpdates();
    if (action === 'open-import') openImportModal();
    if (action === 'close-use-modal') closeModal();
    if (action === 'confirm-template-use') confirmTemplateUse();
    if (action === 'close-success-modal') closeSuccessModal();
    if (action === 'go-to-app') goToAppDetail();
    if (action === 'close-import') closeImportModal();
    if (action === 'select-file') document.getElementById('file-input').click();
    if (action === 'clear-file') clearFile();
    if (action === 'confirm-import') confirmImport();
    if (action === 'close-update') closeUpdateModal();
    if (action === 'sync-templates') syncTemplates();

    if (action && action !== 'official-link' && !action.startsWith('use-template')) {
        return;
    }

    if (actionElement?.dataset.action === 'official-link') {
        event.stopPropagation();
        return;
    }

    const templateCard = actionElement?.closest('[data-template-id]');
    if (!templateCard) return;

    if (actionElement?.dataset.action === 'use-template') {
        event.stopPropagation();
        useTemplate(templateCard.dataset.templateId);
        return;
    }

    if (!actionElement) {
        window.location.href = `/mcp-templates/${templateCard.dataset.templateId}`;
    }
});

// Import functionality
let selectedFile = null;

function openImportModal() {
    // Bootstrapのbackdropを削除
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    const modal = document.getElementById('import-modal');
    const errorDiv = document.getElementById('import-error');
    modal.style.display = 'flex';
    errorDiv.style.display = 'none';
    clearFile();
}

function closeImportModal() {
    const modal = document.getElementById('import-modal');
    modal.style.display = 'none';
    clearFile();
}

function clearFile() {
    selectedFile = null;
    document.getElementById('file-input').value = '';
    const dropZoneContent = document.querySelector('.drop-zone-content');
    const fileInfo = document.getElementById('file-info');
    if (dropZoneContent) dropZoneContent.style.display = 'flex';
    if (fileInfo) fileInfo.style.display = 'none';
    document.getElementById('import-btn').disabled = true;
}

function showImportError(message) {
    const errorDiv = document.getElementById('import-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
}

function handleFileSelect(file) {
    if (!file) return;
    
    if (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml')) {
        showImportError('YAMLファイルを選択してください');
        return;
    }
    
    selectedFile = file;
    document.getElementById('drop-zone').querySelector('.drop-zone-content').style.display = 'none';
    const fileInfo = document.getElementById('file-info');
    fileInfo.style.display = 'flex';
    fileInfo.querySelector('.file-info-name').textContent = file.name;
    document.getElementById('import-btn').disabled = false;
    document.getElementById('import-error').style.display = 'none';
}

async function confirmImport() {
    if (!selectedFile) return;
    
    try {
        const fileContent = await selectedFile.text();
        
        const response = await fetch('/api/mcp-templates/import', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-yaml'
            },
            body: fileContent
        });
        
        if (response.ok) {
            closeImportModal();
            // Reload page with success message
            window.location.href = '/mcp-templates?message=' + encodeURIComponent('インポートしました！');
        } else {
            const error = await response.json();
            showImportError(error.error || 'インポートに失敗しました');
        }
    } catch (e) {
        showImportError('ファイルの読み込みに失敗しました: ' + e.message);
    }
}

// Setup drag and drop
document.addEventListener('DOMContentLoaded', () => {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    
    if (!dropZone || !fileInput) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });
    
    // Highlight drop zone when dragging over
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        });
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        });
    });
    
    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });
    
    // Handle file input change
    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });
});

// Initialize
(async () => {
    await initLanguageSwitcher();
    
    // Check for template updates on page load
    checkTemplateUpdatesOnLoad();
    
    // Check for flash message in URL params
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    if (message) {
        showFlashMessage(decodeURIComponent(message));
        // Remove message from URL
        window.history.replaceState({}, '', '/mcp-templates');
        
        // Switch to custom tab when showing flash message
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelector('.tab[data-tab="custom"]').classList.add('active');
        document.getElementById('api-tab').style.display = 'none';
        document.getElementById('mcp-tab').style.display = 'none';
        document.getElementById('custom-tab').style.display = 'block';
        currentTab = 'custom';
        loadTemplates('custom');
    } else {
        loadTemplates('api');
    }
})();

// ============= Template Update Functions =============

async function checkTemplateUpdatesOnLoad() {
    try {
        const data = await AppApi.request('/api/templates/check-updates');
        if (data.has_update) {
            document.getElementById('update-badge').style.display = 'inline-block';
        }
    } catch (error) {
        console.error('Failed to check for template updates:', error);
    }
}

async function checkTemplateUpdates() {
    // Bootstrapのbackdropを削除
    const backdrops = document.querySelectorAll('.modal-backdrop');
    backdrops.forEach(backdrop => backdrop.remove());
    document.body.classList.remove('modal-open');
    document.body.style.overflow = '';
    document.body.style.paddingRight = '';
    
    const updateModal = document.getElementById('update-modal');
    const updateError = document.getElementById('update-error');
    const updateCheckContent = document.getElementById('update-check-content');
    const updateProgress = document.getElementById('update-progress');
    const syncBtn = document.getElementById('sync-btn');
    
    updateModal.style.display = 'flex';
    updateCheckContent.style.display = 'none';
    updateProgress.style.display = 'block';
    updateError.style.display = 'none';
    syncBtn.style.display = 'none';
    
    try {
        const data = await AppApi.request('/api/templates/check-updates');
        
        updateProgress.style.display = 'none';
        updateCheckContent.style.display = 'block';
        
        // バージョン情報を表示
        document.getElementById('current-version').textContent = data.current_version;
        document.getElementById('latest-version').textContent = data.latest_version;
        
        if (data.has_update) {
            // 新しいバージョンがある場合
            document.getElementById('update-modal-title').textContent = t('mcp_template_update_available') || '最新版のテンプレートがあります';
            document.getElementById('update-modal-message').textContent = 
                t('mcp_template_update_confirm') || 'テンプレートを最新版に同期しますか？';
            document.getElementById('changelog').textContent = data.changelog;
            document.getElementById('update-details').style.display = 'block';
        } else {
            // 最新の状態（再同期も可能）
            document.getElementById('update-modal-title').textContent = t('mcp_template_up_to_date') || '最新の状態です';
            document.getElementById('update-modal-message').textContent = 
                t('mcp_template_resync_confirm') || 'テンプレートは最新版です。再同期しますか？';
            document.getElementById('changelog').textContent = t('mcp_template_no_changes') || '変更なし';
            document.getElementById('update-details').style.display = 'block';
        }
        
        // 同期ボタンは常に表示（最新の状態でも再同期可能）
        syncBtn.style.display = 'inline-block';
        
    } catch (error) {
        updateProgress.style.display = 'none';
        updateCheckContent.style.display = 'none';
        updateError.textContent = error.message;
        updateError.style.display = 'block';
    }
}

async function syncTemplates() {
    const updateCheckContent = document.getElementById('update-check-content');
    const updateProgress = document.getElementById('update-progress');
    const updateError = document.getElementById('update-error');
    const syncBtn = document.getElementById('sync-btn');
    
    updateCheckContent.style.display = 'none';
    updateProgress.style.display = 'block';
    updateError.style.display = 'none';
    syncBtn.disabled = true;
    
    try {
        const data = await AppApi.request('/api/templates/sync', {
            method: 'POST',
        });
        
        // Success - close modal and reload templates
        closeUpdateModal();
        const message = data.added === 1 
            ? `${t('mcp_template_sync_success') || 'テンプレートを同期しました'}: ${data.added} ${t('template') || 'テンプレート'}`
            : `${t('mcp_template_sync_success') || 'テンプレートを同期しました'}: ${data.added} ${t('templates') || 'テンプレート'}`;
        showFlashMessage(message);
        
        // Hide update badge
        document.getElementById('update-badge').style.display = 'none';
        
        // Reload templates
        loadTemplates(currentTab);
        
    } catch (error) {
        updateProgress.style.display = 'none';
        updateCheckContent.style.display = 'block';
        updateError.textContent = error.message;
        updateError.style.display = 'block';
        syncBtn.disabled = false;
    }
}

function closeUpdateModal() {
    document.getElementById('update-modal').style.display = 'none';
    document.getElementById('update-details').style.display = 'block';
    document.getElementById('sync-btn').disabled = false;
}
