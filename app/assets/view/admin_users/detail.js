// admin_users/detail.js - Admin User Detail/Edit Page
const adminUserId = Number.parseInt(window.location.pathname.split('/')[2], 10);

async function loadAdminUser() {
    const user = await AppApi.request(`/api/admin-users/${adminUserId}`);

    document.getElementById('username').value = user.username;

    const container = document.getElementById('admin-user-detail');
    container.innerHTML = `
        <div class="detail-section">
            <h2>${AppDom.escapeHtml(user.username)}</h2>
            ${!user.is_initialized ? `<p class="text-muted">${t('admin_user_pending_change_desc')}</p>` : ''}
        </div>
        <div class="detail-section">
            <table class="detail-table">
                <tr>
                    <th>${t('account_created_at')}</th>
                    <td>${new Date(user.created_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
                <tr>
                    <th>${t('account_updated_at')}</th>
                    <td>${new Date(user.updated_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
            </table>
        </div>
    `;
}

async function deleteAdminUserSelf() {
    const confirmed = await modal.confirmDelete(t('admin_user_delete_confirm'));
    if (!confirmed) return;

    try {
        await AppApi.request(`/api/admin-users/${adminUserId}`, { method: 'DELETE' });
        window.location.href = '/admin-users';
    } catch (error) {
        await modal.error(error.message || t('admin_user_delete_failed'));
    }
}

(async () => {
    await initLanguageSwitcher();
    await loadAdminUser();

    document.getElementById('edit-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData(e.target);
        const data = { username: formData.get('username').trim() };
        const password = formData.get('password');
        if (password) {
            if (password.length < 8) {
                await modal.error(t('admin_user_pw_too_short'));
                return;
            }
            data.password = password;
        }

        try {
            await AppApi.request(`/api/admin-users/${adminUserId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
            });

            await modal.success(t('admin_user_update_success'));
            document.getElementById('password').value = '';
            await loadAdminUser();
        } catch (error) {
            await modal.error(t('admin_user_update_failed') + ': ' + error.message);
        }
    });

    document.getElementById('delete-btn').addEventListener('click', deleteAdminUserSelf);
})();
