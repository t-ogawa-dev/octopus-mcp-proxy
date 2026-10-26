// templates/capability_new.js - Capability Creation Page

let headers = [];
let params = [];

function addHeader() {
    const container = document.getElementById('headers-container');
    const index = headers.length;
    
    const row = document.createElement('div');
    row.className = 'header-row';
    row.innerHTML = `
        <input type="text" placeholder="${t('capability_header_key') || 'キー'}" data-header-key="${index}">
        <input type="text" placeholder="${t('capability_header_value') || '値'}" data-header-value="${index}">
        <button type="button" data-action="remove-header" data-index="${index}">${t('button_remove') || '削除'}</button>
    `;
    
    container.appendChild(row);
    headers.push({key: '', value: ''});
}

function removeHeader(index) {
    const container = document.getElementById('headers-container');
    const rows = container.querySelectorAll('.header-row');
    rows[index].remove();
    headers.splice(index, 1);
    
    // Re-render to fix indices
    renderHeaders();
}

function renderHeaders() {
    const container = document.getElementById('headers-container');
    container.innerHTML = '';
    
    headers.forEach((header, index) => {
        const row = document.createElement('div');
        row.className = 'header-row';
        row.innerHTML = `
            <input type="text" placeholder="${t('capability_header_key') || 'キー'}" data-header-key="${index}" value="${header.key}">
            <input type="text" placeholder="${t('capability_header_value') || '値'}" data-header-value="${index}" value="${header.value}">
            <button type="button" data-action="remove-header" data-index="${index}">${t('button_remove') || '削除'}</button>
        `;
        container.appendChild(row);
    });
}

function addParam() {
    const container = document.getElementById('params-container');
    const index = params.length;
    
    const row = document.createElement('div');
    row.className = 'param-row';
    row.innerHTML = `
        <input type="text" placeholder="${t('capability_param_key') || 'キー'}" data-param-key="${index}">
        <input type="text" placeholder="${t('capability_param_value') || '値'}" data-param-value="${index}">
        <button type="button" data-action="remove-param" data-index="${index}">${t('button_remove') || '削除'}</button>
    `;
    
    container.appendChild(row);
    params.push({key: '', value: ''});
}

function removeParam(index) {
    const container = document.getElementById('params-container');
    const rows = container.querySelectorAll('.param-row');
    rows[index].remove();
    params.splice(index, 1);
    
    // Re-render to fix indices
    renderParams();
}

function renderParams() {
    const container = document.getElementById('params-container');
    container.innerHTML = '';
    
    params.forEach((param, index) => {
        const row = document.createElement('div');
        row.className = 'param-row';
        row.innerHTML = `
            <input type="text" placeholder="${t('capability_param_key') || 'キー'}" data-param-key="${index}" value="${param.key}">
            <input type="text" placeholder="${t('capability_param_value') || '値'}" data-param-value="${index}" value="${param.value}">
            <button type="button" data-action="remove-param" data-index="${index}">${t('button_remove') || '削除'}</button>
        `;
        container.appendChild(row);
    });
}

// Form submission
document.getElementById('capability-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // Collect header data
    const headerObj = {};
    document.querySelectorAll('[data-header-key]').forEach((input, index) => {
        const key = input.value.trim();
        const value = document.querySelector(`[data-header-value="${index}"]`).value.trim();
        if (key) {
            headerObj[key] = value;
        }
    });
    
    // Collect param data
    const paramObj = {};
    document.querySelectorAll('[data-param-key]').forEach((input, index) => {
        const key = input.value.trim();
        const value = document.querySelector(`[data-param-value="${index}"]`).value.trim();
        if (key) {
            paramObj[key] = value;
        }
    });
    
    const formData = {
        name: document.getElementById('name').value.trim(),
        capability_type: document.getElementById('capability_type').value,
        url: document.getElementById('url').value.trim(),
        description: document.getElementById('description').value.trim(),
        headers: headerObj,
        body_params: paramObj,
        template_content: document.getElementById('template_content').value.trim()
    };
    
    try {
        await AppApi.request(`/api/mcp-templates/${TEMPLATE_ID}/capabilities`, {
            method: 'POST',
            body: JSON.stringify(formData)
        });
        window.location.href = `/mcp-templates/${TEMPLATE_ID}/capabilities?message=${encodeURIComponent(t('capability_registered'))}`;
    } catch (e) {
        await modal.error(t('capability_register_failed') + ': ' + e.message);
    }
});

// Initialize
(async () => {
    await initLanguageSwitcher();

    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        if (!actionElement) return;
        const index = Number(actionElement.dataset.index);
        if (actionElement.dataset.action === 'remove-header') removeHeader(index);
        if (actionElement.dataset.action === 'remove-param') removeParam(index);
        if (actionElement.dataset.action === 'add-header') addHeader();
        if (actionElement.dataset.action === 'add-param') addParam();
        if (actionElement.dataset.action === 'back') window.history.back();
    });
    
    // Handle capability type change to show/hide template content section
    const capabilityTypeSelect = document.getElementById('capability_type');
    const templateSection = document.getElementById('template-section');
    
    function toggleTemplateSection() {
        if (capabilityTypeSelect.value === 'prompt') {
            templateSection.style.display = 'block';
        } else {
            templateSection.style.display = 'none';
        }
    }
    
    // Initial state
    toggleTemplateSection();
    
    // Listen for changes
    capabilityTypeSelect.addEventListener('change', toggleTemplateSection);
})();
