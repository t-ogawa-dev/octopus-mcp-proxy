/**
 * Resource詳細画面
 */

let currentResource = null;

async function loadResource() {
    currentResource = await AppApi.request(`/api/resources/${resourceId}`);
    
    // パンくずリスト更新
    document.getElementById('resource-name-breadcrumb').textContent = currentResource.name;
    
    const container = document.getElementById('resource-detail');
    
    // Build referencing capabilities section
    let capabilitiesSection = '';
    if (currentResource.referencing_capabilities && currentResource.referencing_capabilities.length > 0) {
        const capabilitiesList = currentResource.referencing_capabilities.map(cap => `
            <div style="padding: 12px; border: 1px solid #e5e7eb; border-radius: 6px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <strong>${AppDom.escapeHtml(cap.name)}</strong>
                    <span class="text-muted" style="margin-left: 8px; font-size: 0.875rem;">(Capability ID: ${cap.id})</span>
                </div>
                <a href="/capabilities/${cap.id}" class="btn btn-sm btn-secondary">${t('button_view_detail')}</a>
            </div>
        `).join('');
        
        capabilitiesSection = `
        <div class="detail-card">
            <h3>${t('resource_referencing_capabilities')}</h3>
            <p class="text-muted" style="margin-bottom: 12px;">
                このResourceは ${currentResource.usage_count} 個のCapabilityで使用されています。削除する前に、これらのCapabilityを削除するか、別のResourceに変更してください。
            </p>
            ${capabilitiesList}
        </div>`;
    } else {
        capabilitiesSection = `
        <div class="detail-card">
            <h3>${t('resource_referencing_capabilities')}</h3>
            <p class="text-muted">${t('resource_no_capabilities')}</p>
        </div>`;
    }
    
    container.innerHTML = `
        <div class="page-title">
            <div class="page-header-responsive">
                <div class="page-header-text">
                        <h2>${AppDom.escapeHtml(currentResource.name)}</h2>
                    <p>${AppDom.escapeHtml(currentResource.description || t('resource_detail_desc'))}</p>
                </div>
                <div class="page-header-actions">
                    <a href="/resources/${currentResource.id}/edit" class="btn btn-primary">${t('button_edit')}</a>
                    <button type="button" data-action="delete" class="btn btn-danger" ${currentResource.usage_count > 0 ? 'disabled title="このResourceは使用中のため削除できません"' : ''}>${t('button_delete')}</button>
                </div>
            </div>
        </div>
        
        <div class="detail-card">
            <h3>${t('resource_basic_info')}</h3>
            <table class="detail-table">
                <tr>
                    <th>${t('resource_id_label')}</th>
                        <td><code style="font-size: 0.9em;">${AppDom.escapeHtml(currentResource.resource_id)}</code></td>
                </tr>
                <tr>
                    <th>${t('resource_uri_label')}</th>
                        <td><code style="font-size: 0.9em; word-break: break-all;">${AppDom.escapeHtml(currentResource.uri)}</code></td>
                </tr>
                <tr>
                    <th>${t('resource_mime_type_label')}</th>
                        <td><span class="badge badge-mime">${AppDom.escapeHtml(currentResource.mime_type)}</span></td>
                </tr>
                <tr>
                    <th>${t('status')}</th>
                    <td>
                        <span class="badge" style="padding: 4px 12px; border-radius: 4px; background-color: ${currentResource.is_enabled ? '#d1fae5' : '#fee2e2'}; color: ${currentResource.is_enabled ? '#065f46' : '#991b1b'};">
                            ${currentResource.is_enabled ? t('status_enabled') : t('status_disabled')}
                        </span>
                    </td>
                </tr>
                <tr>
                    <th>${t('resource_created_at')}</th>
                    <td>${new Date(currentResource.created_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
                <tr>
                    <th>${t('resource_updated_at')}</th>
                    <td>${new Date(currentResource.updated_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
            </table>
        </div>
        
        ${capabilitiesSection}
        
        <div class="detail-card">
            <h3>${t('resource_content_label')}</h3>
            <pre class="code-block" style="white-space: pre-wrap; max-height: 500px; overflow-y: auto;">${escapeHtml(currentResource.content)}</pre>
        </div>
    `;
}

async function deleteResource() {
    const confirmed = await modal.confirmDelete(t('resource_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/resources/${resourceId}`, {
            method: 'DELETE'
        });
        await modal.success(t('resource_deleted_success'));
        window.location.href = '/resources';
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

// Initialize
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const deleteButton = event.target.closest('[data-action="delete"]');
        if (deleteButton && !deleteButton.disabled) deleteResource();
    });
    await loadResource();
})();
