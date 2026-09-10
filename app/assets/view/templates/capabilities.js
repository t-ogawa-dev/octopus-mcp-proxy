// templates/capabilities.js - Template Capabilities Management Page

let template = null;
let isBuiltin = false;

function showFlashMessage(message) {
    const flashDiv = document.getElementById('flash-message');
    flashDiv.textContent = message;
    flashDiv.style.display = 'block';
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        flashDiv.style.display = 'none';
    }, 5000);
}

async function loadTemplate() {
    try {
        template = await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}`);
        
        document.getElementById('breadcrumb-template').textContent = template.name;
        document.getElementById('page-title').textContent = `${template.name} - Capabilities`;
        
        isBuiltin = template.template_type === 'builtin';
        
        // Hide new button for builtin templates
        if (isBuiltin) {
            document.getElementById('new-btn').style.display = 'none';
            
            // Show notice
            const notice = document.createElement('div');
            notice.className = 'builtin-notice';
            notice.textContent = '標準搭載テンプレートのCapabilitiesは編集できません。閲覧のみ可能です。';
            document.querySelector('.capabilities-container').insertBefore(
                notice,
                document.getElementById('capabilities-list')
            );
        }
        
        await loadCapabilities();
        
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

async function loadCapabilities() {
    const container = document.getElementById('capabilities-list');
    
    if (!template.capabilities || template.capabilities.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <p data-i18n="capability_empty">${t('capability_empty')}</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = template.capabilities.map(cap => `
        <div class="capability-card" data-capability-id="${cap.id}">
            <div class="capability-header">
                <div class="capability-info">
                    <div class="capability-name">${cap.name}</div>
                    <span class="capability-type ${cap.capability_type}">${cap.capability_type}</span>
                </div>
                <div class="capability-actions">
                    ${!isBuiltin ? `<button type="button" class="btn-small btn-secondary" data-action="edit-capability" data-i18n="button_edit">${t('button_edit')}</button>` : ''}
                    ${!isBuiltin ? `<button type="button" class="btn-delete" data-action="delete-capability" data-i18n="button_delete">${t('button_delete')}</button>` : ''}
                </div>
            </div>
            ${cap.url ? `<div class="capability-url">${AppDom.escapeHtml(cap.url)}</div>` : ''}
            ${cap.description ? `<div class="capability-description">${AppDom.escapeHtml(cap.description)}</div>` : ''}
        </div>
    `).join('');
}

function viewCapability(capabilityId) {
    window.location.href = `/mcp-templates/${TEMPLATE_ID}/capabilities/${capabilityId}`;
}

function editCapability(capabilityId, event) {
    event.stopPropagation();
    window.location.href = `/mcp-templates/${TEMPLATE_ID}/capabilities/${capabilityId}/edit`;
}

async function deleteCapability(capabilityId, event) {
    event.stopPropagation();
    
    const confirmed = await modal.confirmDelete(t('capability_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/template-capabilities/${capabilityId}`, {
            method: 'DELETE'
        });
        showFlashMessage('削除しました');
        await loadTemplate();
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Initialize
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        if (event.target.closest('[data-action="back"]')) window.history.back();
    });
    await loadTemplate();

    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        const card = actionElement?.closest('[data-capability-id]');
        if (!card) return;
        const capabilityId = card.dataset.capabilityId;
        if (actionElement.dataset.action === 'edit-capability') editCapability(capabilityId, event);
        if (actionElement.dataset.action === 'delete-capability') deleteCapability(capabilityId, event);
        if (!actionElement) viewCapability(capabilityId);
    });
    
    // Check for flash message in URL params
    const urlParams = new URLSearchParams(window.location.search);
    const message = urlParams.get('message');
    if (message) {
        showFlashMessage(decodeURIComponent(message));
        // Remove message from URL
        window.history.replaceState({}, '', `/mcp-templates/${TEMPLATE_ID}/capabilities`);
    }
})();
