// accounts/detail.js - Account Detail Page
const accountId = Number.parseInt(window.location.pathname.split('/')[2], 10);
let currentAccount = null;

async function loadAccount() {
    const account = await AppApi.request(`/api/accounts/${accountId}`);
    currentAccount = account;
    
    document.getElementById('name').value = account.name;
    document.getElementById('notes').value = account.notes || '';

    // System accounts: lock the name field
    const nameInput = document.getElementById('name');
    if (account.is_system) {
        nameInput.setAttribute('readonly', 'readonly');
        nameInput.title = 'システムアカウントのため名前は変更できません';
    } else {
        nameInput.removeAttribute('readonly');
    }
    
    const container = document.getElementById('account-detail');
    const systemBadge = account.is_system
        ? '<span class="badge badge-system" title="システムアカウント（削除不可）">&#128274; システム</span>'
        : '';
    container.innerHTML = `
        <div class="detail-section">
            <h2>${AppDom.escapeHtml(account.name)} ${systemBadge}</h2>
            ${account.is_system ? '<p class="text-muted">このアカウントは Admin MCP エンドポイントの認証に使用されます。削除できません。</p>' : ''}
        </div>
        
        <div class="detail-section">
            <h3>${t('account_bearer_token')}</h3>
            <div class="token-display" style="display: flex; gap: 10px; align-items: center;">
                <code style="flex: 1; padding: 10px; background: #f5f5f5; border-radius: 4px; overflow-x: auto;">${AppDom.escapeHtml(account.bearer_token)}</code>
                <button type="button" data-action="copy-token" class="btn btn-sm btn-secondary">${t('account_copy_token')}</button>
                <button type="button" data-action="regenerate-token" class="btn btn-sm btn-warning">${t('account_regenerate_token')}</button>
            </div>
            ${account.is_system ? '<small class="text-muted">トークンを再発行すると MCP クライアント側の設定も更新が必要です。</small>' : ''}
        </div>
        
        ${account.notes ? `
        <div class="detail-section">
            <h3>${t('account_notes_label')}</h3>
            <p style="white-space: pre-wrap;">${AppDom.escapeHtml(account.notes)}</p>
        </div>
        ` : ''}
        
        <div class="detail-section">
            <table class="detail-table">
                <tr>
                    <th>${t('account_created_at')}</th>
                    <td>${new Date(account.created_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
                <tr>
                    <th>${t("account_updated_at")}</th>
                    <td>${new Date(account.updated_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
            </table>
        </div>
    `;
}

async function copyToken() {
    await navigator.clipboard.writeText(currentAccount.bearer_token);
    await modal.success(t('account_token_copied'));
}

async function regenerateToken() {
    const confirmed = await modal.confirm(
        t('account_regenerate_confirm'),
        null,
        {
            confirmText: t('common_confirm') || 'OK',
            confirmClass: 'btn-warning'
        }
    );
    if (!confirmed) return;
    
    try {
        await AppApi.request(`/api/accounts/${accountId}/regenerate_token`, { method: 'POST' });
        await modal.success(t('account_token_regenerated'));
        await loadAccount();
    } catch (error) {
        console.error('Error regenerating token:', error);
        await modal.error('トークンの再発行に失敗しました');
    }
}

// Initialize and setup
(async () => {
    await initLanguageSwitcher();
    await loadAccount();
    
    // Setup form submit handler
    document.getElementById('edit-form').addEventListener('submit', async (e) => {
        e.preventDefault();

        try {
            const formData = new FormData(e.target);
            const data = {
                notes: formData.get('notes')
            };

            if (!currentAccount || !currentAccount.is_system) {
                data.name = formData.get('name');
            }

            await AppApi.request(`/api/accounts/${accountId}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            await modal.success(t('account_update_success'));
            await loadAccount();
        } catch (error) {
            await modal.error(t('account_update_failed') + ': ' + error.message);
        }
    });

    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'copy-token') copyToken();
        if (action === 'regenerate-token') regenerateToken();
    });
})();

