// capabilities/new.js - New Capability Registration Page
const pathParts = window.location.pathname.split('/');
const mcpServiceId = Number.parseInt(pathParts[2], 10); // /mcp-services/{id}/apps/{app_id}/capabilities/new
const serviceId = Number.parseInt(pathParts[4], 10);
let headerIndex = 0;
let bodyIndex = 0;

// Debounce utility function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('form-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Hide error message
function hideError() {
    const errorDiv = document.getElementById('form-error');
    errorDiv.style.display = 'none';
}

// Load accounts list
async function loadAccounts() {
    const accounts = await AppApi.request('/api/accounts');
    
    const disabledSelect = document.getElementById('disabled-accounts');
    disabledSelect.innerHTML = accounts.map(account => 
        `<option value="${account.id}">${account.name}</option>`
    ).join('');
    
    updateCounts();
}

function moveToEnabled() {
    const disabledSelect = document.getElementById('disabled-accounts');
    const enabledSelect = document.getElementById('enabled-accounts');
    const selected = Array.from(disabledSelect.selectedOptions);
    
    selected.forEach(option => {
        enabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function moveAllToEnabled() {
    const disabledSelect = document.getElementById('disabled-accounts');
    const enabledSelect = document.getElementById('enabled-accounts');
    
    Array.from(disabledSelect.options).forEach(option => {
        enabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function moveToDisabled() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    const selected = Array.from(enabledSelect.selectedOptions);
    
    selected.forEach(option => {
        disabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function moveAllToDisabled() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    
    Array.from(enabledSelect.options).forEach(option => {
        disabledSelect.appendChild(option);
    });
    
    updateCounts();
}

function updateCounts() {
    const enabledCount = document.getElementById('enabled-accounts').options.length;
    const disabledCount = document.getElementById('disabled-accounts').options.length;
    
    document.getElementById('enabled-count').textContent = enabledCount;
    document.getElementById('disabled-count').textContent = disabledCount;
}

function toggleCapabilityType() {
    const capabilityType = document.getElementById('capability_type').value;
    const toolFields = document.getElementById('tool-fields');
    const promptFields = document.getElementById('prompt-fields');
    const resourceFields = document.getElementById('resource-fields');
    const headersGroup = document.querySelector('[data-i18n="capability_header_params"]')?.closest('.form-group');
    const bodyParamsGroup = document.getElementById('body-params-group');
    const bodyParamsLabel = document.getElementById('body-params-label');
    const bodyParamsHint = document.getElementById('body-params-hint');
    const fixedParamsSection = document.getElementById('fixed-params-section');
    const requestSamplePost = document.getElementById('request-sample-post');
    const timeoutGroup = document.getElementById('timeout_seconds')?.closest('.form-group');
    
    // Hide all type-specific fields first
    if (toolFields) toolFields.style.display = 'none';
    if (promptFields) promptFields.style.display = 'none';
    if (resourceFields) resourceFields.style.display = 'none';
    
    // Reset required fields
    const urlField = document.getElementById('url');
    const methodField = document.getElementById('method');
    const templateContentField = document.getElementById('template_content');
    const resourceUriField = document.getElementById('resource_uri');
    const resourceContentField = document.getElementById('resource_content');
    
    if (urlField) urlField.required = false;
    if (methodField) methodField.required = false;
    if (templateContentField) templateContentField.required = false;
    if (resourceUriField) resourceUriField.required = false;
    if (resourceContentField) resourceContentField.required = false;
    
    if (capabilityType === 'prompt') {
        // Show prompt fields
        if (promptFields) promptFields.style.display = 'block';
        if (headersGroup) headersGroup.style.display = 'none';
        if (bodyParamsGroup) {
            bodyParamsGroup.style.display = 'block';
            if (bodyParamsLabel) bodyParamsLabel.textContent = t('capability_template_args_label');
            if (bodyParamsHint) bodyParamsHint.textContent = t('capability_template_args_hint');
        }
        if (fixedParamsSection) fixedParamsSection.style.display = 'none';
        if (requestSamplePost) requestSamplePost.style.display = 'none';
        if (timeoutGroup) timeoutGroup.style.display = 'none';
        if (templateContentField) templateContentField.required = true;
        generatePromptPreview();
    } else if (capabilityType === 'resource') {
        // Show resource fields
        if (resourceFields) resourceFields.style.display = 'block';
        if (headersGroup) headersGroup.style.display = 'none';
        if (bodyParamsGroup) bodyParamsGroup.style.display = 'none';
        if (timeoutGroup) timeoutGroup.style.display = 'none';
        if (resourceUriField) resourceUriField.required = true;
        generateResourcePreview();
    } else {
        // Show tool fields (default)
        if (toolFields) toolFields.style.display = 'block';
        if (headersGroup) headersGroup.style.display = 'block';
        if (bodyParamsGroup) {
            bodyParamsGroup.style.display = 'block';
            if (bodyParamsLabel) bodyParamsLabel.textContent = t('capability_body_params');
            if (bodyParamsHint) bodyParamsHint.textContent = t('capability_body_json_hint');
        }
        if (fixedParamsSection) fixedParamsSection.style.display = 'block';
        if (requestSamplePost) requestSamplePost.style.display = 'block';
        if (timeoutGroup) timeoutGroup.style.display = 'block';
        if (urlField) urlField.required = true;
        if (methodField) methodField.required = true;
    }
}

function toggleBodyType() {
    const method = document.getElementById('method').value;
    const bodyKeyValue = document.getElementById('body-key-value');
    const bodyJson = document.getElementById('body-json');
    
    if (method === 'GET') {
        bodyKeyValue.style.display = 'block';
        bodyJson.style.display = 'none';
    } else {
        bodyKeyValue.style.display = 'none';
        bodyJson.style.display = 'block';
    }
}

function addHeaderRow(key = '', value = '') {
    const container = document.getElementById('headers-container');
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    row.innerHTML = `
        <input type="text" placeholder="${t('form_key_placeholder')}" value="${key}" 
               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <input type="text" placeholder="${t('form_value_placeholder')}" value="${value}" 
               style="flex: 2; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button type="button" data-action="remove-row" class="btn btn-sm btn-danger">${t('button_delete')}</button>
    `;
    container.appendChild(row);
    headerIndex++;
}

// Fixed Parameters (key-value for query strings or fixed body params)
function addFixedParamRow(key = '', value = '') {
    const container = document.getElementById('fixed-params-container');
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    row.innerHTML = `
        <input type="text" placeholder="Key" value="${key}" 
               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <input type="text" placeholder="Value (or {{VARIABLE}})" value="${value}" 
               style="flex: 2; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button type="button" data-action="remove-row" class="btn btn-sm btn-danger">${t('button_delete')}</button>
    `;
    container.appendChild(row);
}

// LLM Parameters (JSON Schema definition)
let llmParamIndex = 0;
function addLlmParamRow(paramData = null) {
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
    
    const row = document.createElement('div');
    row.className = 'llm-param-row';
    row.setAttribute('data-index', index);
    row.style.cssText = 'border: 1px solid #cce5ff; border-radius: 4px; padding: 15px; margin-bottom: 15px; background: white;';
    row.innerHTML = `
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <div>
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">パラメータ名 *</label>
                <input type="text" class="llm-param-name" value="${data.name}" placeholder="parameter_name"
                       style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;">
            </div>
            <div>
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">型 *</label>
                <select class="llm-param-type" data-action="toggle-enum" style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;">
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
            <input type="text" class="llm-param-description" value="${data.description}" placeholder="このパラメータの説明"
                   style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;">
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 10px;">
            <div>
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">デフォルト値</label>
                <input type="text" class="llm-param-default" value="${data.default}" placeholder="${data.type === 'enum' ? 'Enum値の1つを選択' : 'デフォルト値'}"
                       style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;">
                <small class="default-hint" style="display: ${data.type === 'enum' ? 'block' : 'none'}; color: #856404; font-size: 0.75rem; margin-top: 2px;">⚠️ Enum値の中から選んでください</small>
            </div>
            <div class="enum-field-container" style="display: ${data.type === 'enum' ? 'block' : 'none'};">
                <label style="font-size: 0.85rem; font-weight: 600; color: #333; display: block; margin-bottom: 4px;">Enum値 (カンマ区切り) *</label>
                <input type="text" class="llm-param-enum" value="${data.enum}" placeholder="option1,option2,option3"
                       style="width: 100%; padding: 6px 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;">
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <label style="display: flex; align-items: center; gap: 8px; font-size: 0.9rem; cursor: pointer;">
                <input type="checkbox" class="llm-param-required" ${data.required ? 'checked' : ''}
                       style="width: 16px; height: 16px; cursor: pointer;">
                <span style="font-weight: 600; color: #333;">必須パラメータ</span>
            </label>
            <button type="button" data-action="remove-row" class="btn btn-sm btn-danger">削除</button>
        </div>
    `;
    container.appendChild(row);
}

// Toggle enum field visibility based on type selection
function toggleEnumField(selectElement) {
    const row = selectElement.closest('.llm-param-row');
    const enumContainer = row.querySelector('.enum-field-container');
    const defaultInput = row.querySelector('.llm-param-default');
    const defaultHint = row.querySelector('.default-hint');
    const selectedType = selectElement.value;
    
    if (selectedType === 'enum') {
        enumContainer.style.display = 'block';
        defaultInput.placeholder = 'Enum値の1つを選択';
        if (defaultHint) defaultHint.style.display = 'block';
    } else {
        enumContainer.style.display = 'none';
        defaultInput.placeholder = 'デフォルト値';
        if (defaultHint) defaultHint.style.display = 'none';
    }
}

// ========== POST用の階層エディタ機能 ==========

let treeNodeIdCounter = 0;

// プロパティ定義からparamDataオブジェクトを構築
function buildParamDataFromProperty(name, propDef, requiredList) {
    const hasEnum = propDef.enum && propDef.enum.length > 0;
    const paramData = {
        name: name,
        type: hasEnum ? 'enum' : (propDef.type || 'string'),
        description: propDef.description || '',
        required: requiredList.includes(name),
        enum: propDef.enum ? propDef.enum.join(',') : '',
        default: propDef.default !== undefined ? JSON.stringify(propDef.default) : '',
        children: [],
        itemsType: 'string'
    };
    
    // 配列のitems型を処理
    if (propDef.type === 'array' && propDef.items) {
        paramData.itemsType = propDef.items.type || 'string';
        
        // 配列のitemsがobject型でpropertiesを持つ場合
        if (propDef.items.type === 'object' && propDef.items.properties) {
            const itemRequired = propDef.items.required || [];
            paramData.itemsProperties = Object.entries(propDef.items.properties).map(([itemPropName, itemPropDef]) => {
                return buildParamDataFromProperty(itemPropName, itemPropDef, itemRequired);
            });
        }
    }
    
    // ネストされたobjectのpropertiesを処理
    if (propDef.type === 'object' && propDef.properties) {
        const childRequired = propDef.required || [];
        paramData.children = Object.entries(propDef.properties).map(([childName, childProp]) => {
            return buildParamDataFromProperty(childName, childProp, childRequired);
        });
    }
    
    return paramData;
}

// JSONスキーマをツリー構造に読み込む
function loadSchemaToTree(schema) {
    // 固定パラメータとLLMパラメータを分離
    const fixedContainer = document.getElementById('fixed-params-post-container');
    const treeContainer = document.getElementById('llm-params-tree-container');
    
    // クリア
    fixedContainer.innerHTML = '';
    treeContainer.innerHTML = '';
    
    if (schema.properties) {
        const required = schema.required || [];
        
        Object.entries(schema.properties).forEach(([name, propDef]) => {
            const paramData = buildParamDataFromProperty(name, propDef, required);
            
            // const制約があれば固定パラメータ、なければLLMパラメータ
            if (propDef.const !== undefined) {
                // 固定パラメータ
                paramData.default = typeof propDef.const === 'object' 
                    ? JSON.stringify(propDef.const) 
                    : String(propDef.const);
                addFixedParamPostRow(paramData, 0);  // 引数順序修正
            } else {
                // LLMパラメータ
                addLlmParamTreeRow(null, 0, paramData);
            }
        });
    }
}

// 固定パラメータ（POST用・ネストなし）
function addFixedParamPostRow(paramData = null, depth = 0) {
    const container = document.getElementById('fixed-params-post-container');
    addLlmParamTreeRow(container, depth, paramData);
}

// 階層構造のLLMパラメータ追加
function addLlmParamTreeRow(containerOrParent = null, depth = 0, paramData = null) {
    const nodeId = `tree-node-${treeNodeIdCounter++}`;
    
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
    } else {
        // 親ノードが渡されている場合（後方互換性）
        container = containerOrParent.querySelector('.tree-children');
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
        itemsType: 'string'
    };
    
    const indentPx = depth * 30;
    const node = document.createElement('div');
    node.className = 'tree-node';
    node.setAttribute('data-node-id', nodeId);
    node.setAttribute('data-depth', depth);
    node.style.cssText = `margin-left: ${indentPx}px; margin-bottom: 8px; border-left: ${depth > 0 ? '2px solid #cce5ff' : 'none'}; padding-left: ${depth > 0 ? '10px' : '0'};`;
    
    const isExpandable = data.type === 'object';
    const expandButton = isExpandable ? `<button type="button" class="tree-expand-btn" data-action="toggle-tree" data-node-id="${nodeId}" style="width: 24px; height: 24px; padding: 0; margin-right: 5px; border: 1px solid #ccc; background: white; cursor: pointer; border-radius: 3px;">▼</button>` : '<span style="display: inline-block; width: 24px;"></span>';
    
    node.innerHTML = `
        <div style="border: 1px solid #cce5ff; border-radius: 4px; padding: 12px; background: white;">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: ${isExpandable || data.type === 'array' ? '10px' : '0'};">
                ${expandButton}
                <div style="flex: 1; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px;">
                    <div>
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">プロパティ名 *</label>
                        <input type="text" class="tree-param-name" placeholder="property_name"
                               style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                    </div>
                    <div>
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">型 *</label>
                        <select class="tree-param-type" data-action="tree-type" data-node-id="${nodeId}" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                            <option value="string" ${data.type === 'string' ? 'selected' : ''}>string</option>
                            <option value="number" ${data.type === 'number' ? 'selected' : ''}>number</option>
                            <option value="integer" ${data.type === 'integer' ? 'selected' : ''}>integer</option>
                            <option value="boolean" ${data.type === 'boolean' ? 'selected' : ''}>boolean</option>
                            ${!isFixedParam ? `<option value="enum" ${data.type === 'enum' ? 'selected' : ''}>enum</option>` : ''}
                            <option value="array" ${data.type === 'array' ? 'selected' : ''}>array</option>
                            <option value="object" ${data.type === 'object' ? 'selected' : ''}>object</option>
                        </select>
                    </div>
                    <div class="tree-array-items" style="display: ${data.type === 'array' ? 'block' : 'none'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">配列要素の型 *</label>
                        <select class="tree-array-items-type" data-action="tree-array-type" data-node-id="${nodeId}" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                            <option value="string" ${data.itemsType === 'string' ? 'selected' : ''}>string</option>
                            <option value="number" ${data.itemsType === 'number' ? 'selected' : ''}>number</option>
                            <option value="integer" ${data.itemsType === 'integer' ? 'selected' : ''}>integer</option>
                            <option value="boolean" ${data.itemsType === 'boolean' ? 'selected' : ''}>boolean</option>
                            <option value="object" ${data.itemsType === 'object' ? 'selected' : ''}>object</option>
                        </select>
                    </div>
                    <div class="tree-array-value-field" style="display: ${isFixedParam && data.type === 'array' && data.itemsType !== 'object' ? 'block' : 'none'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">値 (カンマ区切り)</label>
                        <input type="text" class="tree-array-value" placeholder="${
                            data.itemsType === 'string' ? 'value1, value2, value3' :
                            data.itemsType === 'number' || data.itemsType === 'integer' ? '1, 2, 3' :
                            data.itemsType === 'boolean' ? 'true, false, true' : ''
                        }" value="${data.arrayValue || ''}" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                    </div>
                    <div class="tree-array-object-value-field" style="display: ${isFixedParam && data.type === 'array' && data.itemsType === 'object' ? 'block' : 'none'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">値 (オブジェクトをカンマ区切り)</label>
                        <textarea class="tree-array-object-value" rows="4" placeholder='{"key": "value"}, {"key": "value"}' style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem; font-family: monospace;">${data.arrayObjectValue || ''}</textarea>
                    </div>
                    <div class="tree-enum-field" style="display: ${data.type === 'enum' ? 'block' : 'none'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">Enum値 *</label>
                        <input type="text" class="tree-param-enum" placeholder="opt1,opt2,opt3"
                               style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                    </div>
                    <div style="display: ${isFixedParam ? 'none' : 'block'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">説明</label>
                        <input type="text" class="tree-param-description" placeholder="説明"
                               style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                    </div>
                    <div class="tree-default-value-field" style="display: ${data.type === 'object' || data.type === 'array' ? 'none' : 'block'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">${isFixedParam ? '値' : 'デフォルト値'}</label>
                        ${data.type === 'boolean' ? 
                            (isFixedParam ? `
                                <select class="tree-param-default" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                                    <option value="true" ${data.default === 'true' || data.default === true || !data.default ? 'selected' : ''}>true</option>
                                    <option value="false" ${data.default === 'false' || data.default === false ? 'selected' : ''}>false</option>
                                </select>
                            ` : `
                                <select class="tree-param-default" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                                    <option value="" ${!data.default && data.default !== false ? 'selected' : ''}>未設定</option>
                                    <option value="true" ${data.default === 'true' || data.default === true ? 'selected' : ''}>true</option>
                                    <option value="false" ${data.default === 'false' || data.default === false ? 'selected' : ''}>false</option>
                                </select>
                            `)
                        : `
                            <input type="text" class="tree-param-default" placeholder="${isFixedParam ? '値' : 'デフォルト値'}"
                                   value="${data.default || ''}"
                                   style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                        `}
                    </div>
                    <div class="tree-object-value-field" style="display: ${isFixedParam && data.type === 'object' && depth >= 1 ? 'block' : 'none'};">
                        <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">値 (JSON形式)</label>
                        <textarea class="tree-param-default" rows="4" placeholder='{"key": "value"}' style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem; font-family: monospace;">${data.default || ''}</textarea>
                    </div>
                </div>
                <div style="display: flex; flex-direction: column; gap: 5px; justify-content: center; align-self: center;">
                    <label style="font-size: 0.85rem; display: ${isFixedParam ? 'none' : 'flex'}; align-items: center; gap: 4px; cursor: pointer; white-space: nowrap; margin-bottom: 0;">
                        <input type="checkbox" class="tree-param-required" ${data.required ? 'checked' : ''} style="width: 14px; height: 14px; margin-bottom: 0;">
                        <span style="color: #333;">必須</span>
                    </label>
                    <button type="button" data-action="remove-tree" data-node-id="${nodeId}" class="btn btn-sm btn-danger" style="font-size: 0.75rem; padding: 3px 8px;">削除</button>
                </div>
            </div>
            <div class="tree-add-child" style="display: ${isExpandable && (!isFixedParam || depth === 0) ? 'block' : 'none'}; margin-top: 8px;">
                <button type="button" data-action="add-tree-child" data-node-id="${nodeId}" class="btn btn-sm btn-primary" style="font-size: 0.8rem; padding: 4px 10px;">+ 子プロパティを追加</button>
            </div>
            <div class="tree-add-array-item-property" style="display: ${data.type === 'array' && data.itemsType === 'object' ? 'block' : 'none'}; margin-top: 8px;">
                <button type="button" data-action="add-tree-array-property" data-node-id="${nodeId}" class="btn btn-sm btn-secondary" style="font-size: 0.8rem; padding: 4px 10px;">+ 配列要素のプロパティを定義</button>
            </div>
            <div class="tree-children" style="margin-top: 10px;"></div>
            <div class="tree-array-item-properties" style="margin-top: 10px;"></div>
        </div>
    `;
    
    container.appendChild(node);
    
    // Set input values after DOM insertion to avoid template literal issues
    // Note: defaultInput value is already set in the template for boolean type (select)
    const nameInput = node.querySelector('.tree-param-name');
    const descInput = node.querySelector('.tree-param-description');
    const enumInput = node.querySelector('.tree-param-enum');
    const defaultInput = node.querySelector('.tree-param-default');
    
    if (nameInput) nameInput.value = data.name || '';
    if (descInput) descInput.value = data.description || '';
    if (enumInput) enumInput.value = data.enum || '';
    // Only set value if it's not a select element (not boolean type)
    if (defaultInput && defaultInput.tagName !== 'SELECT') {
        defaultInput.value = data.default || '';
    }
    
    // Add event listeners for prompt preview update (only for LLM params)
    if (!isFixedParam) {
        const updatePromptPreviewDebounced = debounce(generatePromptPreview, 300);
        if (nameInput) nameInput.addEventListener('input', updatePromptPreviewDebounced);
        if (descInput) descInput.addEventListener('input', updatePromptPreviewDebounced);
    }
    
    return node;
}

function toggleTreeNode(nodeId) {
    const node = document.querySelector(`[data-node-id="${nodeId}"]`);
    const childrenContainer = node.querySelector('.tree-children');
    const expandBtn = node.querySelector('.tree-expand-btn');
    
    if (childrenContainer.style.display === 'none') {
        childrenContainer.style.display = 'block';
        expandBtn.textContent = '▼';
    } else {
        childrenContainer.style.display = 'none';
        expandBtn.textContent = '▶';
    }
}

function handleTreeTypeChange(nodeId) {
    const node = document.querySelector(`[data-node-id="${nodeId}"]`);
    const typeSelect = node.querySelector('.tree-param-type');
    const arrayItemsField = node.querySelector('.tree-array-items');
    const enumField = node.querySelector('.tree-enum-field');
    const addChildBtn = node.querySelector('.tree-add-child');
    const addArrayItemPropertyBtn = node.querySelector('.tree-add-array-item-property');
    const expandBtn = node.querySelector('.tree-expand-btn');
    const defaultFieldContainer = node.querySelector('.tree-default-value-field');
    
    const selectedType = typeSelect.value;
    
    // デフォルト値フィールドを再構築（boolean型の場合はselectbox、それ以外はinput）
    if (defaultFieldContainer) {
        const currentValue = node.querySelector('.tree-param-default')?.value || '';
        const isFixedParam = node.closest('#fixed-params-post-container') !== null;
        const label = isFixedParam ? '値' : 'デフォルト値';
        
        if (selectedType === 'boolean') {
            // Boolean型: selectbox
            if (isFixedParam) {
                // 固定パラメータ: true/falseのみ、デフォルトtrue
                defaultFieldContainer.innerHTML = `
                    <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">${label}</label>
                    <select class="tree-param-default" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                        <option value="true" ${currentValue === 'true' || !currentValue ? 'selected' : ''}>true</option>
                        <option value="false" ${currentValue === 'false' ? 'selected' : ''}>false</option>
                    </select>
                `;
            } else {
                // LLMパラメータ: 未設定/true/false
                defaultFieldContainer.innerHTML = `
                    <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">${label}</label>
                    <select class="tree-param-default" style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
                        <option value="" ${!currentValue ? 'selected' : ''}>未設定</option>
                        <option value="true" ${currentValue === 'true' ? 'selected' : ''}>true</option>
                        <option value="false" ${currentValue === 'false' ? 'selected' : ''}>false</option>
                    </select>
                `;
            }
        } else {
            // それ以外: input
            // booleanから変更された場合はtrue/false値をクリア
            const shouldClearValue = (currentValue === 'true' || currentValue === 'false');
            defaultFieldContainer.innerHTML = `
                <label style="font-size: 0.75rem; font-weight: 600; color: #333; display: block; margin-bottom: 2px;">${label}</label>
                <input type="text" class="tree-param-default" placeholder="${label}" value="${shouldClearValue ? '' : currentValue}"
                       style="width: 100%; padding: 5px 6px; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;">
            `;
        }
        
        // デフォルト値フィールド表示制御 (object/arrayの場合は非表示)
        defaultFieldContainer.style.display = (selectedType === 'object' || selectedType === 'array') ? 'none' : 'block';
    }
    
    // array表示制御
    const arrayValueField = node.querySelector('.tree-array-value-field');
    const arrayObjectValueField = node.querySelector('.tree-array-object-value-field');
    const objectValueField = node.querySelector('.tree-object-value-field');
    
    if (selectedType === 'array') {
        arrayItemsField.style.display = 'block';
        addChildBtn.style.display = 'none';
        if (expandBtn) expandBtn.style.display = 'none';
        
        // Check if array items type is object
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
    } else {
        arrayItemsField.style.display = 'none';
        addArrayItemPropertyBtn.style.display = 'none';
        if (arrayValueField) arrayValueField.style.display = 'none';
        if (arrayObjectValueField) arrayObjectValueField.style.display = 'none';
        if (objectValueField) objectValueField.style.display = 'none';
    }
    
    // enum表示制御
    if (selectedType === 'enum') {
        enumField.style.display = 'block';
    } else {
        enumField.style.display = 'none';
    }
    
    // object表示制御
    const isFixedParam = node.closest('#fixed-params-post-container') !== null;
    const depth = parseInt(node.getAttribute('data-depth')) || 0;
    if (selectedType === 'object') {
        // 固定パラメータの場合、depth=0のみ子追加可能
        addChildBtn.style.display = (!isFixedParam || depth === 0) ? 'block' : 'none';
        if (expandBtn) expandBtn.style.display = 'inline-block';
        // 固定パラメータのdepth>=1の場合、object値フィールドを表示
        if (objectValueField) {
            objectValueField.style.display = (isFixedParam && depth >= 1) ? 'block' : 'none';
        }
    } else {
        addChildBtn.style.display = 'none';
        if (expandBtn) expandBtn.style.display = 'none';
    }
}

function handleArrayItemsTypeChange(nodeId) {
    const node = document.querySelector(`[data-node-id="${nodeId}"]`);
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
    console.log('addChildToTreeNode called with:', parentNodeId);
    const parentNode = document.querySelector(`[data-node-id="${parentNodeId}"]`);
    console.log('Parent node found:', parentNode);
    
    if (!parentNode) {
        console.error('Parent node not found:', parentNodeId);
        return;
    }
    
    const childrenContainer = parentNode.querySelector('.tree-children');
    console.log('Children container:', childrenContainer);
    
    if (!childrenContainer) {
        console.error('Children container not found');
        console.log('Parent node:', parentNode);
        return;
    }
    
    const depth = parseInt(parentNode.getAttribute('data-depth')) + 1;
    console.log('Adding child with depth:', depth);
    addLlmParamTreeRow(childrenContainer, depth);
    childrenContainer.style.display = 'block';
    
    // Update expand button if it exists
    const expandBtn = parentNode.querySelector('.tree-expand-btn');
    if (expandBtn) expandBtn.textContent = '▼';
}

function addArrayItemPropertyNode(nodeId) {
    const parentNode = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (!parentNode) {
        console.error('Parent node not found:', nodeId);
        return;
    }
    
    const arrayItemPropertiesContainer = parentNode.querySelector('.tree-array-item-properties');
    if (!arrayItemPropertiesContainer) {
        console.error('Array item properties container not found');
        console.log('Parent node:', parentNode);
        return;
    }
    
    const depth = parseInt(parentNode.dataset.depth) + 1;
    addLlmParamTreeRow(arrayItemPropertiesContainer, depth);
    arrayItemPropertiesContainer.style.display = 'block';
}

function removeTreeNode(nodeId) {
    const node = document.querySelector(`[data-node-id="${nodeId}"]`);
    if (node) node.remove();
}

// 固定パラメータのobject型子プロパティから値オブジェクトを構築
function buildConstObjectValueFromChildren(node) {
    const childrenContainer = node.querySelector('.tree-children');
    if (!childrenContainer) return null;
    
    const childNodes = childrenContainer.querySelectorAll(':scope > .tree-node');
    if (childNodes.length === 0) return null;
    
    const obj = {};
    childNodes.forEach(childNode => {
        const nameInput = childNode.querySelector('.tree-param-name');
        const typeSelect = childNode.querySelector('.tree-param-type');
        
        if (!nameInput || !typeSelect) return;
        
        const name = nameInput.value.trim();
        if (!name) return;
        
        const type = typeSelect.value;
        
        // 型に応じて値を取得
        if (type === 'array') {
            // array型: 配列要素の型を確認
            const arrayItemsTypeSelect = childNode.querySelector('.tree-array-items-type');
            const itemsType = arrayItemsTypeSelect ? arrayItemsTypeSelect.value : 'string';
            
            if (itemsType === 'object') {
                // object配列: tree-array-object-valueからJSON取得
                const arrayObjectValueInput = childNode.querySelector('.tree-array-object-value');
                if (arrayObjectValueInput && arrayObjectValueInput.value.trim()) {
                    try {
                        const inputValue = arrayObjectValueInput.value.trim();
                        obj[name] = JSON.parse(`[${inputValue}]`);
                    } catch (e) {
                        console.error('Invalid JSON for array object value:', e);
                        obj[name] = [];
                    }
                } else {
                    obj[name] = [];
                }
            } else {
                // プリミティブ型配列: tree-array-valueからCSV取得
                const arrayValueInput = childNode.querySelector('.tree-array-value');
                if (arrayValueInput && arrayValueInput.value.trim()) {
                    const csvValue = arrayValueInput.value.trim();
                    const arrayItems = csvValue.split(',').map(v => v.trim()).filter(v => v);
                    
                    // 型に応じて変換
                    if (itemsType === 'number') {
                        obj[name] = arrayItems.map(v => parseFloat(v));
                    } else if (itemsType === 'integer') {
                        obj[name] = arrayItems.map(v => parseInt(v));
                    } else if (itemsType === 'boolean') {
                        obj[name] = arrayItems.map(v => v.toLowerCase() === 'true');
                    } else {
                        obj[name] = arrayItems; // string
                    }
                } else {
                    obj[name] = [];
                }
            }
        } else if (type === 'object') {
            // 2階層目のobject: まず子プロパティから再帰的に構築を試み、なければtextareaからJSON取得
            const nestedObj = buildConstObjectValueFromChildren(childNode);
            if (nestedObj) {
                obj[name] = nestedObj;
            } else {
                // tree-object-value-field内のtextareaから取得
                const objectValueField = childNode.querySelector('.tree-object-value-field');
                if (objectValueField) {
                    const textarea = objectValueField.querySelector('.tree-param-default');
                    const value = textarea ? textarea.value.trim() : '';
                    if (value) {
                        try {
                            obj[name] = JSON.parse(value);
                        } catch (e) {
                            console.error('Invalid JSON for nested object:', e);
                        }
                    }
                }
            }
        } else {
            // その他の型: tree-default-value-field内のinputから取得
            const defaultValueField = childNode.querySelector('.tree-default-value-field');
            if (!defaultValueField) return;
            
            const defaultInput = defaultValueField.querySelector('.tree-param-default');
            if (!defaultInput) return;
            
            const value = defaultInput.value.trim();
            if (!value) return;
            
            // 型に応じて値を変換
            if (type === 'number') {
                obj[name] = parseFloat(value);
            } else if (type === 'integer') {
                obj[name] = parseInt(value);
            } else if (type === 'boolean') {
                obj[name] = value.toLowerCase() === 'true';
            } else {
                obj[name] = value;
            }
        }
    });
    
    return Object.keys(obj).length > 0 ? obj : null;
}

// ツリー構造からJSON Schemaを構築
function buildSchemaFromTree() {
    const properties = {};
    const required = [];
    
    // 固定パラメータをconst制約付きでpropertiesに含める
    const fixedContainer = document.getElementById('fixed-params-post-container');
    const fixedNodes = Array.from(fixedContainer.children).filter(child => child.classList.contains('tree-node'));
    
    fixedNodes.forEach(node => {
        const prop = buildPropertyFromNode(node);
        if (prop && prop.name) {
            const typeSelect = node.querySelector('.tree-param-type');
            const type = typeSelect.value;
            
            let constValue;
            
            // array型の場合、arrayValueフィールドからCSV値を取得して配列に変換
            if (type === 'array') {
                const arrayItemsTypeSelect = node.querySelector('.tree-array-items-type');
                const itemsType = arrayItemsTypeSelect ? arrayItemsTypeSelect.value : 'string';
                
                if (itemsType === 'object') {
                    // object配列の場合、オブジェクトのカンマ区切りを配列化
                    const arrayObjectValueInput = node.querySelector('.tree-array-object-value');
                    if (arrayObjectValueInput && arrayObjectValueInput.value.trim()) {
                        try {
                            // 入力値を[]で囲んで配列としてパース
                            const inputValue = arrayObjectValueInput.value.trim();
                            constValue = JSON.parse(`[${inputValue}]`);
                            // 配列であることを確認
                            if (!Array.isArray(constValue)) {
                                console.error('Array object value must be an array');
                                constValue = [];
                            }
                        } catch (e) {
                            console.error('Invalid JSON for array object value:', e);
                            constValue = [];
                        }
                    } else {
                        constValue = [];
                    }
                } else {
                    // プリミティブ型配列の場合、CSV形式のinputから取得
                    const arrayValueInput = node.querySelector('.tree-array-value');
                    if (arrayValueInput && arrayValueInput.value.trim()) {
                        const csvValue = arrayValueInput.value.trim();
                        const arrayItems = csvValue.split(',').map(v => v.trim()).filter(v => v);
                        
                        // 型に応じて配列要素を変換
                        if (itemsType === 'number') {
                            constValue = arrayItems.map(v => parseFloat(v));
                        } else if (itemsType === 'integer') {
                            constValue = arrayItems.map(v => parseInt(v));
                        } else if (itemsType === 'boolean') {
                            constValue = arrayItems.map(v => v.toLowerCase() === 'true');
                        } else {
                            constValue = arrayItems; // string
                        }
                    } else {
                        constValue = []; // 空配列
                    }
                }
            } else if (type === 'object') {
                // object型の場合、子プロパティから値を構築
                constValue = buildConstObjectValueFromChildren(node);
                
                // 子プロパティがない場合は、値フィールドからJSONをパース
                if (!constValue) {
                    const defaultValue = node.querySelector('.tree-param-default').value.trim();
                    if (defaultValue) {
                        try {
                            constValue = JSON.parse(defaultValue);
                        } catch (e) {
                            constValue = defaultValue;
                        }
                    }
                }
            } else {
                // 通常の値フィールドから取得
                const defaultValue = node.querySelector('.tree-param-default').value.trim();
                if (defaultValue) {
                    // 型に応じて値を変換
                    if (prop.schema.type === 'number' || prop.schema.type === 'integer') {
                        constValue = prop.schema.type === 'integer' ? parseInt(defaultValue) : parseFloat(defaultValue);
                    } else if (prop.schema.type === 'boolean') {
                        constValue = defaultValue.toLowerCase() === 'true';
                    } else {
                        constValue = defaultValue;
                    }
                }
            }
            
            if (constValue !== undefined && constValue !== null && constValue !== '') {
                properties[prop.name] = {
                    ...prop.schema,
                    const: constValue,
                    default: constValue,
                    description: prop.schema.description || '固定値パラメータ（変更不可）'
                };
                // 固定パラメータは常にrequiredに含める
                required.push(prop.name);
            }
        }
    });
    
    // LLMパラメータを追加
    const rootNodes = document.querySelectorAll('#llm-params-tree-container > .tree-node');
    rootNodes.forEach(node => {
        const prop = buildPropertyFromNode(node);
        if (prop && prop.name) {
            properties[prop.name] = prop.schema;
            if (prop.required) required.push(prop.name);
        }
    });
    
    if (Object.keys(properties).length > 0) {
        return {
            type: 'object',
            properties: properties,
            required: required
        };
    }
    
    return {};
}

function buildPropertyFromNode(node) {
    const nameInput = node.querySelector('.tree-param-name');
    const typeSelect = node.querySelector('.tree-param-type');
    const descriptionInput = node.querySelector('.tree-param-description');
    const defaultInput = node.querySelector('.tree-param-default');
    const enumInput = node.querySelector('.tree-param-enum');
    const arrayItemsTypeSelect = node.querySelector('.tree-array-items-type');
    const requiredCheckbox = node.querySelector('.tree-param-required');
    
    const name = nameInput.value.trim();
    if (!name) return null;
    
    const type = typeSelect.value;
    const description = descriptionInput.value.trim();
    const defaultValue = defaultInput.value.trim();
    const enumValue = enumInput ? enumInput.value.trim() : '';
    const isRequired = requiredCheckbox.checked;
    
    let schema = { type: type === 'enum' ? 'string' : type };
    if (description) schema.description = description;
    
    if (type === 'enum' && enumValue) {
        schema.enum = enumValue.split(',').map(v => v.trim()).filter(v => v);
    }
    
    if (type === 'array' && arrayItemsTypeSelect) {
        const itemsType = arrayItemsTypeSelect.value;
        schema.items = { type: itemsType };
        
        // If array items type is object, collect properties from array-item-properties container
        if (itemsType === 'object') {
            const arrayItemPropertiesContainer = node.querySelector('.tree-array-item-properties');
            const itemPropertyNodes = arrayItemPropertiesContainer.querySelectorAll(':scope > .tree-node');
            const itemProperties = {};
            const itemRequired = [];
            
            itemPropertyNodes.forEach(itemPropNode => {
                const itemProp = buildPropertyFromNode(itemPropNode);
                if (itemProp && itemProp.name) {
                    itemProperties[itemProp.name] = itemProp.schema;
                    if (itemProp.required) itemRequired.push(itemProp.name);
                }
            });
            
            if (Object.keys(itemProperties).length > 0) {
                schema.items.properties = itemProperties;
                if (itemRequired.length > 0) {
                    schema.items.required = itemRequired;
                }
            }
        }
    }
    
    if (type === 'object') {
        const childNodes = node.querySelector('.tree-children').querySelectorAll(':scope > .tree-node');
        const childProperties = {};
        const childRequired = [];
        
        childNodes.forEach(childNode => {
            const childProp = buildPropertyFromNode(childNode);
            if (childProp && childProp.name) {
                childProperties[childProp.name] = childProp.schema;
                if (childProp.required) childRequired.push(childProp.name);
            }
        });
        
        schema.properties = childProperties;
        if (childRequired.length > 0) schema.required = childRequired;
    }
    
    if (defaultValue) {
        try {
            schema.default = JSON.parse(defaultValue);
        } catch {
            schema.default = defaultValue;
        }
    }
    
    return { name, schema, required: isRequired };
}

// Initialize and setup
function validateJson() {
    const textarea = document.getElementById('body_json');
    const errorDiv = document.getElementById('json-validation-error');
    const jsonText = textarea.value.trim();
    
    if (!jsonText) {
        errorDiv.style.display = 'none';
        return;
    }
    
    try {
        JSON.parse(jsonText);
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
        const parsed = JSON.parse(jsonText);
        textarea.value = JSON.stringify(parsed, null, 2);
        errorDiv.style.display = 'none';
    } catch (e) {
        errorDiv.style.display = 'block';
        errorDiv.style.color = '#dc3545';
        errorDiv.innerHTML = '✗ ' + t('json_invalid') + ': ' + e.message;
    }
}

// Generate request sample based on current parameter definitions
function generateRequestSample() {
    const method = document.getElementById('method').value;
    const url = document.getElementById('url').value || '/api/endpoint';
    
    if (method === 'GET') {
        generateGetRequestSample(url);
    } else {
        generatePostRequestSample();
    }
}

function generateGetRequestSample(baseUrl) {
    const outputElement = document.getElementById('request-sample-output-get');
    
    // Collect fixed parameters
    const fixedParams = [];
    const fixedRows = document.querySelectorAll('#fixed-params-container .key-value-row');
    fixedRows.forEach(row => {
        const inputs = row.querySelectorAll('input[type="text"]');
        const key = inputs[0].value.trim();
        const value = inputs[1].value.trim();
        if (key) {
            // Query parameters don't need quotes - they're all strings by nature
            fixedParams.push(`${key}=${value}`);
        }
    });
    
    // Collect LLM parameters
    const llmParams = [];
    const llmRows = document.querySelectorAll('#llm-params-container .llm-param-row');
    llmRows.forEach(row => {
        const name = row.querySelector('.llm-param-name').value.trim();
        const type = row.querySelector('.llm-param-type').value;
        if (name) {
            let sampleValue;
            if (type === 'enum') {
                const enumValues = row.querySelector('.llm-param-enum').value.trim();
                sampleValue = enumValues ? enumValues.split(',')[0].trim() : '<string>';
            } else if (type === 'string') {
                sampleValue = '<string>';
            } else if (type === 'number' || type === 'integer') {
                sampleValue = '<number>';
            } else if (type === 'boolean') {
                sampleValue = '<boolean>';
            }
            llmParams.push(`${name}=${sampleValue}`);
        }
    });
    
    const allParams = [...fixedParams, ...llmParams];
    const queryString = allParams.length > 0 ? '?' + allParams.join('&') : '';
    const fullUrl = `${baseUrl}${queryString}`;
    
    outputElement.textContent = fullUrl || '(パラメータを追加してください)';
}

function generatePostRequestSample() {
    const outputElement = document.getElementById('request-sample-output-post');
    
    // Visual editor mode - build sample from tree
    const sampleBody = {};
    
    // Add fixed parameters from tree structure
    const fixedNodes = document.querySelectorAll('#fixed-params-post-container > .tree-node');
    fixedNodes.forEach(node => {
        const name = node.querySelector('.tree-param-name').value.trim();
        const type = node.querySelector('.tree-param-type').value;
        
        if (!name) return;
        
        // array型の場合、arrayValueフィールドから値を取得
        if (type === 'array') {
            const arrayItemsTypeSelect = node.querySelector('.tree-array-items-type');
            const itemsType = arrayItemsTypeSelect ? arrayItemsTypeSelect.value : 'string';
            
            if (itemsType === 'object') {
                // object配列の場合、オブジェクトのカンマ区切りを配列化
                const arrayObjectValueInput = node.querySelector('.tree-array-object-value');
                if (arrayObjectValueInput && arrayObjectValueInput.value.trim()) {
                    try {
                        const inputValue = arrayObjectValueInput.value.trim();
                        sampleBody[name] = JSON.parse(`[${inputValue}]`);
                    } catch (e) {
                        console.error('Invalid JSON for array object value:', e);
                        sampleBody[name] = [];
                    }
                }
            } else {
                // プリミティブ型配列の場合、CSV形式のinputから取得
                const arrayValueInput = node.querySelector('.tree-array-value');
                if (arrayValueInput && arrayValueInput.value.trim()) {
                    const csvValue = arrayValueInput.value.trim();
                    const arrayItems = csvValue.split(',').map(v => v.trim()).filter(v => v);
                    
                    // 型に応じて変換
                    if (itemsType === 'number') {
                        sampleBody[name] = arrayItems.map(v => parseFloat(v));
                    } else if (itemsType === 'integer') {
                        sampleBody[name] = arrayItems.map(v => parseInt(v));
                    } else if (itemsType === 'boolean') {
                        sampleBody[name] = arrayItems.map(v => v.toLowerCase() === 'true');
                    } else {
                        sampleBody[name] = arrayItems; // string
                    }
                }
            }
        } else if (type === 'object') {
            // object型の場合、子プロパティから値を構築
            const objValue = buildConstObjectValueFromChildren(node);
            
            // 子プロパティがない場合は、値フィールドからJSONをパース
            if (objValue) {
                sampleBody[name] = objValue;
            } else {
                const defaultValue = node.querySelector('.tree-param-default').value.trim();
                if (defaultValue) {
                    try {
                        sampleBody[name] = JSON.parse(defaultValue);
                    } catch (e) {
                        sampleBody[name] = defaultValue;
                    }
                }
            }
        } else {
            // 通常の型
            const defaultValue = node.querySelector('.tree-param-default').value.trim();
            if (defaultValue) {
                // Convert value based on type
                let value = defaultValue;
                if (type === 'number') {
                    value = parseFloat(defaultValue);
                } else if (type === 'integer') {
                    value = parseInt(defaultValue);
                } else if (type === 'boolean') {
                    value = defaultValue.toLowerCase() === 'true';
                }
                sampleBody[name] = value;
            }
        }
    });
    
    // Add LLM parameters from tree
    const rootNodes = document.querySelectorAll('#llm-params-tree-container > .tree-node');
    rootNodes.forEach(node => {
        const name = node.querySelector('.tree-param-name').value.trim();
        if (name) {
            sampleBody[name] = generateSampleValue(node);
        }
    });
    
    outputElement.textContent = JSON.stringify(sampleBody, null, 2);
}

function generateSampleValue(node) {
    const type = node.querySelector('.tree-param-type').value;
    
    if (type === 'string') {
        return '<string>';
    } else if (type === 'number' || type === 'integer') {
        return '<number>';
    } else if (type === 'boolean') {
        return '<boolean>';
    } else if (type === 'enum') {
        const enumValues = node.querySelector('.tree-param-enum').value.trim();
        return enumValues ? `"${enumValues.split(',')[0].trim()}"` : '<string>';
    } else if (type === 'array') {
        const itemsType = node.querySelector('.tree-array-items-type').value;
        if (itemsType === 'object') {
            // Build sample object from array item properties
            const arrayItemPropertiesContainer = node.querySelector('.tree-array-item-properties');
            const itemPropertyNodes = arrayItemPropertiesContainer.querySelectorAll(':scope > .tree-node');
            const sampleItem = {};
            itemPropertyNodes.forEach(itemNode => {
                const itemName = itemNode.querySelector('.tree-param-name').value.trim();
                if (itemName) {
                    sampleItem[itemName] = generateSampleValue(itemNode);
                }
            });
            return [sampleItem];
        } else {
            // Simple type array
            const sampleValue = itemsType === 'string' ? '<string>' : 
                               itemsType === 'number' || itemsType === 'integer' ? '<number>' : 
                               itemsType === 'boolean' ? '<boolean>' : '<value>';
            return [sampleValue];
        }
    } else if (type === 'object') {
        const childrenContainer = node.querySelector('.tree-children');
        const childNodes = childrenContainer.querySelectorAll(':scope > .tree-node');
        const sampleObj = {};
        childNodes.forEach(childNode => {
            const childName = childNode.querySelector('.tree-param-name').value.trim();
            if (childName) {
                sampleObj[childName] = generateSampleValue(childNode);
            }
        });
        return sampleObj;
    }
    
    return '<value>';
}

// Initialize and setup
(async () => {
    await initLanguageSwitcher();
    
    // Initialize body type
    toggleBodyType();
    
    // Load accounts
    await loadAccounts();
    
    // Load existing resources for selection
    await loadExistingResources();

    setupStaticEventListeners();
    
    // Setup drag and drop for resource file upload
    const dropZone = document.getElementById('resource-drop-zone');
    if (dropZone) {
        // Prevent default drag behaviors
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });
        
        // Highlight drop zone when dragging over
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = '#e6f7ff';
                dropZone.style.borderColor = '#1890ff';
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.style.backgroundColor = '#f7fafc';
                dropZone.style.borderColor = '#cbd5e0';
            });
        });
        
        // Handle dropped files
        dropZone.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleResourceFileUpload(files[0]);
            }
        });
        
        // Click to select file
        dropZone.addEventListener('click', (e) => {
            // ボタンクリックでない場合のみ
            if (e.target.tagName !== 'BUTTON') {
                document.getElementById('resource_file')?.click();
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
    
    // Setup form submit handler
    document.getElementById('capability-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        hideError();
        
        const formData = new FormData(e.target);
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
            // POST method - always use visual editor mode
            bodyParams = buildSchemaFromTree();
        }
        
        const data = {
            name: formData.get('name'),
            capability_type: formData.get('capability_type') || 'tool',
            url: formData.get('url'),
            description: formData.get('description'),
            timeout_seconds: parseInt(formData.get('timeout_seconds')) || 30,
            template_content: formData.get('template_content'),
            headers: headers,
            body_params: bodyParams
        };
        
        // Resource type specific fields
        const capabilityType = formData.get('capability_type');
        if (capabilityType === 'resource') {
            const resourceSource = document.querySelector('input[name="resource_source"]:checked')?.value || 'existing';
            
            if (resourceSource === 'existing') {
                // Use existing resource
                const existingResourceId = document.getElementById('existing_resource_id')?.value;
                if (!existingResourceId) {
                    showError(t('capability_resource_not_selected') || 'Resourceを選択してください');
                    return;
                }
                // Store the global resource ID
                data.global_resource_id = parseInt(existingResourceId);
            } else {
                // Create new resource inline
                const newResourceName = formData.get('new_resource_name')?.trim();
                if (!newResourceName) {
                    showError(t('resource_name_required') || 'Resource名を入力してください');
                    document.getElementById('new_resource_name')?.focus();
                    return;
                }
                data.resource_name = newResourceName;
                data.resource_uri = formData.get('resource_uri');
                data.resource_mime_type = formData.get('resource_mime_type');
                // Get content from text input or uploaded file
                data.template_content = getResourceContent();
            }
        }
        
        // Add HTTP method to headers (only for tool type)
        if (capabilityType === 'tool') {
            data.headers['X-HTTP-Method'] = method;
        }
        
        // Collect enabled account IDs
        const enabledSelect = document.getElementById('enabled-accounts');
        const accountIds = Array.from(enabledSelect.options).map(opt => parseInt(opt.value));
        data.account_ids = accountIds;
        
        await AppApi.request(`/api/apps/${serviceId}/capabilities`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
            window.location.href = `/mcp-services/${mcpServiceId}/apps/${serviceId}/capabilities`;
    });
})();

// ========== Prompt Preview機能 ==========

// テンプレートから変数を抽出
function extractTemplateVariables(template) {
    const regex = /\{\{([a-zA-Z_][a-zA-Z0-9_]*)\}\}/g;
    const variables = [];
    let match;
    while ((match = regex.exec(template)) !== null) {
        if (!variables.includes(match[1])) {
            variables.push(match[1]);
        }
    }
    return variables;
}

// LLMパラメータから変数情報を取得
function getLlmParamsInfo() {
    const params = {};
    const treeNodes = document.querySelectorAll('#llm-params-tree-container > .tree-node');
    
    treeNodes.forEach(node => {
        const nameInput = node.querySelector('.tree-param-name');
        const typeSelect = node.querySelector('.tree-param-type');
        const descInput = node.querySelector('.tree-param-description');
        const requiredCheck = node.querySelector('.tree-param-required');
        const enumInput = node.querySelector('.tree-param-enum');
        
        if (nameInput && nameInput.value.trim()) {
            const name = nameInput.value.trim();
            const type = typeSelect ? typeSelect.value : 'string';
            params[name] = {
                type: type,
                description: descInput ? descInput.value.trim() : '',
                required: requiredCheck ? requiredCheck.checked : false,
                enum: enumInput ? enumInput.value.trim().split(',').filter(v => v.trim()) : []
            };
        }
    });
    
    return params;
}

// プロンプトプレビューを生成
function generatePromptPreview() {
    const templateContent = document.getElementById('template_content')?.value || '';
    const previewOutput = document.getElementById('prompt-preview-output');
    const variablesList = document.getElementById('prompt-variables-list');
    
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
            const description = paramInfo?.description ? ` - ${paramInfo.description}` : '';
            
            return `
                <div style="display: flex; align-items: center; gap: 8px; padding: 6px 10px; margin-bottom: 4px; background: ${isDefinedInParams ? '#c3e6cb' : '#ffeeba'}; border-radius: 4px;">
                    <span>${statusIcon}</span>
                    <code style="font-weight: bold; background: white; padding: 2px 6px; border-radius: 3px;">{{${varName}}}</code>
                    <span style="color: #666; font-size: 0.85rem;">(${typeLabel})</span>
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

// ========== Resource機能 ==========

// Resource入力タイプ切り替え（テキスト/ファイル）
function toggleResourceInputType() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    const textInput = document.getElementById('resource-text-input');
    const fileInput = document.getElementById('resource-file-input');
    
    if (inputType === 'file') {
        if (textInput) textInput.style.display = 'none';
        if (fileInput) fileInput.style.display = 'block';
    } else {
        if (textInput) textInput.style.display = 'block';
        if (fileInput) fileInput.style.display = 'none';
    }
}

// Resource source toggle (existing vs new)
function toggleResourceSource() {
    const resourceSource = document.querySelector('input[name="resource_source"]:checked')?.value || 'existing';
    const existingSection = document.getElementById('existing-resource-section');
    const newSection = document.getElementById('new-resource-section');
    
    if (resourceSource === 'existing') {
        if (existingSection) existingSection.style.display = 'block';
        if (newSection) newSection.style.display = 'none';
    } else {
        if (existingSection) existingSection.style.display = 'none';
        if (newSection) newSection.style.display = 'block';
    }
}

// Load existing resources into select
let globalResources = [];
async function loadExistingResources() {
    try {
        globalResources = await AppApi.request('/api/resources');
        
        const selectElement = document.getElementById('existing_resource_id');
        if (selectElement) {
            // Keep placeholder option
            selectElement.innerHTML = `<option value="" data-i18n="capability_select_resource_placeholder">-- Resourceを選択してください --</option>` +
                globalResources.filter(r => r.is_enabled).map(resource => 
                    `<option value="${resource.id}">${resource.name} (${resource.mime_type})</option>`
                ).join('');
        }
    } catch (e) {
        console.error('Failed to load resources:', e);
    }
}

// Load and preview selected existing resource
async function loadExistingResourcePreview() {
    const selectElement = document.getElementById('existing_resource_id');
    const resourceId = selectElement?.value;
    const previewDiv = document.getElementById('selected-resource-preview');
    
    if (!resourceId) {
        if (previewDiv) previewDiv.style.display = 'none';
        return;
    }
    
    const selectedResource = globalResources.find(r => r.id === parseInt(resourceId));
    if (!selectedResource) return;
    
    // Display resource info
    document.getElementById('selected-resource-name').textContent = selectedResource.name;
    document.getElementById('selected-resource-uri').textContent = selectedResource.uri;
    document.getElementById('selected-resource-mime').textContent = selectedResource.mime_type;
    document.getElementById('selected-resource-desc').textContent = selectedResource.description || '-';
    
    if (previewDiv) previewDiv.style.display = 'block';
}

// ファイルアップロード処理
let uploadedResourceContent = null;
function handleResourceFileUpload(file) {
    // 引数がない場合はinputから取得
    if (!file) {
        const fileInput = document.getElementById('resource_file');
        file = fileInput?.files[0];
    }
    
    if (!file) return;
    
    // ファイルサイズチェック (1MB)
    if (file.size > 1024 * 1024) {
        modal.error(t('resource_file_too_large') || 'ファイルサイズが1MBを超えています');
        const fileInput = document.getElementById('resource_file');
        if (fileInput) fileInput.value = '';
        return;
    }
    
    const reader = new FileReader();
    reader.onload = function(e) {
        uploadedResourceContent = e.target.result;
        
        // プレビュー表示
        const previewDiv = document.getElementById('resource-file-preview');
        const fileNameSpan = document.getElementById('resource-file-name');
        const fileSizeSpan = document.getElementById('resource-file-size');
        
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
        
        generateResourcePreview();
    };
    reader.readAsText(file);
}

// ファイルクリア
function clearResourceFile() {
    const fileInput = document.getElementById('resource_file');
    const previewDiv = document.getElementById('resource-file-preview');
    
    if (fileInput) fileInput.value = '';
    if (previewDiv) previewDiv.style.display = 'none';
    uploadedResourceContent = null;
    generateResourcePreview();
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
        if (action === 'select-resource-file') document.getElementById('resource_file').click();
        if (action === 'clear-resource-file') clearResourceFile();
    });

    document.addEventListener('change', (event) => {
        const action = event.target.dataset.action;
        if (action === 'toggle-capability-type') toggleCapabilityType();
        if (action === 'toggle-body-type') toggleBodyType();
        if (action === 'toggle-resource-source') toggleResourceSource();
        if (action === 'toggle-resource-input') toggleResourceInputType();
        if (action === 'load-resource-preview') loadExistingResourcePreview();
        if (action === 'resource-file-input' && event.target.files[0]) {
            handleResourceFileUpload(event.target.files[0]);
        }
        if (action === 'tree-type') handleTreeTypeChange(event.target.dataset.nodeId);
        if (action === 'tree-array-type') handleArrayItemsTypeChange(event.target.dataset.nodeId);
    });

    document.addEventListener('input', (event) => {
        if (event.target.dataset.action === 'prompt-preview-input') generatePromptPreview();
        if (event.target.dataset.action === 'resource-preview-input') generateResourcePreview();
    });
}

// リソースプレビュー生成
function generateResourcePreview() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    const previewOutput = document.getElementById('resource-preview-output');
    
    if (!previewOutput) return;
    
    let content = '';
    if (inputType === 'file' && uploadedResourceContent) {
        content = uploadedResourceContent;
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
        previewOutput.textContent = t('resource_preview_empty');
    }
}

// リソースコンテンツを取得（保存時に使用）
function getResourceContent() {
    const inputType = document.querySelector('input[name="resource_input_type"]:checked')?.value || 'text';
    
    if (inputType === 'file' && uploadedResourceContent) {
        return uploadedResourceContent;
    }
    return document.getElementById('resource_content')?.value || '';
}
// Cache bust: 2026-01-21T00:00:00
