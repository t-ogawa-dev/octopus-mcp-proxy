// accounts/list.js - Accounts List Page

async function loadAccounts() {
    const allAccounts = await AppApi.request('/api/accounts');

    // システムアカウントは接続ガイドページで管理するため一覧から除外
    const accounts = allAccounts.filter(a => !a.is_system);

    const container = document.getElementById('accounts-list');
    
    if (accounts.length === 0) {
        container.innerHTML = `<div class="empty-state">${t('account_empty')}</div>`;
        return;
    }
    
    container.innerHTML = accounts.map(account => `
        <div class="list-item" data-account-id="${account.id}">
            <div class="list-item-main">
                <h3>
                    <a href="/accounts/${account.id}">${AppDom.escapeHtml(account.name)}</a>
                    ${account.is_system ? '<span class="badge badge-system" title="システムアカウント（削除不可）">&#128274; システム</span>' : ''}
                </h3>
                <div class="list-item-meta">
                    ${account.notes ? `<span class="text-muted">${AppDom.escapeHtml(account.notes.substring(0, 50))}${account.notes.length > 50 ? '...' : ''}</span>` : ''}
                    <span class="text-muted">${t('account_created')}: ${new Date(account.created_at).toLocaleDateString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</span>
                </div>
            </div>
            <div class="list-item-actions">
                ${account.is_system
                    ? ''
                    : `<button type="button" data-action="delete" class="btn btn-sm btn-danger">${t('button_delete')}</button>`
                }
            </div>
        </div>
    `).join('');
}

async function deleteAccount(id) {
    const confirmed = await modal.confirmDelete(t('account_delete_confirm'));
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/accounts/${id}`, { method: 'DELETE' });
        await loadAccounts();
    } catch (error) {
        await modal.error(t('common_error') + ': ' + error.message);
    }
}

// Initialize language and load accounts
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action="delete"]');
        const accountItem = actionElement?.closest('[data-account-id]');
        if (accountItem) deleteAccount(accountItem.dataset.accountId);
    });
    await loadAccounts();
})();

