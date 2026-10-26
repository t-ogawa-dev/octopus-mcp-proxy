// capabilities/edit.js - Capability Edit Page
const capabilityId = Number.parseInt(window.location.pathname.split('/')[2], 10);
let headerIndex = 0;
let bodyIndex = 0;
let currentAccessControl = 'public'; // デフォルトはpublic（制限なし）
let baseUrl = ''; // App's base URL

// Update URL preview
function updateUrlPreview() {
    const urlInput = document.getElementById('url');
    const urlPreviewBase = document.getElementById('url-preview-base');
    const urlPreviewPath = document.getElementById('url-preview-path');
    
    const inputPath = urlInput.value.trim();
    
    if (baseUrl) {
        // Show baseUrl + inputPath (or placeholder if empty)
        const separator = baseUrl.endsWith('/') || inputPath.startsWith('/') ? '' : '/';
        urlPreviewBase.textContent = baseUrl;
        
        if (inputPath && !inputPath.startsWith('http')) {
            urlPreviewPath.textContent = separator + inputPath;
        } else if (!inputPath) {
            urlPreviewPath.textContent = separator + '<input path>';
        } else {
            // Absolute URL entered
            urlPreviewPath.textContent = '';
        }
    } else {
        // No base URL - clear preview
        urlPreviewBase.textContent = '';
        urlPreviewPath.textContent = '';
    }
}

// Update access control UI
function updateAccessControlUI(isRestricted) {
    const permissionsSection = document.getElementById('permissions-section');
    
    if (isRestricted) {
        permissionsSection.style.display = 'block';
    } else {
        permissionsSection.style.display = 'none';
    }
}

// Toggle resource source selection (existing vs new) - for edit page
window.toggleResourceSourceEdit = function() {
    const sourceValue = document.querySelector('input[name="resource_source"]:checked')?.value || 'existing';
    const existingSection = document.getElementById('existing-resource-section-edit');
    const newSection = document.getElementById('new-resource-section-edit');
    
    if (sourceValue === 'existing') {
        // Show existing resource selection, hide new resource fields
        if (existingSection) existingSection.style.display = 'block';
        if (newSection) newSection.style.display = 'none';
    } else {
        // Hide existing resource selection, show new resource fields
        if (existingSection) existingSection.style.display = 'none';
        if (newSection) newSection.style.display = 'block';
    }
};

// Toggle resource input type (text vs file) - for edit page
function toggleResourceInputTypeEdit() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    const textInput = document.getElementById('resource-text-input-edit');
    const fileInput = document.getElementById('resource-file-input-edit');
    
    if (inputType === 'file') {
        if (textInput) textInput.style.display = 'none';
        if (fileInput) fileInput.style.display = 'block';
    } else {
        if (textInput) textInput.style.display = 'block';
        if (fileInput) fileInput.style.display = 'none';
    }
}

// ファイルアップロード処理 - for edit page
let uploadedResourceContentEdit = null;
function handleResourceFileUploadEdit(file) {
    // 引数がない場合はinputから取得
    if (!file) {
        const fileInput = document.getElementById('resource_file_edit');
        file = fileInput?.files[0];
    }
    
    if (!file) return;
    
    // ファイルサイズチェック (1MB)
    if (file.size > 1024 * 1024) {
        modal.error(t('resource_file_too_large') || 'ファイルサイズが1MBを超えています');
        const fileInput = document.getElementById('resource_file_edit');
        if (fileInput) fileInput.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        uploadedResourceContentEdit = e.target.result;
        
        // プレビュー表示
        const previewDiv = document.getElementById('resource-file-preview-edit');
        const fileNameSpan = document.getElementById('resource-file-name-edit');
        const fileSizeSpan = document.getElementById('resource-file-size-edit');
        
        if (previewDiv) previewDiv.style.display = 'block';
        if (fileNameSpan) fileNameSpan.textContent = file.name;
        if (fileSizeSpan) fileSizeSpan.textContent = `${(file.size / 1024).toFixed(1)} KB`;
        
        // MIMEタイプ自動設定
        const mimeTypeSelect = document.getElementById('resource_mime_type');
        if (mimeTypeSelect) {
            const ext = file.name.split('.').pop().toLowerCase();
            const mimeMap = {
                'txt': 'text/plain',
                'md': 'text/markdown',
                'json': 'application/json',
                'html': 'text/html',
                'csv': 'text/csv',
                'xml': 'application/xml',
                'yaml': 'text/yaml',
                'yml': 'text/yaml'
            };
            if (mimeMap[ext]) {
                mimeTypeSelect.value = mimeMap[ext];
            }
        }
        
        generateResourcePreviewEdit();
    };
    reader.readAsText(file);
}

// ファイルクリア - for edit page
function clearResourceFileEdit() {
    const fileInput = document.getElementById('resource_file_edit');
    const previewDiv = document.getElementById('resource-file-preview-edit');
    
    if (fileInput) fileInput.value = '';
    if (previewDiv) previewDiv.style.display = 'none';
    uploadedResourceContentEdit = null;
    generateResourcePreviewEdit();
}

function setupStaticEventListeners() {
    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        if (!actionElement) return;

        const action = actionElement.dataset.action;
        if (action === 'remove-row') actionElement.closest('.key-value-row, .llm-param-row')?.remove();
        if (action === 'toggle-enum') toggleEnumField(actionElement);
        if (action === 'toggle-tree') toggleTreeNode(actionElement.dataset.nodeId);
        if (action === 'remove-tree') removeTreeNode(actionElement.dataset.nodeId);
        if (action === 'add-tree-child') addChildToTreeNode(actionElement.dataset.nodeId);
        if (action === 'add-tree-array-property') addArrayItemPropertyNode(actionElement.dataset.nodeId);
        if (action === 'add-header') addHeaderRow();
        if (action === 'add-fixed-param') addFixedParamRow();
        if (action === 'add-llm-param') addLlmParamRow();
        if (action === 'add-fixed-param-post') addFixedParamPostRow(null, 0);
        if (action === 'add-llm-param-tree') addLlmParamTreeRow(null, 0);
        if (action === 'move-enabled') moveToEnabled();
        if (action === 'move-all-enabled') moveAllToEnabled();
        if (action === 'move-disabled') moveToDisabled();
        if (action === 'move-all-disabled') moveAllToDisabled();
        if (action === 'select-resource-file') document.getElementById('resource_file_edit').click();
        if (action === 'clear-resource-file') clearResourceFileEdit();
    });

    document.addEventListener('change', (event) => {
        const action = event.target.dataset.action;
        if (action === 'toggle-body-type') toggleBodyType();
        if (action === 'toggle-resource-source') window.toggleResourceSourceEdit();
        if (action === 'toggle-resource-input') toggleResourceInputTypeEdit();
        if (action === 'resource-file-input' && event.target.files[0]) {
            handleResourceFileUploadEdit(event.target.files[0]);
        }
        if (action === 'tree-type') handleTreeTypeChange(event.target.dataset.nodeId);
        if (action === 'tree-array-type') handleArrayItemsTypeChange(event.target.dataset.nodeId);
    });

    document.addEventListener('input', (event) => {
        if (event.target.dataset.action === 'prompt-preview-input') generatePromptPreviewEdit();
        if (event.target.dataset.action === 'resource-preview-input') generateResourcePreviewEdit();
    });
}

// リソースプレビュー生成 - for edit page
function generateResourcePreviewEdit() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    const previewOutput = document.getElementById('resource-preview-output-edit');
    
    if (!previewOutput) return;
    
    let content = '';
    if (inputType === 'file' && uploadedResourceContentEdit) {
        content = uploadedResourceContentEdit;
    } else {
        content = document.getElementById('resource_content')?.value || '';
    }
    
    if (content) {
        // 最大500文字でトランケート
        if (content.length > 500) {
            previewOutput.textContent = content.substring(0, 500) + '\n...(省略)';
        } else {
            previewOutput.textContent = content;
        }
    } else {
        previewOutput.textContent = t('resource_preview_empty') || '(空のリソース)';
    }
}

// リソースコンテンツを取得（保存時に使用） - for edit page
function getResourceContentEdit() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    
    if (inputType === 'file' && uploadedResourceContentEdit) {
        return uploadedResourceContentEdit;
    }
    return document.getElementById('resource_content')?.value || '';
}

// Load account permissions
async function loadPermissions() {
    const data = await AppApi.request(`/api/capabilities/${capabilityId}/permissions`);
    
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    
    enabledSelect.innerHTML = data.enabled.map(account => 
        `<option value="${Number(account.id)}">${AppDom.escapeHtml(account.name)}</option>`
    ).join('');
    
    disabledSelect.innerHTML = data.disabled.map(account => 
        `<option value="${Number(account.id)}">${AppDom.escapeHtml(account.name)}</option>`
    ).join('');
    
    updateCounts();
}

// Save permissions
async function savePermissions() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const enabledAccountIds = Array.from(enabledSelect.options).map(opt => parseInt(opt.value));
    
    await AppApi.request(`/api/capabilities/${capabilityId}/permissions`, {
        method: 'POST',
        body: JSON.stringify({ account_ids: enabledAccountIds })
    });
}

function addHeaderRow(key = '', value = '', isReadOnly = false) {
    const container = document.getElementById('headers-container');
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    
    const readOnlyStyle = isReadOnly ? 'background-color: #f5f5f5; cursor: not-allowed;' : '';
    const readOnlyAttr = isReadOnly ? 'readonly' : '';
    
    row.innerHTML = `
        <input type="text" placeholder="${t('form_key_placeholder')}" value="${AppDom.escapeHtml(key)}" ${readOnlyAttr}
               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px; ${readOnlyStyle}">
        <input type="text" placeholder="${t('form_value_placeholder')}" value="${AppDom.escapeHtml(value)}" ${readOnlyAttr}
               style="flex: 2; padding: 8px; border: 1px solid #ddd; border-radius: 4px; ${readOnlyStyle}">
        ${!isReadOnly ? `<button type="button" data-action="remove-row" class="btn btn-sm btn-danger">${t('button_delete')}</button>` : ''}
    `;
    container.appendChild(row);
    headerIndex++;
}

// Fixed Parameters (key-value for query strings or fixed body params)
function addFixedParamRow(key = '', value = '', isReadOnly = false) {
    const container = document.getElementById('fixed-params-container');
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    
    const readOnlyStyle = isReadOnly ? 'background-color: #f5f5f5; cursor: not-allowed;' : '';
    const readOnlyAttr = isReadOnly ? 'readonly' : '';
    
    row.innerHTML = `
        <input type="text" placeholder="Key" value="${AppDom.escapeHtml(key)}" ${readOnlyAttr}
               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px; ${readOnlyStyle}">
        <input type="text" placeholder="Value (or {{VARIABLE}})" value="${AppDom.escapeHtml(value)}" ${readOnlyAttr}
               style="flex: 2; padding: 8px; border: 1px solid #ddd; border-radius: 4px; ${readOnlyStyle}">
        ${!isReadOnly ? `<button type="button" data-action="remove-row" class="btn btn-sm btn-danger">${t('button_delete')}</button>` : ''}
    `;
    container.appendChild(row);
}

// LLM Parameters (JSON Schema definition)
let llmParamIndex = 0;
function addLlmParamRow(paramData = null, isReadOnly = false) {
    const container = document.getElementById('llm-params-container');
    const index = llmParamIndex++;
    
    const data = paramData || {
        name: '',
        type: 'string',
        description: '',
        required: false,
        enum: '',
        default: ''
    };
    
    const readOnlyStyle = isReadOnly ? 'background-color: #f5f5f5; cursor: not-allowed;' : '';
    const readOnlyAttr = isReadOnly ? 'readonly disabled' : '';
    
    const row = document.createElement('div');
    row.className = 'llm-param-row';
    row.setAttribute('data-index', index);
    row.style.cssText = 'border: 1px solid #cce5ff; border-radius: 4px; padding: 15px; margin-bottom: 15px; background: white;';
    row.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <div>
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">パラメータ名 *</label>
                <input type="text" class="llm-param-name" value="${AppDom.escapeHtml(data.name)}" placeholder="parameter_name" ${readOnlyAttr}
                       style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; ${readOnlyStyle}">
            </div>
            <div>
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">型 *</label>
                <select class="llm-param-type" ${readOnlyAttr} data-action="toggle-enum" style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; ${readOnlyStyle}">
                    <option value="string" ${data.type === 'string' ? 'selected' : ''}>string</option>
                    <option value="number" ${data.type === 'number' ? 'selected' : ''}>number</option>
                    <option value="integer" ${data.type === 'integer' ? 'selected' : ''}>integer</option>
                    <option value="boolean" ${data.type === 'boolean' ? 'selected' : ''}>boolean</option>
                    <option value="enum" ${data.type === 'enum' ? 'selected' : ''}>enum (選択肢)</option>
                </select>
                <small style="display: block; color: #6c757d; font-size: 0.75rem; margin-top: 2px;">※ GETメソッドではシンプルな型のみ使用可能</small>
            </div>
        </div>
        <div style="margin-bottom: 10px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">説明 (LLMに表示)</label>
            <input type="text" class="llm-param-description" value="${AppDom.escapeHtml(data.description)}" placeholder="このパラメータの説明" ${readOnlyAttr}
                   style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; ${readOnlyStyle}">
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <div>
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">デフォルト値</label>
                <input type="text" class="llm-param-default" value="${AppDom.escapeHtml(data.default)}" placeholder="${data.type === 'enum' ? 'Enum値の1つを選択' : 'デフォルト値'}" ${readOnlyAttr}
                       style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; ${readOnlyStyle}">
                <small class="default-hint" style="display: ${data.type === 'enum' ? 'block' : 'none'}; color: #856404; font-size: 0.75rem; margin-top: 2px;">⚠️ Enum値の中から選んでください</small>
            </div>
            <div class="enum-field-container" style="display: ${data.type === 'enum' ? 'block' : 'none'};">
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">Enum値 (カンマ区切り) *</label>
                <input type="text" class="llm-param-enum" value="${AppDom.escapeHtml(data.enum)}" placeholder="option1,option2,option3" ${readOnlyAttr}
                       style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem; ${readOnlyStyle}">
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.9rem; cursor: ${isReadOnly ? 'not-allowed' : 'pointer'};">
                <input type="checkbox" class="llm-param-required" ${data.required ? 'checked' : ''} ${readOnlyAttr}
                       style="width: 16px; height: 16px; cursor: ${isReadOnly ? 'not-allowed' : 'pointer'};">
                <span style="font-weight: 600; color: #333;">必須パラメータ</span>
            </label>
            ${!isReadOnly ? `<button type="button" data-action="remove-row" class="btn btn-sm btn-danger">削除</button>` : ''}
        </div>
    `;
    container.appendChild(row);
}

// JSON validation and formatting
function validateJson() {
    const textarea = document.getElementById('body_json');
    const errorDiv = document.getElementById('json-validation-error');
    const jsonText = textarea.value.trim();
    
    if (!jsonText) {
        errorDiv.style.display = 'none';
        return;
    }
    
    try {
        // Replace {{VARIABLE}} placeholders with dummy values for validation
        const testJson = jsonText.replace(/\{\{[^}]+\}\}/g, '"__VARIABLE__"');
        JSON.parse(testJson);
        errorDiv.style.display = 'block';
        errorDiv.style.color = '#28a745';
        errorDiv.innerHTML = '✓ ' + t('json_valid');
        setTimeout(() => {
            errorDiv.style.display = 'none';
        }, 3000);
    } catch (e) {
        errorDiv.style.display = 'block';
        errorDiv.style.color = '#dc3545';
        errorDiv.innerHTML = '✗ ' + t('json_invalid') + ': ' + e.message;
    }
}

function formatJson() {
    const textarea = document.getElementById('body_json');
    const errorDiv = document.getElementById('json-validation-error');
    const jsonText = textarea.value.trim();
    
    if (!jsonText) {
        return;
    }
    
    try {
        // Extract variables before formatting
        const variables = [];
        const testJson = jsonText.replace(/\{\{([^}]+)\}\}/g, (match, varName) => {
            variables.push({ match, varName });
            return '"__VARIABLE_' + (variables.length - 1) + '__"';
        });
        
        const parsed = JSON.parse(testJson);
        let formatted = JSON.stringify(parsed, null, 2);
        
        // Restore variables in formatted JSON
        variables.forEach((v, index) => {
            formatted = formatted.replace('"__VARIABLE_' + index + '__"', v.match);
        });
        
        textarea.value = formatted;
        errorDiv.style.display = 'none';
    } catch (e) {
        errorDiv.style.display = 'block';
        errorDiv.style.color = '#dc3545';
        errorDiv.innerHTML = '✗ ' + t('json_invalid') + ': ' + e.message;
    }
}

// ============================================
// POST Method: Hierarchical Tree Editor
// ============================================

// Fixed Parameters for POST
let fixedParamPostIndex = 0;
// 固定パラメータ(POST用・階層対応)
function addFixedParamPostRow(containerOrParent = null, depth = 0, paramData = null, isReadOnly = false) {
    // 階層エディタを使用
    return addLlmParamTreeRow(containerOrParent || document.getElementById('fixed-params-post-container'), depth, paramData, isReadOnly);
}

// Tree-based hierarchical editor for LLM Parameters (POST)
let treeNodeIdCounter = 0;

function addLlmParamTreeRow(containerOrParent = null, depth = 0, paramData = null) {
    const nodeId = treeNodeIdCounter++;
    
    // containerOrParentが配列コンテナ要素かどうかをチェック
    let container;
    if (!containerOrParent) {
        // ルート要素の場合
        container = document.getElementById('llm-params-tree-container');
    } else if (containerOrParent.classList && (containerOrParent.classList.contains('tree-children') || containerOrParent.classList.contains('tree-array-item-properties'))) {
        // 既にコンテナ要素が渡されている場合
        container = containerOrParent;
    } else if (containerOrParent.id === 'llm-params-tree-container' || containerOrParent.id === 'fixed-params-post-container') {
        // ルートコンテナが直接渡されている場合
        container = containerOrParent;
    } else if (containerOrParent.classList && containerOrParent.classList.contains('tree-node')) {
        // 親ノードが渡されている場合（後方互換性）
        container = containerOrParent.querySelector('.tree-children');
    } else {
        // その他の場合（旧コードとの互換性）
        container = containerOrParent;
    }
    
    if (!container) {
        console.error('Container not found for:', containerOrParent);
        return null;
    }
    
    // Check if this is for fixed parameters (not LLM parameters)
    const isFixedParam = container.id === 'fixed-params-post-container' || 
                         container.closest('#fixed-params-post-container') !== null;
    
    const data = paramData || {
        name: '',
        type: 'string',
        description: '',
        required: false,
        enum: '',
        default: '',
        children: [],
        itemsType: 'string'
    };
    
    const node = document.createElement('div');
    node.className = 'tree-node';
    node.setAttribute('data-node-id', nodeId);
    node.setAttribute('data-depth', depth);
    node.style.cssText = `margin-left: ${depth * 20}px; border: 1px solid #cce5ff; border-radius: 4px; padding: 10px; margin-bottom: 10px; background: white;`;
    
    const isExpandable = data.type === 'object';
    const hasChildren = data.children && data.children.length > 0;
    const expandIcon = isExpandable ? (hasChildren ? '▼' : '▶') : '';
    
    node.innerHTML = `
        <div class="tree-node-header" style="display: flex; gap: 10px; align-items: center; margin-bottom: 8px;">
            <button type="button" class="expand-btn" data-action="toggle-tree" data-node-id="${nodeId}"
                    style="width: 24px; height: 24px; border: none; background: #f0f0f0; border-radius: 4px; cursor: pointer; font-size: 0.8rem; display: ${isExpandable ? 'block' : 'none'};">
                ${expandIcon}
            </button>
            <div style="flex: 1; display: grid; grid-template-columns: 1fr 1fr 2fr auto; gap: 8px; align-items: center;">
                <div style="display: flex; align-items: center;">
                    <input type="text" class="tree-param-name" placeholder="param_name"
                           style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                </div>
                <div style="display: flex; align-items: center;">
                    <select class="tree-param-type" data-action="tree-type" data-node-id="${nodeId}"
                            style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                        <option value="string" ${data.type === 'string' ? 'selected' : ''}>string</option>
                        <option value="number" ${data.type === 'number' ? 'selected' : ''}>number</option>
                        <option value="integer" ${data.type === 'integer' ? 'selected' : ''}>integer</option>
                        <option value="boolean" ${data.type === 'boolean' ? 'selected' : ''}>boolean</option>
                        ${!isFixedParam ? `<option value="enum" ${data.type === 'enum' ? 'selected' : ''}>enum</option>` : ''}
                        <option value="object" ${data.type === 'object' ? 'selected' : ''}>object</option>
                        <option value="array" ${data.type === 'array' ? 'selected' : ''}>array</option>
                    </select>
                </div>
                <div style="display: ${isFixedParam ? 'none' : 'flex'}; align-items: center;">
                    <input type="text" class="tree-param-description" placeholder="説明"
                           style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                </div>
                <div style="display: flex; gap: 8px; align-items: center; justify-content: center;">
                    <label style="display: ${isFixedParam ? 'none' : 'flex'}; align-items: center; gap: 4px; cursor: pointer; font-size: 0.85rem; white-space: nowrap; margin-bottom: 0;">
                        <input type="checkbox" class="tree-param-required" ${data.required ? 'checked' : ''}
                               style="width: 16px; height: 16px; margin: 0;">
                        <span style="color: #333;">必須</span>
                    </label>
                    <button type="button" data-action="remove-tree" data-node-id="${nodeId}" class="btn btn-sm btn-danger" style="padding: 4px 8px; font-size: 0.8rem;">×</button>
                </div>
            </div>
        </div>
        
        <!-- Enum values field (shown when type is enum) -->
        <div class="tree-enum-field" style="display: ${data.type === 'enum' ? 'block' : 'none'}; margin-bottom: 8px; margin-left: 34px;">
            <input type="text" class="tree-param-enum" placeholder="option1,option2,option3"
                   style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
            <small style="display: block; color: #6c757d; font-size: 0.75rem; margin-top: 2px;">カンマ区切りで選択肢を入力</small>
        </div>
        
        <!-- Default value field -->
        <div class="tree-default-field tree-default-value-field" style="display: ${data.type === 'object' || data.type === 'array' ? 'none' : 'block'}; margin-bottom: 8px; margin-left: 34px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;" class="tree-default-label">${isFixedParam ? '値:' : 'デフォルト値:'}</label>
            ${
                data.type === 'boolean' ?
                (isFixedParam ?
                    `<select class="tree-param-default" style="width: 200px; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                        <option value="true" ${data.default === true || data.default === 'true' || !data.default ? 'selected' : ''}>true</option>
                        <option value="false" ${data.default === false || data.default === 'false' ? 'selected' : ''}>false</option>
                    </select>` :
                    `<select class="tree-param-default" style="width: 200px; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                        <option value="" ${!data.default && data.default !== false ? 'selected' : ''}>未設定</option>
                        <option value="true" ${data.default === true || data.default === 'true' ? 'selected' : ''}>true</option>
                        <option value="false" ${data.default === false || data.default === 'false' ? 'selected' : ''}>false</option>
                    </select>`
                ) :
                `<input type="text" class="tree-param-default" placeholder="${isFixedParam ? '値' : 'デフォルト値'}" style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">`
            }
        </div>
        
        <!-- Array items type field (shown when type is array) -->
        <div class="tree-array-items-field" style="display: ${data.type === 'array' ? 'block' : 'none'}; margin-bottom: 8px; margin-left: 34px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">配列要素の型:</label>
            <select class="tree-array-items-type" style="width: 200px; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                <option value="string" ${data.itemsType === 'string' ? 'selected' : ''}>string</option>
                <option value="number" ${data.itemsType === 'number' ? 'selected' : ''}>number</option>
                <option value="integer" ${data.itemsType === 'integer' ? 'selected' : ''}>integer</option>
                <option value="boolean" ${data.itemsType === 'boolean' ? 'selected' : ''}>boolean</option>
                <option value="object" ${data.itemsType === 'object' ? 'selected' : ''}>object</option>
            </select>
        </div>
        
        <!-- Array value field (shown for fixed params with array type and non-object items) -->
        <div class="tree-array-value-field" style="display: ${isFixedParam && data.type === 'array' && data.itemsType !== 'object' ? 'block' : 'none'}; margin-bottom: 8px; margin-left: 34px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">値 (カンマ区切り):</label>
            <input type="text" class="tree-array-value" placeholder="${
                data.itemsType === 'string' ? 'value1, value2, value3' :
                data.itemsType === 'number' || data.itemsType === 'integer' ? '1, 2, 3' :
                data.itemsType === 'boolean' ? 'true, false, true' : ''
            }" style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
        </div>
        
        <!-- Array object value field (shown for fixed params with array type and object items) -->
        <div class="tree-array-object-value-field" style="display: ${isFixedParam && data.type === 'array' && data.itemsType === 'object' ? 'block' : 'none'}; margin-bottom: 8px; margin-left: 34px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">値 (オブジェクトをカンマ区切り):</label>
            <textarea class="tree-array-object-value" rows="4" placeholder='{"key": "value"}, {"key": "value"}' style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; font-family: monospace;"></textarea>
        </div>
        
        <!-- Object value field (shown for fixed params with object type at depth >= 1) -->
        <div class="tree-object-value-field" style="display: ${isFixedParam && data.type === 'object' && depth >= 1 ? 'block' : 'none'}; margin-bottom: 8px; margin-left: 34px;">
            <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">値 (JSON形式):</label>
            <textarea class="tree-param-default" rows="4" placeholder='{"key": "value"}' style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem; font-family: monospace;"></textarea>
        </div>
        
        <!-- Children container (for object type) -->
        <div class="tree-children" style="display: ${isExpandable && hasChildren ? 'block' : 'none'}; margin-left: 20px; margin-top: 10px;"></div>
        
        <!-- Add child button (for object type) -->
        <div class="tree-add-child" style="display: ${data.type === 'object' && (!isFixedParam || depth === 0) ? 'block' : 'none'}; margin-left: 34px; margin-top: 8px;">
            <button type="button" data-action="add-tree-child" data-node-id="${nodeId}" class="btn btn-sm btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;">+ 子プロパティを追加</button>
        </div>
        
        <!-- Add array item property button (for array type with object items) -->
        <div class="tree-add-array-item-property" style="display: ${data.type === 'array' && data.itemsType === 'object' ? 'block' : 'none'}; margin-left: 34px; margin-top: 8px;">
            <button type="button" data-action="add-tree-array-property" data-node-id="${nodeId}" class="btn btn-sm btn-secondary" style="padding: 4px 10px; font-size: 0.8rem;">+ 配列要素のプロパティを定義</button>
        </div>
        
        <!-- Children container (for object type) -->
        <div class="tree-children" style="display: ${isExpandable && hasChildren ? 'block' : 'none'}; margin-left: 20px; margin-top: 10px;"></div>
        
        <!-- Array item properties container (for array type with object items) -->
        <div class="tree-array-item-properties" style="margin-left: 20px; margin-top: 10px;"></div>
    `;
    
    container.appendChild(node);
    
    // Set input values after DOM insertion to avoid template literal issues
    const nameInput = node.querySelector('.tree-param-name');
    const descInput = node.querySelector('.tree-param-description');
    const enumInput = node.querySelector('.tree-param-enum');
    const defaultInput = node.querySelector('.tree-param-default');
    
    if (nameInput) nameInput.value = data.name || '';
    if (descInput) descInput.value = data.description || '';
    if (enumInput) enumInput.value = data.enum || '';
    // boolean型selectboxの場合はtemplate内のselected属性で値が設定されているためスキップ
    if (defaultInput && defaultInput.tagName !== 'SELECT') {
        defaultInput.value = data.default || '';
    }
    
    // Set array value for fixed params with array type
    const arrayValueInput = node.querySelector('.tree-array-value');
    if (arrayValueInput) {
        arrayValueInput.value = data.arrayValue || '';
    }
    
    // Set array object value for fixed params with array+object type
    const arrayObjectValueInput = node.querySelector('.tree-array-object-value');
    if (arrayObjectValueInput) {
        arrayObjectValueInput.value = data.arrayObjectValue || '';
    }
    
    // Set object value for fixed params with object type at depth >= 1
    if (isFixedParam && data.type === 'object' && depth >= 1) {
        const objectValueInput = node.querySelector('.tree-object-value-field .tree-param-default');
        if (objectValueInput && data.default) {
            objectValueInput.value = typeof data.default === 'object' ? JSON.stringify(data.default, null, 2) : data.default;
        }
    }
    
    // Recursively add children if any
    if (data.children && data.children.length > 0) {
        data.children.forEach(child => {
            addLlmParamTreeRow(node, depth + 1, child);
        });
    }
    
    // Recursively add array items properties if any
    if (data.itemsProperties && data.itemsProperties.length > 0) {
        const arrayItemPropertiesContainer = node.querySelector('.tree-array-item-properties');
        data.itemsProperties.forEach(itemProp => {
            addLlmParamTreeRow(arrayItemPropertiesContainer, depth + 1, itemProp);
        });
    }
    
    return node;
}

function toggleTreeNode(nodeId) {
    const node = document.querySelector(`.tree-node[data-node-id="${nodeId}"]`);
    if (!node) return;
    
    const expandBtn = node.querySelector('.expand-btn');
    const childrenContainer = node.querySelector('.tree-children');
    
    if (childrenContainer.style.display === 'none') {
        childrenContainer.style.display = 'block';
        expandBtn.textContent = '▼';
    } else {
        childrenContainer.style.display = 'none';
        expandBtn.textContent = '▶';
    }
}

function handleTreeTypeChange(nodeId) {
    const node = document.querySelector(`.tree-node[data-node-id="${nodeId}"]`);
    if (!node) return;
    
    const typeSelect = node.querySelector('.tree-param-type');
    const selectedType = typeSelect.value;
    
    const enumField = node.querySelector('.tree-enum-field');
    const arrayItemsField = node.querySelector('.tree-array-items-field');
    const addChildBtn = node.querySelector('.tree-add-child');
    const addArrayItemPropertyBtn = node.querySelector('.tree-add-array-item-property');
    const expandBtn = node.querySelector('.expand-btn');
    const childrenContainer = node.querySelector('.tree-children');
    const defaultFieldContainer = node.querySelector('.tree-default-value-field');
    
    // 固定パラメータとdepthチェック
    const isFixedParam = node.closest('#fixed-params-post-container') !== null;
    const depth = parseInt(node.getAttribute('data-depth')) || 0;
    
    // Show/hide fields based on type
    enumField.style.display = selectedType === 'enum' ? 'block' : 'none';
    arrayItemsField.style.display = selectedType === 'array' ? 'block' : 'none';
    // 固定パラメータの場合、depth=0のみ子追加可能
    addChildBtn.style.display = (selectedType === 'object' && (!isFixedParam || depth === 0)) ? 'block' : 'none';
    expandBtn.style.display = selectedType === 'object' ? 'block' : 'none';
    
    // デフォルト値/値フィールド表示制御とフィールド再構築
    if (defaultFieldContainer) {
        const shouldShow = selectedType !== 'object' && selectedType !== 'array';
        defaultFieldContainer.style.display = shouldShow ? 'block' : 'none';
        
        if (shouldShow) {
            // 現在の値を保持
            const currentInput = defaultFieldContainer.querySelector('.tree-param-default');
            const currentValue = currentInput ? currentInput.value : '';
            
            // ラベルテキストを判定（固定パラメータか否か）
            const label = defaultFieldContainer.querySelector('.tree-default-label');
            const isFixedParam = label && label.textContent.includes('値:');
            const labelText = isFixedParam ? '値:' : 'デフォルト値:';
            const placeholderText = isFixedParam ? '値' : 'デフォルト値';
            
            // フィールドを再構築
            if (selectedType === 'boolean') {
                if (isFixedParam) {
                    // 固定パラメータ: true/falseのみ、デフォルトtrue
                    defaultFieldContainer.innerHTML = `
                        <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;" class="tree-default-label">${labelText}</label>
                        <select class="tree-param-default" style="width: 200px; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                            <option value="true" ${currentValue === 'true' || !currentValue ? 'selected' : ''}>true</option>
                            <option value="false" ${currentValue === 'false' ? 'selected' : ''}>false</option>
                        </select>
                    `;
                } else {
                    // LLMパラメータ: 未設定/true/false
                    defaultFieldContainer.innerHTML = `
                        <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;" class="tree-default-label">${labelText}</label>
                        <select class="tree-param-default" style="width: 200px; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                            <option value="" ${!currentValue ? 'selected' : ''}>未設定</option>
                            <option value="true" ${currentValue === 'true' ? 'selected' : ''}>true</option>
                            <option value="false" ${currentValue === 'false' ? 'selected' : ''}>false</option>
                        </select>
                    `;
                }
            } else {
                // booleanから変更された場合はtrue/false値をクリア
                const shouldClearValue = (currentValue === 'true' || currentValue === 'false');
                defaultFieldContainer.innerHTML = `
                    <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;" class="tree-default-label">${labelText}</label>
                    <input type="text" class="tree-param-default" placeholder="${placeholderText}" value="${shouldClearValue ? '' : AppDom.escapeHtml(currentValue)}" style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.85rem;">
                `;
            }
        }
    }
    
    // Array items object control
    const arrayValueField = node.querySelector('.tree-array-value-field');
    const arrayObjectValueField = node.querySelector('.tree-array-object-value-field');
    const objectValueField = node.querySelector('.tree-object-value-field');
    
    if (selectedType === 'array') {
        const itemsType = node.querySelector('.tree-array-items-type').value;
        const isFixedParam = node.closest('#fixed-params-post-container') !== null;
        
        // 固定パラメータの場合はボタンを非表示（JSON直接入力するため）
        addArrayItemPropertyBtn.style.display = (itemsType === 'object' && !isFixedParam) ? 'block' : 'none';
        
        // array値フィールド：固定パラメータの場合のみ表示
        if (arrayValueField) {
            arrayValueField.style.display = (isFixedParam && itemsType !== 'object') ? 'block' : 'none';
        }
        if (arrayObjectValueField) {
            arrayObjectValueField.style.display = (isFixedParam && itemsType === 'object') ? 'block' : 'none';
        }
        if (objectValueField) {
            objectValueField.style.display = 'none';
        }
    } else if (selectedType === 'object') {
        addArrayItemPropertyBtn.style.display = 'none';
        if (arrayValueField) arrayValueField.style.display = 'none';
        if (arrayObjectValueField) arrayObjectValueField.style.display = 'none';
        // 固定パラメータのdepth>=1の場合、object値フィールドを表示
        if (objectValueField) {
            objectValueField.style.display = (isFixedParam && depth >= 1) ? 'block' : 'none';
        }
    } else {
        addArrayItemPropertyBtn.style.display = 'none';
        if (arrayValueField) arrayValueField.style.display = 'none';
        if (arrayObjectValueField) arrayObjectValueField.style.display = 'none';
        if (objectValueField) objectValueField.style.display = 'none';
    }
    
    // If changing away from object, hide children
    if (selectedType !== 'object') {
        childrenContainer.style.display = 'none';
    }
}

function handleArrayItemsTypeChange(nodeId) {
    const node = document.querySelector(`.tree-node[data-node-id="${nodeId}"]`);
    if (!node) return;
    
    const itemsType = node.querySelector('.tree-array-items-type').value;
    const addArrayItemPropertyBtn = node.querySelector('.tree-add-array-item-property');
    const arrayValueField = node.querySelector('.tree-array-value-field');
    const arrayObjectValueField = node.querySelector('.tree-array-object-value-field');
    
    const isFixedParam = node.closest('#fixed-params-post-container') !== null;
    
    // 固定パラメータの場合はボタンを非表示（JSON直接入力するため）
    addArrayItemPropertyBtn.style.display = (itemsType === 'object' && !isFixedParam) ? 'block' : 'none';
    
    // array値フィールド：固定パラメータの場合のみ表示
    if (arrayValueField) {
        arrayValueField.style.display = (isFixedParam && itemsType !== 'object') ? 'block' : 'none';
        
        // プリミティブ型の場合、プレースホルダーを更新
        if (itemsType !== 'object') {
            const arrayValueInput = arrayValueField.querySelector('.tree-array-value');
            if (arrayValueInput) {
                if (itemsType === 'string') {
                    arrayValueInput.placeholder = 'value1, value2, value3';
                } else if (itemsType === 'number' || itemsType === 'integer') {
                    arrayValueInput.placeholder = '1, 2, 3';
                } else if (itemsType === 'boolean') {
                    arrayValueInput.placeholder = 'true, false, true';
                }
            }
        }
    }
    
    // array object値フィールド：object型の場合のみ表示
    if (arrayObjectValueField) {
        arrayObjectValueField.style.display = (isFixedParam && itemsType === 'object') ? 'block' : 'none';
    }
}

function addChildToTreeNode(parentNodeId) {
    const parentNode = document.querySelector(`.tree-node[data-node-id="${parentNodeId}"]`);
    if (!parentNode) return;
    
    const depth = parseInt(parentNode.getAttribute('data-depth')) + 1;
    const childrenContainer = parentNode.querySelector('.tree-children');
    
    if (childrenContainer) {
        addLlmParamTreeRow(childrenContainer, depth);
        
        // Show children container and update expand button
        childrenContainer.style.display = 'block';
        const expandBtn = parentNode.querySelector('.expand-btn');
        if (expandBtn) expandBtn.textContent = '▼';
    }
}

function addArrayItemPropertyNode(nodeId) {
    const parentNode = document.querySelector(`.tree-node[data-node-id="${nodeId}"]`);
    if (!parentNode) return;
    
    const arrayItemPropertiesContainer = parentNode.querySelector('.tree-array-item-properties');
    const depth = parseInt(parentNode.dataset.depth) + 1;
    
    if (arrayItemPropertiesContainer) {
        addLlmParamTreeRow(arrayItemPropertiesContainer, depth);
        arrayItemPropertiesContainer.style.display = 'block';
    }
}

function removeTreeNode(nodeId) {
    const node = document.querySelector(`.tree-node[data-node-id="${nodeId}"]`);
    if (node) {
        node.remove();
    }
}

// Form inputs show strings as-is; only non-string defaults are JSON-encoded
function formatDefaultForInput(value) {
    if (value === undefined) return '';
    return typeof value === 'string' ? value : JSON.stringify(value);
}

// The new page stores fixed params as properties with a const constraint; legacy data used _fixed
function splitFixedProperties(properties) {
    const fixed = {};
    const llm = {};
    Object.entries(properties || {}).forEach(([name, propDef]) => {
        if (propDef && propDef.const !== undefined) {
            fixed[name] = propDef;
        } else {
            llm[name] = propDef;
        }
    });
    return { fixed, llm };
}

// Helper function to build paramData from JSON Schema property definition
function buildParamDataFromProperty(name, propDef, requiredList) {
    const hasEnum = propDef.enum && propDef.enum.length > 0;
    const paramData = {
        name: name,
        type: hasEnum ? 'enum' : (propDef.type || 'string'),
        description: propDef.description || '',
        required: requiredList.includes(name),
        enum: propDef.enum ? propDef.enum.join(',') : '',
        default: formatDefaultForInput(propDef.default),
        children: [],
        itemsType: 'string',
        arrayValue: '' // CSV形式の配列値
    };
    
    // Handle array items type
    if (propDef.type === 'array' && propDef.items) {
        paramData.itemsType = propDef.items.type || 'string';
        
        // const制約がある場合、配列値を適切な形式に変換
        if (propDef.const !== undefined && Array.isArray(propDef.const)) {
            if (propDef.items.type === 'object') {
                // object配列の場合、各オブジェクトをカンマ区切りで連結（[]なし）
                const objectStrings = propDef.const.map(obj => JSON.stringify(obj));
                paramData.arrayObjectValue = objectStrings.join(',\n');
            } else {
                // プリミティブ型配列の場合、CSV文字列として保存
                paramData.arrayValue = propDef.const.join(', ');
            }
        }
        
        // Handle array items with object type that have properties
        if (propDef.items.type === 'object' && propDef.items.properties) {
            const itemRequired = propDef.items.required || [];
            paramData.itemsProperties = Object.entries(propDef.items.properties).map(([itemPropName, itemPropDef]) => {
                return buildParamDataFromProperty(itemPropName, itemPropDef, itemRequired);
            });
        }
    }
    
    // Handle nested object properties
    if (propDef.type === 'object' && propDef.properties) {
        const childRequired = propDef.required || [];
        paramData.children = Object.entries(propDef.properties).map(([childName, childProp]) => {
            return buildParamDataFromProperty(childName, childProp, childRequired);
        });
    }
    
    return paramData;
}

async function loadCapability() {
    const cap = await AppApi.request(`/api/capabilities/${capabilityId}`);
    
    console.log('=== Capability Data ===');
    console.log('Full capability:', cap);
    console.log('Headers:', cap.headers);
    console.log('Body params:', cap.body_params);
    console.log('=====================');
    
    // Get parent app information to check if it's MCP type and get base URL
    const app = await AppApi.request(`/api/apps/${cap.service_id}`);
    const isMcpType = app.service_type === 'mcp';
    baseUrl = app.mcp_url || '';
    
    // Get MCP service information for breadcrumb
    const mcpServiceId = cap.mcp_service_id || 1; // APIから取得するか、デフォルト値
    const mcpService = await AppApi.request(`/api/mcp-services/${mcpServiceId}`);
    
    // Update breadcrumb links with specific names
    document.getElementById('mcp-service-link').href = `/mcp-services/${mcpServiceId}`;
    document.getElementById('mcp-service-link').textContent = mcpService.name;
    
    document.getElementById('apps-link').href = `/mcp-services/${mcpServiceId}/apps`;
    
    document.getElementById('service-link').href = `/mcp-services/${mcpServiceId}/apps/${cap.service_id}`;
    document.getElementById('service-link').textContent = app.name;
    
    document.getElementById('capabilities-link').href = `/mcp-services/${mcpServiceId}/apps/${cap.service_id}/capabilities`;
    
    document.getElementById('detail-link').href = `/capabilities/${capabilityId}`;
    document.getElementById('detail-link').textContent = cap.name;
    
    document.getElementById('cancel-link').href = `/capabilities/${capabilityId}`;
    
    document.getElementById('name').value = cap.name;
    document.getElementById('url').value = cap.url || '';
    document.getElementById('description').value = cap.description || '';
    document.getElementById('timeout_seconds').value = cap.timeout_seconds || 30;
    
    // Add input event listener for URL preview
    const urlInput = document.getElementById('url');
    if (urlInput) {
        urlInput.addEventListener('input', updateUrlPreview);
        // Initial URL preview update
        updateUrlPreview();
    }
    
    // Set access control (default: public for capabilities)
    currentAccessControl = cap.access_control || 'public';
    const isRestricted = currentAccessControl === 'restricted';
    document.getElementById('access-control-toggle').checked = isRestricted;
    updateAccessControlUI(isRestricted);
    
    // Handle different capability types
    const capabilityType = cap.capability_type || 'tool';
    
    // Load Prompt type specific fields if applicable
    if (capabilityType === 'prompt') {
        const promptFieldsSection = document.getElementById('prompt-fields-section');
        if (promptFieldsSection) {
            promptFieldsSection.style.display = 'block';
        }
        
        // Load template content
        const templateContentEdit = document.getElementById('template_content_edit');
        if (templateContentEdit) {
            templateContentEdit.value = cap.template_content || '';
            generatePromptPreviewEdit();
        }
        
        // Hide tool-specific sections
        const toolFieldsSection = document.getElementById('tool-fields-section');
        if (toolFieldsSection) {
            toolFieldsSection.style.display = 'none';
        }
        
        const timeoutFieldSection = document.getElementById('timeout-field-section');
        if (timeoutFieldSection) {
            timeoutFieldSection.style.display = 'none';
        }
        
        // Remove required attribute from URL and method fields
        const urlField = document.getElementById('url');
        if (urlField) urlField.removeAttribute('required');
        const methodField = document.getElementById('method');
        if (methodField) methodField.removeAttribute('required');
        
        // Promptタイプは後続の処理をスキップして、body_paramsのロードまでジャンプ
        // (body_paramsは引数定義として使用)
    }
    
    // Load Resource type specific fields if applicable
    if (cap.capability_type === 'resource') {
        const resourceFieldsSection = document.getElementById('resource-fields-section');
        if (resourceFieldsSection) {
            resourceFieldsSection.style.display = 'block';
        }
        
        // Load available resources for selection
        const globalResourceSelect = document.getElementById('global_resource_id');
        if (globalResourceSelect) {
            const resources = await AppApi.request('/api/resources');
            
            globalResourceSelect.innerHTML = resources.map(r => 
                `<option value="${Number(r.id)}" ${cap.global_resource_id === r.id ? 'selected' : ''}>
                    ${AppDom.escapeHtml(r.name)} (${AppDom.escapeHtml(r.mime_type)})
                </option>`
            ).join('');
            
            // Add change listener to load resource info
            globalResourceSelect.addEventListener('change', async (e) => {
                if (e.target.value) {
                    const selectedResource = resources.find(r => r.id == e.target.value);
                    if (selectedResource) {
                        // Update resource info display
                        document.getElementById('selected-resource-name-edit').textContent = selectedResource.name;
                        document.getElementById('selected-resource-uri-edit').textContent = selectedResource.resource_id || '';
                        document.getElementById('selected-resource-mime-edit').textContent = selectedResource.mime_type;
                        document.getElementById('selected-resource-desc-edit').textContent = selectedResource.description || '';
                        document.getElementById('selected-resource-content-edit').textContent = selectedResource.content || '';
                        document.getElementById('selected-resource-info-edit').style.display = 'block';
                    }
                } else {
                    document.getElementById('selected-resource-info-edit').style.display = 'none';
                }
            });
        }
        
        // Determine if using existing or new resource
        if (cap.global_resource_id) {
            // Using existing global resource
            document.querySelector('input[name="resource_source"][value="existing"]').checked = true;
            
            // Fetch and display resource info
            const resource = await AppApi.request(`/api/resources/${cap.global_resource_id}`);
            
            document.getElementById('selected-resource-name-edit').textContent = resource.name;
            document.getElementById('selected-resource-uri-edit').textContent = resource.resource_id || '';
            document.getElementById('selected-resource-mime-edit').textContent = resource.mime_type;
            document.getElementById('selected-resource-desc-edit').textContent = resource.description || '';
            document.getElementById('selected-resource-content-edit').textContent = resource.content || '';
            document.getElementById('selected-resource-info-edit').style.display = 'block';
        } else {
            // Using inline resource (new)
            document.querySelector('input[name="resource_source"][value="new"]').checked = true;
            
            // Populate new resource fields
            document.getElementById('resource_name_edit').value = cap.name || '';
            document.getElementById('resource_mime_type').value = cap.resource_mime_type || 'text/plain';
            document.getElementById('resource_content').value = cap.template_content || '';
            
            // Generate initial preview
            generateResourcePreviewEdit();
        }
        
        // Initialize toggle
        window.toggleResourceSourceEdit();
    }
    
    // Skip method and params loading for resource type
    if (cap.capability_type === 'resource') {
        // Resource type doesn't need method, headers, or body params
        // Remove required attribute from URL and method fields
        const urlField = document.getElementById('url');
        if (urlField) urlField.removeAttribute('required');
        const methodField = document.getElementById('method');
        if (methodField) methodField.removeAttribute('required');
        
        // Hide tool-specific sections
        const toolFieldsSection = document.getElementById('tool-fields-section');
        if (toolFieldsSection) toolFieldsSection.style.display = 'none';
        
        const timeoutFieldSection = document.getElementById('timeout-field-section');
        if (timeoutFieldSection) timeoutFieldSection.style.display = 'none';
        
        const headersFormGroup = document.getElementById('headers-container')?.closest('.form-group');
        if (headersFormGroup) headersFormGroup.style.display = 'none';
        
        const bodyFormGroup = document.getElementById('body-key-value')?.closest('.form-group');
        if (bodyFormGroup) bodyFormGroup.style.display = 'none';
        
        const fixedParamsFormGroup = document.getElementById('fixed-params-container')?.closest('.form-group');
        if (fixedParamsFormGroup) fixedParamsFormGroup.style.display = 'none';
        
        const llmParamsFormGroup = document.getElementById('llm-params-container')?.closest('.form-group');
        if (llmParamsFormGroup) llmParamsFormGroup.style.display = 'none';
        
        const postFixedParamsFormGroup = document.getElementById('fixed-params-post-container')?.closest('.form-group');
        if (postFixedParamsFormGroup) postFixedParamsFormGroup.style.display = 'none';
        
        const llmParamsTreeFormGroup = document.getElementById('llm-params-tree-container')?.closest('.form-group');
        if (llmParamsTreeFormGroup) llmParamsTreeFormGroup.style.display = 'none';
        
        return isMcpType;
    }
    
    // Get HTTP method from headers
    const method = cap.headers['X-HTTP-Method'] || 'POST';
    const methodElem = document.getElementById('method');
    if (methodElem) {
        methodElem.value = method;
    }
    
    // If MCP type, make fields read-only and hide URL/method fields
    if (isMcpType) {
        document.getElementById('name').readOnly = true;
        document.getElementById('url').readOnly = true;
        document.getElementById('description').readOnly = true;
        document.getElementById('method').disabled = true;
        
        // Hide URL and method fields for MCP type
        const toolFieldsSection = document.getElementById('tool-fields-section');
        if (toolFieldsSection) {
            toolFieldsSection.style.display = 'none';
        }
        
        // Add visual indication
        ['name', 'description'].forEach(id => {
            const elem = document.getElementById(id);
            elem.style.backgroundColor = '#f5f5f5';
            elem.style.cursor = 'not-allowed';
        });
        
        // Update request sample titles for MCP type
        const getSampleTitle = document.getElementById('request-sample-get-title');
        const postSampleTitle = document.getElementById('request-sample-post-title');
        if (getSampleTitle) {
            getSampleTitle.setAttribute('data-i18n', 'capability_request_to_mcp');
            getSampleTitle.textContent = t('capability_request_to_mcp');
        }
        if (postSampleTitle) {
            postSampleTitle.setAttribute('data-i18n', 'capability_request_body_to_mcp');
            postSampleTitle.textContent = t('capability_request_body_to_mcp');
        }
    }
    
    // Load headers (excluding X-HTTP-Method)
    const headers = { ...cap.headers };
    delete headers['X-HTTP-Method'];
    
    if (Object.keys(headers).length === 0) {
        if (!isMcpType) addHeaderRow(); // Add empty row if no headers (only for API type)
    } else {
        Object.entries(headers).forEach(([key, value]) => {
            addHeaderRow(key, value, isMcpType);
        });
    }
    
    // Hide "Add Header" button for MCP type
    if (isMcpType) {
        const addHeaderBtn = document.querySelector('button[data-action="add-header"]');
        if (addHeaderBtn) addHeaderBtn.style.display = 'none';
    }
    
    // Load body parameters
    toggleBodyType();
    
    if (method === 'GET') {
        // Check if body_params has JSON Schema structure (properties field)
        const hasSchema = cap.body_params && cap.body_params.properties;
        
        if (hasSchema) {
            // New format: JSON Schema with _fixed params
            const { fixed: constProperties, llm: properties } = splitFixedProperties(cap.body_params.properties);
            const fixedParams = { ...(cap.body_params._fixed || {}) };
            Object.entries(constProperties).forEach(([key, propDef]) => {
                fixedParams[key] = formatDefaultForInput(propDef.const);
            });
            const required = cap.body_params.required || [];
            
            // Load fixed parameters
            if (Object.keys(fixedParams).length === 0 && !isMcpType) {
                addFixedParamRow('', '', isMcpType);
            } else {
                Object.entries(fixedParams).forEach(([key, valueOrObj]) => {
                    // 新形式: {value: "...", type: "..."} または旧形式: 直接値
                    const value = (typeof valueOrObj === 'object' && valueOrObj.value !== undefined) 
                        ? valueOrObj.value 
                        : valueOrObj;
                    addFixedParamRow(key, value, isMcpType);
                });
            }
            
            // Load LLM parameters from schema
            if (Object.keys(properties).length === 0 && !isMcpType) {
                addLlmParamRow(null, isMcpType);
            } else {
                Object.entries(properties).forEach(([name, propDef]) => {
                    // Check if it has enum to determine type
                    const hasEnum = propDef.enum && propDef.enum.length > 0;
                    const paramData = {
                        name: name,
                        type: hasEnum ? 'enum' : (propDef.type || 'string'),
                        description: propDef.description || '',
                        required: required.includes(name),
                        enum: propDef.enum ? propDef.enum.join(',') : '',
                        default: formatDefaultForInput(propDef.default)
                    };
                    addLlmParamRow(paramData, isMcpType);
                });
            }
        } else {
            // Old format: simple key-value pairs - convert to new format
            const fixedParams = cap.body_params || {};
            
            if (Object.keys(fixedParams).length === 0) {
                if (!isMcpType) {
                    addFixedParamRow('', '', isMcpType);
                    addLlmParamRow(null, isMcpType);
                }
            } else {
                // Treat all existing params as fixed params for backward compatibility
                Object.entries(fixedParams).forEach(([key, value]) => {
                    addFixedParamRow(key, value, isMcpType);
                });
                if (!isMcpType) {
                    addLlmParamRow(null, isMcpType);
                }
            }
        }
    } else {
        // POST method: load into hierarchical tree editor
        
        // body_paramsが文字列の場合はパース
        let bodyParamsObj = cap.body_params;
        if (typeof bodyParamsObj === 'string') {
            try {
                bodyParamsObj = JSON.parse(bodyParamsObj);
            } catch (e) {
                console.error('Failed to parse body_params:', e);
                bodyParamsObj = {};
            }
        }
        
        const hasSchema = bodyParamsObj && bodyParamsObj.properties;
        
        console.log('POST method loading - bodyParamsObj:', bodyParamsObj);
        console.log('hasSchema:', hasSchema);
        
        if (hasSchema) {
            // New format: JSON Schema with hierarchical structure
            const { fixed: constProperties, llm: properties } = splitFixedProperties(bodyParamsObj.properties);
            const fixedParams = bodyParamsObj._fixed || {};
            const required = bodyParamsObj.required || [];
            
            // Load const-constrained properties (current format) as fixed parameters
            Object.entries(constProperties).forEach(([key, propDef]) => {
                const paramData = buildParamDataFromProperty(key, propDef, []);
                if (!Array.isArray(propDef.const)) {
                    // Arrays are carried in arrayValue/arrayObjectValue by buildParamDataFromProperty
                    paramData.default = formatDefaultForInput(propDef.const);
                }
                addFixedParamPostRow(null, 0, paramData, isMcpType);
            });
            
            // Load fixed parameters stored in the legacy _fixed key
            if (Object.keys(fixedParams).length === 0 && !isMcpType) {
                // Empty fixed params - add placeholder if needed
            } else {
                Object.entries(fixedParams).forEach(([key, valueOrObj]) => {
                    let paramData;
                    if (typeof valueOrObj === 'object' && valueOrObj.schema) {
                        // 新形式: 階層構造あり
                        paramData = buildParamDataFromProperty(key, valueOrObj.schema, []);
                        paramData.default = valueOrObj.value || '';
                    } else if (typeof valueOrObj === 'object' && valueOrObj.value !== undefined) {
                        // 中間形式: {value: "...", type: "string"}
                        paramData = {
                            name: key,
                            type: valueOrObj.type || 'string',
                            default: valueOrObj.value,
                            description: '',
                            required: false,
                            enum: '',
                            children: [],
                            itemsType: 'string'
                        };
                    } else {
                        // 旧形式互換: 直接値
                        paramData = {
                            name: key,
                            type: 'string',
                            default: valueOrObj,
                            description: '',
                            required: false,
                            enum: '',
                            children: [],
                            itemsType: 'string'
                        };
                    }
                    addFixedParamPostRow(null, 0, paramData, isMcpType);
                });
            }
            
            // Load LLM parameters into tree structure
            if (Object.keys(properties).length === 0 && !isMcpType) {
                addLlmParamTreeRow(null, 0);
            } else {
                Object.entries(properties).forEach(([name, propDef]) => {
                    const paramData = buildParamDataFromProperty(name, propDef, required);
                    addLlmParamTreeRow(null, 0, paramData);
                });
            }
        } else {
            // Old format: convert to tree structure
            // This is the old format where each parameter has {type, description, required}
            if (bodyParamsObj && Object.keys(bodyParamsObj).length > 0) {
                Object.entries(bodyParamsObj).forEach(([key, paramDef]) => {
                    // Check if it's the old format with type/description/required
                    if (paramDef && typeof paramDef === 'object' && paramDef.type) {
                        const paramData = {
                            name: key,
                            type: paramDef.type || 'string',
                            description: paramDef.description || '',
                            required: paramDef.required || false,
                            enum: '',
                            default: '',
                            children: [],
                            itemsType: 'string'
                        };
                        addLlmParamTreeRow(null, 0, paramData);
                    } else {
                        // Even older format: just key-value pairs
                        const paramData = {
                            name: key,
                            type: typeof paramDef === 'number' ? 'number' : typeof paramDef === 'boolean' ? 'boolean' : 'string',
                            default: paramDef,
                            description: '',
                            required: false,
                            enum: '',
                            children: [],
                            itemsType: 'string'
                        };
                        addFixedParamPostRow(null, 0, paramData, isMcpType);
                    }
                });
            } else if (!isMcpType) {
                // No params - add empty row
                addLlmParamTreeRow(null, 0);
            }
        }
    }
    
    // Hide "Add" buttons for MCP type
    if (isMcpType) {
        const addFixedBtn = document.querySelector('button[data-action="add-fixed-param"]');
        if (addFixedBtn) addFixedBtn.style.display = 'none';
        const addLlmBtn = document.querySelector('button[data-action="add-llm-param"]');
        if (addLlmBtn) addLlmBtn.style.display = 'none';
        
        // Hide POST editor buttons
        const addFixedPostBtn = document.querySelector('button[data-action="add-fixed-param-post"]');
        if (addFixedPostBtn) addFixedPostBtn.style.display = 'none';
        const addLlmTreeBtn = document.querySelector('button[data-action="add-llm-param-tree"]');
        if (addLlmTreeBtn) addLlmTreeBtn.style.display = 'none';
    }
    
    return isMcpType;
}

// Initialize and setup
(async () => {
    await initLanguageSwitcher();
    const isMcpType = await loadCapability();
    await loadPermissions();
    setupStaticEventListeners();
    
    // Setup drag and drop for resource file upload
    const dropZoneEdit = document.getElementById('resource-drop-zone-edit');
    if (dropZoneEdit) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZoneEdit.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // Highlight drop zone when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZoneEdit.addEventListener(eventName, () => {
                dropZoneEdit.style.backgroundColor = '#e6f7ff';
                dropZoneEdit.style.borderColor = '#1890ff';
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZoneEdit.addEventListener(eventName, () => {
                dropZoneEdit.style.backgroundColor = '#f7fafc';
                dropZoneEdit.style.borderColor = '#cbd5e0';
            });
        });
        
        // Handle dropped files
        dropZoneEdit.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleResourceFileUploadEdit(files[0]);
            }
        });
        
        // Click to select file
        dropZoneEdit.addEventListener('click', (e) => {
            // ボタンクリックでない場合のみ
            if (e.target.tagName !== 'BUTTON') {
                document.getElementById('resource_file_edit')?.click();
            }
        });
    }
    
    // Setup auto-update for request sample (debounced)
    let sampleUpdateTimer;
    function scheduleRequestSampleUpdate() {
        clearTimeout(sampleUpdateTimer);
        sampleUpdateTimer = setTimeout(() => {
            generateRequestSample();
        }, 500); // 500ms debounce
    }
    
    // Listen to method changes
    document.getElementById('method').addEventListener('change', () => {
        toggleBodyType();
        scheduleRequestSampleUpdate();
    });
    
    // Listen to URL changes
    document.getElementById('url').addEventListener('input', scheduleRequestSampleUpdate);
    
    // Use event delegation for dynamically added parameter rows
    document.addEventListener('input', (e) => {
        // Check if the input is in parameter containers
        if (e.target.closest('#fixed-params-container') ||
            e.target.closest('#llm-params-container') ||
            e.target.closest('#fixed-params-post-container') ||
            e.target.closest('#llm-params-tree-container')) {
            scheduleRequestSampleUpdate();
        }
    });
    
    // Listen to checkbox changes in parameter rows
    document.addEventListener('change', (e) => {
        if (e.target.closest('#llm-params-container') ||
            e.target.closest('#llm-params-tree-container')) {
            scheduleRequestSampleUpdate();
        }
    });
    
    // Initial sample generation
    setTimeout(generateRequestSample, 100);
    
    // Setup access control toggle
    document.getElementById('access-control-toggle').addEventListener('change', async (e) => {
        const isRestricted = e.target.checked;
        updateAccessControlUI(isRestricted);
        currentAccessControl = isRestricted ? 'restricted' : 'public';
    });
    
    // Setup form submit handler
    document.getElementById('capability-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError();
        
        const formData = new FormData(e.target);
        
        // Check capability type
        const promptFieldsSection = document.getElementById('prompt-fields-section');
        const isPromptType = promptFieldsSection && promptFieldsSection.style.display !== 'none';
        
        const resourceFieldsSection = document.getElementById('resource-fields-section');
        const isResourceType = resourceFieldsSection && resourceFieldsSection.style.display !== 'none';
        
        let data = {};
        
        if (isPromptType) {
            // Prompt type capability
            const templateContent = document.getElementById('template_content_edit')?.value || '';
            if (!templateContent.trim()) {
                showError(t('template_content_required') || 'プロンプトテンプレートを入力してください');
                document.getElementById('template_content_edit')?.focus();
                return;
            }
            
            // Collect body parameters for arguments
            const bodyParams = buildSchemaFromTree();
            
            data = {
                name: formData.get('name'),
                capability_type: 'prompt',
                description: formData.get('description') || '',
                template_content: templateContent,
                body_params: bodyParams
            };
        } else if (isResourceType) {
            // Resource type capability
            const resourceSource = document.querySelector('input[name="resource_source"]:checked')?.value || 'existing';
            
            data = {
                name: formData.get('name'),
                capability_type: 'resource',
                description: formData.get('description') || '',
                timeout_seconds: parseInt(formData.get('timeout_seconds')) || 30
            };
            
            if (resourceSource === 'existing') {
                // Using existing global resource
                const globalResourceId = document.getElementById('global_resource_id')?.value;
                if (!globalResourceId) {
                    showError(t('capability_resource_not_selected') || 'Resourceを選択してください');
                    return;
                }
                data.global_resource_id = parseInt(globalResourceId);
                // Clear inline resource fields when using global resource
                data.resource_mime_type = null;
                data.resource_uri = null;
                data.template_content = null;
            } else {
                // New inline resource data
                const resourceName = formData.get('resource_name')?.trim();
                if (!resourceName) {
                    showError(t('resource_name_required') || 'Resource名を入力してください');
                    document.getElementById('resource_name_edit')?.focus();
                    return;
                }
                
                // Get resource content from either text input or file upload
                const resourceContent = getResourceContentEdit();
                if (!resourceContent) {
                    showError(t('resource_content_required') || 'リソースコンテンツを入力してください');
                    return;
                }
                
                // Generate Resource URI automatically from resource name
                const resourceUri = `resource://${resourceName}`;
                
                data.name = resourceName;
                data.resource_uri = resourceUri;
                data.resource_mime_type = formData.get('resource_mime_type') || 'text/plain';
                data.template_content = resourceContent;
                // Clear global_resource_id when using inline data
                data.global_resource_id = null;
            }
        } else {
            // Tool type capability (existing logic)
            const method = formData.get('method');
            
            // Collect headers
            const headers = {};
            const headerRows = document.querySelectorAll('#headers-container .key-value-row');
            headerRows.forEach(row => {
                const inputs = row.querySelectorAll('input[type="text"]');
                const key = inputs[0].value.trim();
                const value = inputs[1].value.trim();
                if (key) {
                    headers[key] = value;
                }
            });
            
            // Add HTTP method to headers
            headers['X-HTTP-Method'] = method;
            
            // Collect body parameters
            let bodyParams = {};
            if (method === 'GET') {
                const properties = {};
                const required = [];
                
                // 固定パラメータをconst制約付きでpropertiesに含める
                const fixedRows = document.querySelectorAll('#fixed-params-container .key-value-row');
                fixedRows.forEach(row => {
                    const inputs = row.querySelectorAll('input[type="text"]');
                    const key = inputs[0].value.trim();
                    const value = inputs[1].value.trim();
                    if (key) {
                        // GET固定パラメータはstring型のconst制約
                        properties[key] = {
                            type: 'string',
                            const: value,
                            default: value,
                            description: '固定値パラメータ（変更不可）'
                        };
                        required.push(key);
                    }
                });
                
                // Collect LLM parameters and build JSON Schema
                const llmRows = document.querySelectorAll('#llm-params-container .llm-param-row');
                
                llmRows.forEach(row => {
                    const name = row.querySelector('.llm-param-name').value.trim();
                    if (!name) return;
                    
                    const type = row.querySelector('.llm-param-type').value;
                    const description = row.querySelector('.llm-param-description').value.trim();
                    const defaultValue = row.querySelector('.llm-param-default').value.trim();
                    const enumValue = row.querySelector('.llm-param-enum').value.trim();
                    const isRequired = row.querySelector('.llm-param-required').checked;
                    
                    // For enum type, use string as the base type with enum constraint
                    const propDef = { type: type === 'enum' ? 'string' : type };
                    if (description) propDef.description = description;
                    
                    if (type === 'enum' && enumValue) {
                        propDef.enum = enumValue.split(',').map(v => v.trim()).filter(v => v);
                        
                        // Validate default value for enum
                        if (defaultValue && !propDef.enum.includes(defaultValue)) {
                            showError(`パラメータ "${name}": デフォルト値 "${defaultValue}" はEnum値 [${propDef.enum.join(', ')}] の中に存在しません。`);
                            row.querySelector('.llm-param-default').focus();
                            throw new Error('Invalid enum default value');
                        }
                    }
                    
                    if (defaultValue) {
                        // Try to parse as JSON for proper type conversion
                        try {
                            propDef.default = JSON.parse(defaultValue);
                        } catch {
                            propDef.default = defaultValue;
                        }
                    }
                    
                    properties[name] = propDef;
                    if (isRequired) {
                        required.push(name);
                    }
                });
                
                // Build final body_params structure
                if (Object.keys(properties).length > 0) {
                    // MCP JSON Schema format (固定パラメータもpropertiesに含まれている)
                    bodyParams = {
                        type: 'object',
                        properties: properties,
                        required: required
                    };
                }
            } else {
                // POST method: always use visual editor mode
                bodyParams = buildSchemaFromTree();
            }
            
            // URL validation: skip if baseUrl exists (relative paths are valid)
            // Skip for resource type
            const urlValue = formData.get('url')?.trim() || '';
            if (!isResourceType && !baseUrl && urlValue) {
                // No baseUrl - must be absolute URL
                if (!urlValue.startsWith('http://') && !urlValue.startsWith('https://')) {
                    showError(t('error_invalid_url') || 'URLを入力してください');
                    document.getElementById('url').focus();
                    return;
                }
            }
            
            // Build data object for tool type
            data.name = formData.get('name');
            data.capability_type = 'tool';
            data.url = urlValue;
            data.description = formData.get('description');
            data.timeout_seconds = parseInt(formData.get('timeout_seconds')) || 30;
            data.headers = headers;
            data.body_params = bodyParams;
        }
        
        try {
            await AppApi.request(`/api/capabilities/${capabilityId}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
        } catch (error) {
            showError(t('capability_update_failed') + ': ' + error.message);
            return;
        }
        
        // Update access control
        try {
            await AppApi.request(`/api/capabilities/${capabilityId}/access-control`, {
                method: 'PUT',
                body: JSON.stringify({ access_control: currentAccessControl })
            });
        } catch (error) {
            showError('Failed to update access control: ' + error.message);
            return;
        }
        
        // Save permissions if restricted
        if (currentAccessControl === 'restricted') {
            await savePermissions();
        }
        
        window.location.href = `/capabilities/${capabilityId}`;
    });
})();

// ========== Prompt機能 (Edit) ==========

// プロンプトプレビューを生成 - for edit page
function generatePromptPreviewEdit() {
    const templateContent = document.getElementById('template_content_edit')?.value || '';
    const previewOutput = document.getElementById('prompt-preview-output-edit');
    const variablesList = document.getElementById('prompt-variables-list-edit');
    
    if (!previewOutput || !variablesList) return;
    
    // テンプレートから変数を抽出
    const templateVars = extractTemplateVariables(templateContent);
    const llmParams = getLlmParamsInfo();
    
    // プレビュー生成（サンプル値で置換）
    let preview = templateContent || t('prompt_preview_empty');
    
    templateVars.forEach(varName => {
        const paramInfo = llmParams[varName];
        let sampleValue;
        
        if (paramInfo) {
            if (paramInfo.type === 'enum' && paramInfo.enum.length > 0) {
                sampleValue = `【${paramInfo.enum[0]}】`;
            } else if (paramInfo.type === 'number' || paramInfo.type === 'integer') {
                sampleValue = '【<数値>】';
            } else if (paramInfo.type === 'boolean') {
                sampleValue = '【<true/false>】';
            } else {
                sampleValue = `【<${varName}>】`;
            }
        } else {
            sampleValue = `【<${varName}>】`;
        }
        
        preview = preview.replace(new RegExp(`\\{\\{${varName}\\}\\}`, 'g'), sampleValue);
    });
    
    previewOutput.textContent = preview;
    
    // 検出された変数リストを表示
    if (templateVars.length === 0) {
        variablesList.innerHTML = `<em data-i18n="prompt_no_variables">${t('prompt_no_variables')}</em>`;
    } else {
        const varItems = templateVars.map(varName => {
            const paramInfo = llmParams[varName];
            const isDefinedInParams = !!paramInfo;
            const typeLabel = paramInfo ? paramInfo.type : 'string';
            const statusIcon = isDefinedInParams ? '✅' : '⚠️';
            const statusText = isDefinedInParams 
                ? t('prompt_var_defined')
                : t('prompt_var_not_defined');
            const description = paramInfo?.description ? ` - ${AppDom.escapeHtml(paramInfo.description)}` : '';
            
            return `
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 10px; margin-bottom: 4px; background: ${isDefinedInParams ? '#c3e6cb' : '#ffeeba'}; border-radius: 4px;">
                    <span>${statusIcon}</span>
                    <code style="font-weight: bold; background: white; padding: 2px 6px; border-radius: 3px;">{{${AppDom.escapeHtml(varName)}}}</code>
                    <span style="color: #666; font-size: 0.85rem;">(${AppDom.escapeHtml(typeLabel)})</span>
                    <span style="font-size: 0.8rem; color: #666;">${statusText}${description}</span>
                </div>
            `;
        }).join('');
        
        variablesList.innerHTML = varItems;
        
        // 未定義の変数がある場合は警告表示
        const undefinedVars = templateVars.filter(v => !llmParams[v]);
        if (undefinedVars.length > 0) {
            variablesList.innerHTML += `
                <div style="margin-top: 10px; padding: 10px; background: #fff3cd; border-radius: 4px; font-size: 0.85rem; color: #856404;">
                    ⚠️ <strong>${t('prompt_undefined_warning')}</strong><br>
                    ${t('prompt_add_llm_params')}: ${undefinedVars.map(v => `<code>{{${v}}}</code>`).join(', ')}
                </div>
            `;
        }
    }
}

// Cache bust: 2025-12-05T00:00:00
