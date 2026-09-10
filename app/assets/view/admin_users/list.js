// admin_users/list.js - Admin Users (Web Login Accounts) List Page

async function loadAdminUsers() {
    const users = await AppApi.request('/api/admin-users');

    const container = document.getElementById('admin-users-list');

    if (users.length === 0) {
        container.innerHTML = `<div class="empty-state">${t('admin_user_empty')}</div>`;
        return;
    }

    container.innerHTML = users.map(user => `
        <div class="list-item" data-user-id="${user.id}">
            <div class="list-item-main">
            <h3><a href="/admin-users/${user.id}">${AppDom.escapeHtml(user.username)}</a></h3>
                <div class="list-item-meta">
                    <span class="text-muted">${t('admin_user_created')}: ${new Date(user.created_at).toLocaleDateString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</span>
                    ${!user.is_initialized ? `<span class="text-muted">（${t('admin_user_pending_change')}）</span>` : ''}
                </div>
            </div>
            <div class="list-item-actions">
                <button type="button" data-action="delete" class="btn btn-sm btn-danger">${t('button_delete')}</button>
            </div>
        </div>
    `).join('');
}

async function deleteAdminUser(id) {
    const confirmed = await modal.confirmDelete(t('admin_user_delete_confirm'));
    if (!confirmed) return;

    try {
        await AppApi.request(`/api/admin-users/${id}`, { method: 'DELETE' });
        await loadAdminUsers();
    } catch (error) {
        await modal.error(error.message || t('admin_user_delete_failed'));
    }
}

// Initialize language and load admin users
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action="delete"]');
        const userItem = actionElement?.closest('[data-user-id]');
        if (userItem) deleteAdminUser(userItem.dataset.userId);
    });
    await loadAdminUsers();
})();
