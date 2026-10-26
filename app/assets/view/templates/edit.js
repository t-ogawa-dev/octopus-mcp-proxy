// templates/edit.js - Template Edit Page

function addHeader(key = '', value = '') {
    const container = document.getElementById('headers-container');
    const row = document.createElement('div');
    row.className = 'header-row';
    row.innerHTML = `
        <input type="text" placeholder="Header Name (例: Authorization)" class="header-key" value="${key}">
        <input type="text" placeholder="Header Value (例: Bearer {token})" class="header-value" value="${value}">
        <button type="button" data-action="remove-header">削除</button>
    `;
    container.appendChild(row);
}

function getHeaders() {
    const headers = {};
    const rows = document.querySelectorAll('.header-row');
    rows.forEach(row => {
        const key = row.querySelector('.header-key').value.trim();
        const value = row.querySelector('.header-value').value.trim();
        if (key && value) {
            headers[key] = value;
        }
    });
    return headers;
}

async function loadTemplate() {
    try {
        const template = await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}`);
        
        // Populate form
        document.getElementById('name').value = template.name || '';
        document.getElementById('icon').value = template.icon || '';
        document.getElementById('category').value = template.category || '';
        document.getElementById('description').value = template.description || '';
        document.getElementById('service_type').value = template.service_type || 'api';
        document.getElementById('breadcrumb-name').textContent = template.name;
        
        // Load headers
        let headers = {};
        if (template.common_headers) {
            // Check if it's already an object or needs parsing
            headers = typeof template.common_headers === 'string' 
                ? JSON.parse(template.common_headers) 
                : template.common_headers;
        }
        Object.entries(headers).forEach(([key, value]) => {
            addHeader(key, value);
        });
        
        // If no headers, add one empty row
        if (Object.keys(headers).length === 0) {
            addHeader();
        }
        
    } catch (e) {
        await modal.error(t('common_error') + ': ' + e.message);
    }
}

document.getElementById('template-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        name: document.getElementById('name').value.trim(),
        icon: document.getElementById('icon').value.trim() || '📦',
        category: document.getElementById('category').value.trim() || 'General',
        description: document.getElementById('description').value.trim(),
        service_type: document.getElementById('service_type').value,
        common_headers: getHeaders()
    };
    
    try {
        await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}`, {
            method: 'PUT',
            body: JSON.stringify(formData)
        });
        window.location.href = `/templates?message=${encodeURIComponent('更新しました')}`;
    } catch (e) {
        await modal.error('更新に失敗しました: ' + e.message);
    }
});

// Initialize
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'remove-header') {
            event.target.closest('.header-row')?.remove();
        }
        if (action === 'add-header') addHeader();
        if (action === 'back') window.history.back();
    });
    await loadTemplate();
})();
