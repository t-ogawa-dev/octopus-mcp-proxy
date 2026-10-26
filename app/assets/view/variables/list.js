/**
 * Variables一覧画面
 */

function toggleAccordion() {
    const content = document.getElementById('usage-accordion');
    const icon = document.querySelector('.accordion-icon');
    
    if (content.classList.contains('open')) {
        content.classList.remove('open');
        icon.classList.remove('rotate');
    } else {
        content.classList.add('open');
        icon.classList.add('rotate');
    }
}

async function loadVariables() {
    const variables = await AppApi.request('/api/variables');
    
    const container = document.getElementById('variables-list');
    
    if (variables.length === 0) {
        container.innerHTML = `<div class="empty-state">${t('variable_empty')}</div>`;
        return;
    }
    
    container.innerHTML = variables.map(variable => `
        <div class="list-item" data-variable-id="${variable.id}">
            <div class="list-item-main">
            <h3>${AppDom.escapeHtml(variable.name)}</h3>
                <div class="list-item-meta">
                    ${variable.is_secret ? '<span class="badge badge-secret">🔒 Secret</span>' : '<span class="badge">Public</span>'}
                    <span class="badge badge-type">${variable.value_type === 'number' ? '🔢 Number' : '📝 String'}</span>
                    <span class="text-muted">${variable.source_type === 'env' ? t('variable_env_var_name_display') : t('variable_value_label')}: <code>${AppDom.escapeHtml(variable.value)}</code></span>
                </div>
                ${variable.description ? `<p class="text-muted">${AppDom.escapeHtml(variable.description)}</p>` : ''}
            </div>
            <div class="list-item-actions">
                <a href="/variables/${variable.id}/edit" class="btn btn-sm btn-secondary">${t('button_edit')}</a>
                <button type="button" data-action="delete" class="btn btn-sm btn-danger">${t('button_delete')}</button>
            </div>
        </div>
    `).join('');
}

async function deleteVariable(id) {
    const confirmed = await modal.confirmDelete(t('variable_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/variables/${id}`, { method: 'DELETE' });
        await loadVariables();
    } catch (error) {
        await modal.error(t('common_error') + ': ' + error.message);
    }
}

// 言語初期化完了後にVariables一覧を読み込む
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        if (actionElement?.dataset.action === 'toggle-accordion') {
            toggleAccordion();
            return;
        }
        const variableItem = actionElement?.closest('[data-variable-id]');
        if (variableItem && actionElement.dataset.action === 'delete') {
            deleteVariable(variableItem.dataset.variableId);
        }
    });
    await loadVariables();
})();
