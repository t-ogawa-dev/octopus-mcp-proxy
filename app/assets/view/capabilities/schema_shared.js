// capabilities/schema_shared.js - Helpers shared by the capability new and edit pages
// Loaded before new.js / edit.js; keep page-specific logic in those files.

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

// Hide error message
function hideError() {
    const errorDiv = document.getElementById('form-error');
    errorDiv.style.display = 'none';
}

function moveAllToDisabled() {
    const enabledSelect = document.getElementById('enabled-accounts');
    const disabledSelect = document.getElementById('disabled-accounts');
    
    Array.from(enabledSelect.options).forEach(option => {
        disabledSelect.appendChild(option);
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

function moveToEnabled() {
    const disabledSelect = document.getElementById('disabled-accounts');
    const enabledSelect = document.getElementById('enabled-accounts');
    const selected = Array.from(disabledSelect.selectedOptions);
    
    selected.forEach(option => {
        enabledSelect.appendChild(option);
    });
    
    updateCounts();
}

// Show error message
function showError(message) {
    const errorDiv = document.getElementById('form-error');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    errorDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
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

function updateCounts() {
    const enabledCount = document.getElementById('enabled-accounts').options.length;
    const disabledCount = document.getElementById('disabled-accounts').options.length;
    
    document.getElementById('enabled-count').textContent = enabledCount;
    document.getElementById('disabled-count').textContent = disabledCount;
}

// ---------------------------------------------------------------------------
// JSON Schema (body_params) builder for the POST tree editor.
// Both pages must produce identical schemas, so this is the only implementation.
// ---------------------------------------------------------------------------

// Interpret a default/fixed value typed into the form according to the parameter type
function parseValueForType(rawValue, type) {
    if (type === 'number') return parseFloat(rawValue);
    if (type === 'integer') return parseInt(rawValue, 10);
    if (type === 'boolean') return rawValue.toLowerCase() === 'true';
    if (type === 'object' || type === 'array') {
        try {
            return JSON.parse(rawValue);
        } catch {
            return rawValue;
        }
    }
    return rawValue; // string and enum keep the text exactly as typed
}

function childTreeNodes(container) {
    return container ? Array.from(container.children).filter(child => child.classList.contains('tree-node')) : [];
}

// Read {name, schema, required} from a tree node, or null when the name is empty
function readTreeNodeSchema(node) {
    const name = node.querySelector('.tree-param-name').value.trim();
    if (!name) return null;

    const type = node.querySelector('.tree-param-type').value;
    const description = node.querySelector('.tree-param-description')?.value.trim() || '';
    const defaultValue = node.querySelector('.tree-param-default')?.value.trim() || '';
    const enumValue = node.querySelector('.tree-param-enum')?.value.trim() || '';
    const isRequired = node.querySelector('.tree-param-required')?.checked || false;

    const schema = { type: type === 'enum' ? 'string' : type };
    if (type === 'enum' && enumValue) {
        schema.enum = enumValue.split(',').map(v => v.trim()).filter(v => v);
    }

    if (type === 'array') {
        const itemsType = node.querySelector('.tree-array-items-type')?.value || 'string';
        schema.items = { type: itemsType };
        if (itemsType === 'object') {
            const items = readChildSchemas(node.querySelector('.tree-array-item-properties'));
            if (Object.keys(items.properties).length > 0) {
                schema.items.properties = items.properties;
                if (items.required.length > 0) schema.items.required = items.required;
            }
        }
    }

    if (type === 'object') {
        const children = readChildSchemas(node.querySelector('.tree-children'));
        if (Object.keys(children.properties).length > 0) schema.properties = children.properties;
        if (children.required.length > 0) schema.required = children.required;
    }

    if (description) schema.description = description;
    if (defaultValue) schema.default = parseValueForType(defaultValue, type);

    return { name, schema, required: isRequired };
}

function readChildSchemas(container) {
    const properties = {};
    const required = [];
    childTreeNodes(container).forEach(child => {
        const prop = readTreeNodeSchema(child);
        if (!prop) return;
        properties[prop.name] = prop.schema;
        if (prop.required) required.push(prop.name);
    });
    return { properties, required };
}

// Value of a fixed (const) parameter node, or undefined when nothing was entered
function readFixedParamValue(node, type) {
    if (type === 'array') {
        const itemsType = node.querySelector('.tree-array-items-type')?.value || 'string';
        if (itemsType === 'object') {
            // object配列の場合、オブジェクトのカンマ区切りを配列化
            const input = node.querySelector('.tree-array-object-value')?.value.trim();
            if (!input) return [];
            try {
                const parsed = JSON.parse(`[${input}]`);
                return Array.isArray(parsed) ? parsed : [];
            } catch (e) {
                console.error('Invalid JSON for array object value:', e);
                return [];
            }
        }
        // プリミティブ型配列の場合、CSV形式のinputから取得
        const csv = node.querySelector('.tree-array-value')?.value.trim();
        if (!csv) return [];
        return csv.split(',').map(v => v.trim()).filter(v => v).map(v => parseValueForType(v, itemsType));
    }

    if (type === 'object') {
        // object型の場合、子プロパティから値を構築し、なければ値フィールドのJSONを使う
        const fromChildren = buildConstObjectValueFromChildren(node);
        if (fromChildren) return fromChildren;
    }

    const rawValue = node.querySelector('.tree-param-default')?.value.trim();
    return rawValue ? parseValueForType(rawValue, type) : undefined;
}

function buildSchemaFromTree() {
    const properties = {};
    const required = [];

    // 固定パラメータをconst制約付きでpropertiesに含める
    childTreeNodes(document.getElementById('fixed-params-post-container')).forEach(node => {
        const prop = readTreeNodeSchema(node);
        if (!prop) return;
        const constValue = readFixedParamValue(node, node.querySelector('.tree-param-type').value);
        if (constValue === undefined || constValue === null || constValue === '') return;

        properties[prop.name] = {
            ...prop.schema,
            const: constValue,
            default: constValue,
            description: prop.schema.description || '固定値パラメータ（変更不可）'
        };
        // 固定パラメータは常にrequiredに含める
        required.push(prop.name);
    });

    // LLMパラメータを追加
    childTreeNodes(document.getElementById('llm-params-tree-container')).forEach(node => {
        const prop = readTreeNodeSchema(node);
        if (!prop) return;
        properties[prop.name] = prop.schema;
        if (prop.required) required.push(prop.name);
    });

    return { type: 'object', properties, required };
}
