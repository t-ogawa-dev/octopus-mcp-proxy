// capabilities/detail.js - Capability Detail Page
const capabilityId = Number.parseInt(window.location.pathname.split('/')[2], 10);
let llmParamsSchema = { properties: {}, required: [] }; // Store LLM params schema for form generation
let currentCapabilityType = 'tool'; // Store capability type for test/preview logic
let currentTemplateContent = ''; // Store template content for prompt preview

async function loadCapability() {
    const cap = await AppApi.request(`/api/capabilities/${capabilityId}`);
    
    // Store capability type and template content
    currentCapabilityType = cap.capability_type;
    currentTemplateContent = cap.template_content || '';
    
    let baseUrl = '';
    let serviceType = 'api'; // default
    
    // Update breadcrumb links and fetch base URL
    if (cap.mcp_service_id && cap.service_id) {
        const mcpServiceId = cap.mcp_service_id;
        const serviceId = cap.service_id;
        
        document.getElementById('mcp-service-link').href = `/mcp-services/${mcpServiceId}`;
        document.getElementById('apps-link').href = `/mcp-services/${mcpServiceId}/apps`;
        document.getElementById('service-link').href = `/mcp-services/${mcpServiceId}/apps/${serviceId}`;
        document.getElementById('capabilities-link').href = `/mcp-services/${mcpServiceId}/apps/${serviceId}/capabilities`;
        
        // Fetch service name, base URL, and service type for breadcrumb
        try {
            const service = await AppApi.request(`/api/apps/${serviceId}`);
            if (service.mcp_service_name) {
                document.getElementById('mcp-service-link').textContent = service.mcp_service_name;
            }
            // Set app name in breadcrumb
            document.getElementById('service-link').textContent = service.name;
            
            baseUrl = service.mcp_url || '';
            serviceType = service.service_type || 'api';
        } catch (e) {
            console.error('Failed to fetch service info for breadcrumb:', e);
        }
    }
    
    document.getElementById('edit-link').href = `/capabilities/${capabilityId}/edit`;
    
    // Set capability name in breadcrumb (after cap is loaded)
    const breadcrumbCurrent = document.querySelector('.breadcrumb-current');
    if (breadcrumbCurrent && cap.name) {
        breadcrumbCurrent.textContent = cap.name;
    }
    
    // Build full URL display
    let urlDisplay = cap.url || 'N/A';
    if (baseUrl && cap.url && !cap.url.startsWith('http')) {
        const separator = baseUrl.endsWith('/') || cap.url.startsWith('/') ? '' : '/';
        urlDisplay = `<span style="color: #666;">${baseUrl}</span>${separator}<span style="font-weight: 600;">${cap.url}</span>`;
    }
    
    // Filter out internal headers (X-HTTP-Method)
    const displayHeaders = { ...cap.headers };
    delete displayHeaders['X-HTTP-Method'];
    
    // Parse body_params if it's a string
    let bodyParams = cap.body_params;
    if (typeof bodyParams === 'string') {
        try {
            bodyParams = JSON.parse(bodyParams);
        } catch (e) {
            bodyParams = {};
        }
    }
    
    // Separate body_params into fixed parameters (const) and LLM parameters
    const fixedParams = {};
    const llmParams = { properties: {}, required: [] };
    
    // Handle both old format (direct properties) and new format (properties wrapper)
    const properties = bodyParams.properties || bodyParams;
    
    if (properties && typeof properties === 'object') {
        for (const [key, value] of Object.entries(properties)) {
            if (value && typeof value === 'object') {
                if (value.const !== undefined) {
                    // Fixed parameter (has const constraint)
                    fixedParams[key] = value.const;
                } else {
                    // LLM parameter (no const constraint)
                    llmParams.properties[key] = value;
                    // Add to required array if marked as required
                    if (value.required === true) {
                        llmParams.required.push(key);
                    }
                }
            }
        }
        
        // Also check bodyParams.required array if exists
        if (bodyParams.required && Array.isArray(bodyParams.required)) {
            for (const key of bodyParams.required) {
                if (!fixedParams.hasOwnProperty(key) && !llmParams.required.includes(key)) {
                    llmParams.required.push(key);
                }
            }
        }
    }
    
    // Relay parameters label and description based on service type
    const relayParamsLabel = serviceType === 'mcp' 
        ? t('capability_relay_params_to_mcp')
        : t('capability_relay_params_to_api');
    const relayParamsDescription = serviceType === 'mcp'
        ? t('capability_relay_params_description_mcp')
        : t('capability_relay_params_description_api');
    
    // Build relay params structure showing actual format sent to API/MCP
    const relayParamsDisplay = {};
    
    // Add fixed params first (with actual const values)
    for (const [key, value] of Object.entries(fixedParams)) {
        relayParamsDisplay[key] = value;
    }
    
    // Add LLM params (with type placeholders)
    for (const [key, schema] of Object.entries(llmParams.properties)) {
        // Show type placeholder for LLM-set values
        const typeHint = schema.type ? `<${schema.type}>` : '<value>';
        relayParamsDisplay[key] = typeHint;
    }
    
    console.log('Final relayParamsDisplay:', JSON.stringify(relayParamsDisplay, null, 2));
    
    const relayParamsJson = Object.keys(relayParamsDisplay).length > 0 
        ? AppDom.escapeHtml(JSON.stringify(relayParamsDisplay, null, 2))
        : t('capability_no_relay_params');
    const llmParamsJson = Object.keys(llmParams.properties).length > 0 
        ? AppDom.escapeHtml(JSON.stringify(llmParams, null, 2))
        : t('capability_no_params');
    
    const container = document.getElementById('capability-detail');
    
    // Build sections based on capability type
    let typeSpecificSections = '';
    
    if (cap.capability_type === 'prompt') {
        // Prompt type: show template content instead of URL/headers/params
        const templateContent = cap.template_content || t('capability_no_template_content');
        typeSpecificSections = `
        <div class="detail-section">
            <h3>${t("capability_mcp_template_content_label")}</h3>
            <p class="text-muted" style="font-size: 0.9em; margin-bottom: 0.5rem;">${t('capability_template_content_description')}</p>
            <pre class="code-block" style="white-space: pre-wrap;">${AppDom.escapeHtml(templateContent)}</pre>
        </div>
        
        <div class="detail-section">
            <h3>${t("capability_body_params_label")}</h3>
            <p class="text-muted" style="font-size: 0.9em; margin-bottom: 0.5rem;">${t('capability_prompt_args_description')}</p>
            <pre class="code-block">${llmParamsJson}</pre>
        </div>
        `;
    } else if (cap.capability_type === 'resource') {
        // Resource type: show URI, MIME type, and content
        const resourceUri = cap.resource_uri || t('capability_resource_no_uri');
        const resourceMimeType = cap.resource_mime_type || 'text/plain';
        const resourceContent = cap.template_content || t('capability_resource_no_content');
        
        typeSpecificSections = `
        <div class="detail-section">
            <h3>${t("capability_resource_info_title")}</h3>
            <table class="detail-table">
                <tr>
                    <th>${t("capability_resource_uri_label")}</th>
                        <td><code style="font-size: 0.9em;">${AppDom.escapeHtml(resourceUri)}</code></td>
                </tr>
                <tr>
                    <th>${t("capability_resource_mime_type_label")}</th>
                        <td><span class="badge badge-method">${AppDom.escapeHtml(resourceMimeType)}</span></td>
                </tr>
            </table>
        </div>
        
        <div class="detail-section">
            <h3>${t("capability_resource_content_title")}</h3>
            <p class="text-muted" style="font-size: 0.9em; margin-bottom: 0.5rem;">${t('capability_resource_content_description')}</p>
            <pre class="code-block" style="white-space: pre-wrap; max-height: 400px; overflow-y: auto;">${AppDom.escapeHtml(resourceContent)}</pre>
        </div>
        `;
    } else {
        // Tool type: show URL, headers, params
        typeSpecificSections = `
        <div class="detail-section">
            <h3>${t("capability_individual_headers")}</h3>
            <pre class="code-block">${Object.keys(displayHeaders).length > 0 ? JSON.stringify(displayHeaders, null, 2) : t('capability_no_headers')}</pre>
        </div>
        
        <div class="detail-section">
            <h3>${relayParamsLabel}</h3>
            <p class="text-muted" style="font-size: 0.9em; margin-bottom: 0.5rem;">${relayParamsDescription}</p>
            <pre class="code-block">${relayParamsJson}</pre>
        </div>
        
        <div class="detail-section">
            <h3>${t("capability_body_params_label")}</h3>
            <p class="text-muted" style="font-size: 0.9em; margin-bottom: 0.5rem;">${t('capability_llm_params_description')}</p>
            <pre class="code-block">${llmParamsJson}</pre>
        </div>
        `;
    }
    
    container.innerHTML = `
        <div class="detail-section">
            <h2>${cap.name}</h2>
            <span class="badge badge-${cap.capability_type}">${cap.capability_type.toUpperCase()}</span>
            ${cap.description ? `<p class="text-muted">${cap.description}</p>` : ''}
        </div>
        
        <div class="detail-section">
            <h3>${t("capability_basic_info")}</h3>
            <table class="detail-table">
                <tr>
                    <th>${t("capability_type_detail")}</th>
                    <td><span class="badge badge-${cap.capability_type}">${cap.capability_type.toUpperCase()}</span></td>
                </tr>
                <tr>
                    <th>${t('access_control')}</th>
                    <td>
                        <span id="access-control-badge"></span>
                    </td>
                </tr>
                ${cap.capability_type !== 'prompt' && cap.capability_type !== 'resource' ? `
                <tr>
                    <th>${t("capability_method_label")}</th>
                    <td><span class="badge badge-method">${cap.headers['X-HTTP-Method'] || 'POST'}</span></td>
                </tr>
                <tr>
                    <th>${t("capability_url_label")}</th>
                    <td><code style="font-size: 0.9em;">${urlDisplay}</code></td>
                </tr>
                ` : ''}
                <tr>
                    <th>${t("capability_registered_at")}</th>
                    <td>${new Date(cap.created_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
                <tr>
                    <th>${t("capability_updated_at")}</th>
                    <td>${new Date(cap.updated_at).toLocaleString(currentLanguage === 'ja' ? 'ja-JP' : 'en-US')}</td>
                </tr>
            </table>
        </div>
        
        ${typeSpecificSections}
    `;
    
    // Update access control badge
    const badge = document.getElementById('access-control-badge');
    const isPublic = cap.access_control === 'public';
    
    if (isPublic) {
        badge.textContent = t('access_control_public');
        badge.style.cssText = 'padding: 4px 12px; border-radius: 4px; background-color: #d1fae5; color: #065f46; font-weight: 500; font-size: 0.875rem;';
    } else {
        badge.textContent = t('access_control_restricted');
        badge.style.cssText = 'padding: 4px 12px; border-radius: 4px; background-color: #fef3c7; color: #92400e; font-weight: 500; font-size: 0.875rem;';
    }
    
    // Store LLM params schema for test form
    llmParamsSchema = llmParams;
    
    // Update test section UI based on capability type
    updateTestSectionForType();
    
    // Generate test parameter form
    generateTestParamsForm();
}

// Update test section UI based on capability type (tool vs prompt vs resource)
function updateTestSectionForType() {
    const testSection = document.getElementById('test-section');
    const testSectionTitle = document.getElementById('test-section-title');
    const testSectionDesc = document.getElementById('test-section-desc');
    const testButton = document.getElementById('test-button');
    const testResultHeader = document.getElementById('test-result-header');
    const testParamsContainer = document.getElementById('test-params-container');
    
    if (currentCapabilityType === 'prompt') {
        // Prompt type: Preview mode
        testSection.style.display = 'block';
        testSectionTitle.textContent = t('capability_preview_title');
        testSectionDesc.textContent = t('capability_preview_desc');
        testButton.textContent = t('button_preview');
        testResultHeader.textContent = t('capability_preview_result_title');
    } else if (currentCapabilityType === 'resource') {
        // Resource type: Content is already shown in resource content section, hide test section
        testSection.style.display = 'none';
    } else {
        // Tool type: Test mode
        testSection.style.display = 'block';
        testSectionTitle.textContent = t('capability_test_title');
        testSectionDesc.textContent = t('capability_test_desc');
        testButton.textContent = t('button_test_execute');
        testResultHeader.textContent = t('capability_test_result_title');
    }
}

// Generate dynamic form fields based on LLM params schema
function generateTestParamsForm() {
    const container = document.getElementById('test-params-container');
    const properties = llmParamsSchema.properties || {};
    const required = llmParamsSchema.required || [];
    
    if (Object.keys(properties).length === 0) {
        container.innerHTML = `<p style="color: #6c757d; font-style: italic;" data-i18n="capability_test_no_params">${t('capability_test_no_params')}</p>`;
        return;
    }
    
    let html = '';
    
    for (const [key, schema] of Object.entries(properties)) {
        const isRequired = required.includes(key) || schema.required === true;
        const requiredBadge = isRequired 
            ? `<span style="background-color: #fee2e2; color: #991b1b; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-left: 8px;">${t('capability_test_required')}</span>`
            : `<span style="background-color: #e5e7eb; color: #6b7280; padding: 2px 6px; border-radius: 3px; font-size: 0.75rem; margin-left: 8px;">${t('capability_test_optional')}</span>`;
        
        const typeLabel = schema.type ? `<span style="color: #6b7280; font-size: 0.85rem; margin-left: 8px;">(${schema.type})</span>` : '';
        
        const defaultValue = schema.default !== undefined ? schema.default : getDefaultByType(schema.type);
        
        html += `<div class="form-group" style="margin-bottom: 16px;">`;
        html += `<label for="test-param-${key}" style="display: flex; align-items: center; margin-bottom: 6px;">`;
        html += `<strong>${key}</strong>${typeLabel}${requiredBadge}`;
        html += `</label>`;
        
        // Generate input based on type
        if (schema.type === 'boolean') {
            html += `<div style="display: flex; gap: 16px;">`;
            html += `<label style="display: flex; align-items: center; cursor: pointer;">`;
            html += `<input type="radio" name="test-param-${key}" id="test-param-${key}-true" value="true" ${defaultValue === true ? 'checked' : ''} style="margin-right: 6px;">`;
            html += `<span>${t('capability_test_true')}</span>`;
            html += `</label>`;
            html += `<label style="display: flex; align-items: center; cursor: pointer;">`;
            html += `<input type="radio" name="test-param-${key}" id="test-param-${key}-false" value="false" ${defaultValue !== true ? 'checked' : ''} style="margin-right: 6px;">`;
            html += `<span>${t('capability_test_false')}</span>`;
            html += `</label>`;
            html += `</div>`;
        } else if (schema.type === 'number' || schema.type === 'integer') {
            const step = schema.type === 'integer' ? '1' : 'any';
            html += `<input type="number" id="test-param-${key}" data-key="${key}" data-type="${schema.type}" step="${step}" value="${defaultValue}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 4px;">`;
        } else if (schema.type === 'array' || schema.type === 'object') {
            const placeholderValue = schema.type === 'array' ? '[]' : '{}';
            const displayValue = typeof defaultValue === 'object' ? JSON.stringify(defaultValue, null, 2) : placeholderValue;
            html += `<textarea id="test-param-${key}" data-key="${key}" data-type="${schema.type}" rows="3" style="width: 100%; padding: 10px; font-family: monospace; font-size: 0.9em; border: 1px solid #d1d5db; border-radius: 4px;">${displayValue}</textarea>`;
            html += `<small style="color: #6c757d;">JSON形式で入力</small>`;
        } else {
            // Default: string or unknown type
            html += `<input type="text" id="test-param-${key}" data-key="${key}" data-type="${schema.type || 'string'}" value="${defaultValue}" style="width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 4px;">`;
        }
        
        // Show description if available
        if (schema.description) {
            html += `<small style="color: #6c757d; display: block; margin-top: 4px;">${schema.description}</small>`;
        }
        
        // Show default value hint if available
        if (schema.default !== undefined) {
            html += `<small style="color: #3b82f6; display: block; margin-top: 2px;">${t('capability_test_default')}: ${JSON.stringify(schema.default)}</small>`;
        }
        
        html += `</div>`;
    }
    
    container.innerHTML = html;
}

// Get default value by type
function getDefaultByType(type) {
    switch (type) {
        case 'string': return '';
        case 'number': return 0;
        case 'integer': return 0;
        case 'boolean': return false;
        case 'array': return [];
        case 'object': return {};
        default: return '';
    }
}

// Collect test parameters from form
function collectTestParams() {
    const params = {};
    const properties = llmParamsSchema.properties || {};
    const required = llmParamsSchema.required || [];
    const errors = [];
    
    for (const [key, schema] of Object.entries(properties)) {
        const isRequired = required.includes(key) || schema.required === true;
        
        if (schema.type === 'boolean') {
            // Get radio button value
            const checkedRadio = document.querySelector(`input[name="test-param-${key}"]:checked`);
            params[key] = checkedRadio ? checkedRadio.value === 'true' : false;
        } else if (schema.type === 'number' || schema.type === 'integer') {
            const input = document.getElementById(`test-param-${key}`);
            const value = input ? input.value : '';
            if (value === '' && !isRequired) {
                // Skip empty optional number fields
                continue;
            }
            if (value === '' && isRequired) {
                errors.push(key);
                continue;
            }
            params[key] = schema.type === 'integer' ? parseInt(value, 10) : parseFloat(value);
        } else if (schema.type === 'array' || schema.type === 'object') {
            const input = document.getElementById(`test-param-${key}`);
            const value = input ? input.value.trim() : '';
            if (value === '' || value === '[]' || value === '{}') {
                if (isRequired) {
                    errors.push(key);
                }
                continue;
            }
            try {
                params[key] = JSON.parse(value);
            } catch (e) {
                errors.push(`${key} (JSON形式エラー)`);
            }
        } else {
            // String or unknown type
            const input = document.getElementById(`test-param-${key}`);
            const value = input ? input.value : '';
            if (value === '' && isRequired) {
                errors.push(key);
                continue;
            }
            if (value !== '' || isRequired) {
                params[key] = value;
            }
        }
    }
    
    return { params, errors };
}

async function executeTest() {
    const resultDiv = document.getElementById('test-result');
    const statusDiv = document.getElementById('test-result-status');
    const bodyPre = document.getElementById('test-result-body');
    const testButton = document.getElementById('test-button');
    
    // Collect parameters from form
    const { params, errors } = collectTestParams();
    
    // Validate required fields
    if (errors.length > 0) {
        statusDiv.textContent = `✗ ${t('capability_test_validation_error')}`;
        statusDiv.style.backgroundColor = '#fee2e2';
        statusDiv.style.color = '#991b1b';
        bodyPre.textContent = `${t('capability_test_required_missing')}: ${errors.join(', ')}`;
        resultDiv.style.display = 'block';
        return;
    }
    
    // Show loading
    testButton.disabled = true;
    
    if (currentCapabilityType === 'prompt') {
        // Prompt type: Preview template expansion (client-side)
        testButton.textContent = t('capability_preview_running');
        
        try {
            // Expand template with provided parameters
            let expandedTemplate = currentTemplateContent;
            for (const [key, value] of Object.entries(params)) {
                // Replace {{key}} patterns
                const pattern = new RegExp(`\\{\\{\\s*${key}\\s*\\}\\}`, 'g');
                expandedTemplate = expandedTemplate.replace(pattern, String(value));
            }
            
            // Show result
            resultDiv.style.display = 'block';
            statusDiv.textContent = `✓ ${t('capability_preview_success')}`;
            statusDiv.style.backgroundColor = '#d1fae5';
            statusDiv.style.color = '#065f46';
            bodyPre.textContent = expandedTemplate;
        } catch (e) {
            resultDiv.style.display = 'block';
            statusDiv.textContent = `✗ ${t('capability_preview_error')}`;
            statusDiv.style.backgroundColor = '#fee2e2';
            statusDiv.style.color = '#991b1b';
            bodyPre.textContent = e.message;
        } finally {
            testButton.disabled = false;
            testButton.textContent = t('button_preview');
        }
    } else {
        // Tool/Resource type: Call API test endpoint
        const isResource = currentCapabilityType === 'resource';
        testButton.textContent = isResource ? t('capability_resource_fetching') : t('capability_test_running');
        resultDiv.style.display = 'none';
        
        try {
            const result = await AppApi.request(`/api/capabilities/${capabilityId}/test`, {
                method: 'POST',
                body: JSON.stringify({ params })
            });
            
            // Show result
            resultDiv.style.display = 'block';
            
            if (result.success) {
                statusDiv.textContent = `✓ ${isResource ? t('capability_resource_fetch_success') : t('capability_test_success')} (HTTP ${result.status_code})`;
                statusDiv.style.backgroundColor = '#d1fae5';
                statusDiv.style.color = '#065f46';
                bodyPre.textContent = JSON.stringify(result.data, null, 2);
            } else {
                statusDiv.textContent = `✗ ${t('capability_test_error')}`;
                statusDiv.style.backgroundColor = '#fee2e2';
                statusDiv.style.color = '#991b1b';
                bodyPre.textContent = JSON.stringify(result.error, null, 2);
            }
        } catch (e) {
            resultDiv.style.display = 'block';
            statusDiv.textContent = `✗ ${t('capability_test_comm_error')}`;
            statusDiv.style.backgroundColor = '#fee2e2';
            statusDiv.style.color = '#991b1b';
            bodyPre.textContent = e.message;
        } finally {
            testButton.disabled = false;
            testButton.textContent = isResource ? t('button_resource_fetch') : t('button_test_execute');
        }
    }
}

function clearTestResult() {
    document.getElementById('test-result').style.display = 'none';
    // Reset form fields
    generateTestParamsForm();
}

// Initialize language and load capability detail
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const action = event.target.closest('[data-action]')?.dataset.action;
        if (action === 'execute-test') executeTest();
        if (action === 'clear-test') clearTestResult();
    });
    loadCapability();
})();
