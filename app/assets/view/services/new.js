// services/new.js - Service Registration Page
let headerIndex = 0;
let envIndex = 0;

function toggleServiceType() {
    const serviceType = document.querySelector('input[name="service_type"]:checked').value;
    const mcpConfigSection = document.getElementById('mcp-config-section');
    const mcpUrlSection = document.getElementById('mcp-url-section');
    const mcpUrlInput = document.getElementById('mcp_url');
    const mcpUrlLabel = document.querySelector('#mcp-url-label span:first-child');
    const mcpUrlRequired = document.getElementById('mcp-url-required');
    const mcpUrlHint = document.getElementById('mcp-url-hint');
    const testConnectionBtn = document.getElementById('test-connection-btn');
    
    if (serviceType === 'mcp') {
        mcpConfigSection.style.display = 'block';
        // Reset to HTTP transport by default
        document.querySelector('input[name="mcp_transport"][value="http"]').checked = true;
        toggleMcpTransport();
    } else {
        // API type - show URL field without MCP config section
        mcpConfigSection.style.display = 'none';
        
        // Show mcp_url field for API base URL (optional)
        mcpUrlSection.style.display = 'block';
        mcpUrlInput.removeAttribute('required');
        if (mcpUrlLabel) {
            mcpUrlLabel.setAttribute('data-i18n', 'app_api_base_url_label');
            mcpUrlLabel.textContent = t('app_api_base_url_label');
        }
        if (mcpUrlRequired) mcpUrlRequired.textContent = '';
        if (mcpUrlHint) {
            mcpUrlHint.setAttribute('data-i18n', 'app_api_base_url_hint');
            mcpUrlHint.textContent = t('app_api_base_url_hint');
        }
        if (mcpUrlInput) mcpUrlInput.placeholder = 'https://api.example.com/v1/';
        if (testConnectionBtn) testConnectionBtn.style.display = 'none';
    }
}

function toggleMcpTransport() {
    const transport = document.querySelector('input[name="mcp_transport"]:checked').value;
    const mcpUrlSection = document.getElementById('mcp-url-section');
    const stdioConfigSection = document.getElementById('stdio-config-section');
    const mcpUrlInput = document.getElementById('mcp_url');
    const stdioCommandInput = document.getElementById('stdio_command');
    
    if (transport === 'http') {
        mcpUrlSection.style.display = 'block';
        stdioConfigSection.style.display = 'none';
        mcpUrlInput.setAttribute('required', 'required');
        if (stdioCommandInput) stdioCommandInput.removeAttribute('required');
    } else {
        // stdio
        mcpUrlSection.style.display = 'none';
        stdioConfigSection.style.display = 'block';
        mcpUrlInput.removeAttribute('required');
        if (stdioCommandInput) stdioCommandInput.setAttribute('required', 'required');
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

function addEnvRow(key = '', value = '') {
    const container = document.getElementById('env-container');
    const row = document.createElement('div');
    row.className = 'key-value-row';
    row.style.cssText = 'display: flex; gap: 10px; margin-bottom: 10px; align-items: center;';
    row.innerHTML = `
        <input type="text" placeholder="${t('form_env_key_placeholder') || '環境変数名 (例: API_KEY)'}" value="${key}" 
               style="flex: 1; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <input type="text" placeholder="${t('form_env_value_placeholder') || '値 または {{VARIABLE}}'}" value="${value}" 
               style="flex: 2; padding: 8px; border: 1px solid #ddd; border-radius: 4px;">
        <button type="button" data-action="remove-row" class="btn btn-sm btn-danger">${t('button_delete')}</button>
    `;
    container.appendChild(row);
    envIndex++;
}

async function testConnection() {
    const mcpUrl = document.getElementById('mcp_url').value.trim();
    const resultDiv = document.getElementById('connection-test-result');
    
    if (!mcpUrl) {
        resultDiv.style.display = 'block';
        resultDiv.style.padding = '12px';
        resultDiv.style.borderRadius = '6px';
        resultDiv.style.backgroundColor = '#fee';
        resultDiv.style.border = '1px solid #fcc';
        resultDiv.style.color = '#c33';
        resultDiv.textContent = t('app_mcp_url_required') || 'MCP接続URLを入力してください';
        return false;
    }
    
    // Collect common headers
    const commonHeaders = {};
    const headerRows = document.querySelectorAll('#headers-container .key-value-row');
    headerRows.forEach(row => {
        const inputs = row.querySelectorAll('input[type="text"]');
        const key = inputs[0].value.trim();
        const value = inputs[1].value.trim();
        if (key) {
            commonHeaders[key] = value;
        }
    });
    
    // Show loading state
    resultDiv.style.display = 'block';
    resultDiv.style.padding = '12px';
    resultDiv.style.borderRadius = '6px';
    resultDiv.style.backgroundColor = '#f0f9ff';
    resultDiv.style.border = '1px solid #bae6fd';
    resultDiv.style.color = '#0369a1';
    resultDiv.textContent = t('app_testing_connection') || '接続テスト中...';
    
    try {
        const response = await fetch('/api/apps/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                mcp_url: mcpUrl,
                common_headers: commonHeaders
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Success
            resultDiv.style.backgroundColor = '#d1fae5';
            resultDiv.style.border = '1px solid #10b981';
            resultDiv.style.color = '#065f46';
            resultDiv.textContent = '✓ ' + (t('app_connection_success') || '接続成功');
            return true;
        } else {
            // Failure
            resultDiv.style.backgroundColor = '#fee';
            resultDiv.style.border = '1px solid #fcc';
            resultDiv.style.color = '#c33';
            resultDiv.textContent = '✗ ' + (result.error || t('app_connection_failed') || '接続失敗');
            return false;
        }
    } catch (e) {
        // Error
        resultDiv.style.backgroundColor = '#fee';
        resultDiv.style.border = '1px solid #fcc';
        resultDiv.style.color = '#c33';
        resultDiv.textContent = '✗ ' + (t('app_connection_error') || '接続エラー') + ': ' + e.message;
        return false;
    }
}

async function testStdioConnection() {
    const command = document.getElementById('stdio_command').value.trim();
    const argsText = document.getElementById('stdio_args').value.trim();
    const resultDiv = document.getElementById('stdio-test-result');
    
    if (!command) {
        resultDiv.style.display = 'block';
        resultDiv.style.padding = '12px';
        resultDiv.style.borderRadius = '6px';
        resultDiv.style.backgroundColor = '#fee';
        resultDiv.style.border = '1px solid #fcc';
        resultDiv.style.color = '#c33';
        resultDiv.textContent = t('app_stdio_command_required') || 'コマンドを入力してください';
        return false;
    }
    
    // Parse args (one per line)
    const args = argsText ? argsText.split('\n').map(line => line.trim()).filter(line => line) : [];
    
    // Collect environment variables
    const env = {};
    const envRows = document.querySelectorAll('#env-container .key-value-row');
    envRows.forEach(row => {
        const inputs = row.querySelectorAll('input[type="text"]');
        const key = inputs[0].value.trim();
        const value = inputs[1].value.trim();
        if (key) {
            env[key] = value;
        }
    });
    
    const cwd = document.getElementById('stdio_cwd').value.trim() || null;
    
    // Show loading state
    resultDiv.style.display = 'block';
    resultDiv.style.padding = '12px';
    resultDiv.style.borderRadius = '6px';
    resultDiv.style.backgroundColor = '#f0f9ff';
    resultDiv.style.border = '1px solid #bae6fd';
    resultDiv.style.color = '#0369a1';
    resultDiv.textContent = t('app_testing_connection') || '接続テスト中...';
    
    try {
        const response = await fetch('/api/apps/test-stdio-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                command: command,
                args: args,
                env: env,
                cwd: cwd
            })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            // Success
            resultDiv.style.backgroundColor = '#d1fae5';
            resultDiv.style.border = '1px solid #10b981';
            resultDiv.style.color = '#065f46';
            let successMsg = '✓ ' + (t('app_connection_success') || '接続成功');
            if (result.tools && result.tools.length > 0) {
                successMsg += ` (${result.tools.length} ${t('tools_detected') || 'ツール検出'})`;
            }
            resultDiv.textContent = successMsg;
            return true;
        } else {
            // Failure
            resultDiv.style.backgroundColor = '#fee';
            resultDiv.style.border = '1px solid #fcc';
            resultDiv.style.color = '#c33';
            resultDiv.textContent = '✗ ' + (result.error || t('app_connection_failed') || '接続失敗');
            return false;
        }
    } catch (e) {
        // Error
        resultDiv.style.backgroundColor = '#fee';
        resultDiv.style.border = '1px solid #fcc';
        resultDiv.style.color = '#c33';
        resultDiv.textContent = '✗ ' + (t('app_connection_error') || '接続エラー') + ': ' + e.message;
        return false;
    }
}

// Initialize and setup form
(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const element = event.target.closest('[data-action]');
        if (!element) return;
        const action = element.dataset.action;
        if (action === 'remove-row') element.closest('.key-value-row')?.remove();
        if (action === 'add-env') addEnvRow();
        if (action === 'add-header') addHeaderRow();
        if (action === 'test-connection') testConnection();
        if (action === 'test-stdio') testStdioConnection();
    });
    document.addEventListener('change', (event) => {
        if (event.target.dataset.action === 'service-type') toggleServiceType();
        if (event.target.dataset.action === 'mcp-transport') toggleMcpTransport();
    });
    
    // URLからMCPサービスIDを取得
    const pathParts = window.location.pathname.split('/');
    const mcpServiceId = pathParts[2]; // /mcp-services/{id}/apps/new
    
    if (!mcpServiceId) {
        console.error('MCP Service ID not found in URL');
        await modal.error('MCPサービスIDが見つかりません');
        window.location.href = '/mcp-services';
        return;
    }
    
    // Check if this is a template-based registration
    const urlParams = new URLSearchParams(window.location.search);
    const isFromTemplate = urlParams.has('from') && urlParams.get('from') === 'template';
    
    // If not from template, clear any existing template data
    if (!isFromTemplate) {
        sessionStorage.removeItem('app_template_data');
    }
    
    // Check for template data in sessionStorage
    const templateDataStr = sessionStorage.getItem('app_template_data');
    let templateCapabilities = null;
    
    if (templateDataStr) {
        try {
            const templateData = JSON.parse(templateDataStr);
            
            // Save capabilities for later use
            if (templateData.capabilities) {
                templateCapabilities = templateData.capabilities;
            }
            
            // Fill form with template data
            if (templateData.name) {
                document.getElementById('name').value = templateData.name;
            }
            if (templateData.description) {
                document.getElementById('description').value = templateData.description;
            }
            if (templateData.service_type) {
                document.querySelector(`input[name="service_type"][value="${templateData.service_type}"]`).checked = true;
                toggleServiceType();
            }
            if (templateData.mcp_url) {
                document.getElementById('mcp_url').value = templateData.mcp_url;
            }
            
            // Fill common headers
            if (templateData.common_headers && Object.keys(templateData.common_headers).length > 0) {
                // Clear default header row
                document.getElementById('headers-container').innerHTML = '';
                
                // Add headers from template
                Object.entries(templateData.common_headers).forEach(([key, value]) => {
                    addHeaderRow(key, value);
                });
            } else {
                // Add initial empty header row
                addHeaderRow();
            }
            
            // Show info message
            if (templateData.official_url) {
                const infoDiv = document.createElement('div');
                infoDiv.style.cssText = 'margin-bottom: 20px; padding: 12px; background: #f0f9ff; border: 1px solid #bae6fd; border-radius: 6px; color: #0369a1;';
                infoDiv.textContent = `📚 ${t('app_template_creating')}: ${templateData.name}`;
                const safeOfficialUrl = AppDom.safeHttpUrl(templateData.official_url);
                if (safeOfficialUrl) {
                    const link = document.createElement('a');
                    link.href = safeOfficialUrl;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.style.cssText = 'color: #0369a1; text-decoration: underline; display: block;';
                    link.textContent = t('app_template_official_docs');
                    infoDiv.appendChild(link);
                }
                
                // If API template with capabilities, show capability count
                if (templateData.service_type === 'api' && templateCapabilities && templateCapabilities.length > 0) {
                    const count = document.createElement('div');
                    count.textContent = `📌 ${templateCapabilities.length}${t('app_template_capabilities_auto_register')}`;
                    infoDiv.appendChild(count);
                }
                
                document.querySelector('form').insertBefore(infoDiv, document.querySelector('form').firstChild);
            }
            
            // Don't clear template data yet - keep it until form submission succeeds
            // sessionStorage will be cleared after successful form submission
        } catch (e) {
            console.error('Failed to parse template data:', e);
            sessionStorage.removeItem('app_template_data');
        }
    } else {
        // Add initial header row if no template data
        addHeaderRow();
    }
    
    // Setup form submit handler
    document.getElementById('service-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(e.target);
        const serviceType = formData.get('service_type');
        const mcpTransport = formData.get('mcp_transport') || 'http';
        
        // For MCP type, validate connection first
        if (serviceType === 'mcp') {
            if (mcpTransport === 'http') {
                const connectionSuccess = await testConnection();
                if (!connectionSuccess) {
                    await modal.warning(t('app_mcp_connection_required') || 'MCP接続テストに成功してから登録してください');
                    return;
                }
            } else {
                // stdio transport
                const connectionSuccess = await testStdioConnection();
                if (!connectionSuccess) {
                    await modal.warning(t('app_stdio_connection_required') || 'stdio接続テストに成功してから登録してください');
                    return;
                }
            }
        }
        
        const data = {
            name: formData.get('name'),
            description: formData.get('description'),
            service_type: serviceType,
            common_headers: {},
            mcp_service_id: mcpServiceId
        };
        
        // Handle MCP transport specific data
        if (serviceType === 'mcp') {
            data.mcp_transport = mcpTransport;
            
            if (mcpTransport === 'http') {
                // Get mcp_url for HTTP transport
                const mcpUrlValue = formData.get('mcp_url');
                if (mcpUrlValue && mcpUrlValue.trim()) {
                    data.mcp_url = mcpUrlValue.trim();
                }
            } else {
                // Get stdio config
                data.stdio_command = formData.get('stdio_command');
                
                // Parse args (one per line)
                const argsText = formData.get('stdio_args') || '';
                data.stdio_args = argsText ? argsText.split('\n').map(line => line.trim()).filter(line => line) : [];
                
                // Collect environment variables
                const env = {};
                const envRows = document.querySelectorAll('#env-container .key-value-row');
                envRows.forEach(row => {
                    const inputs = row.querySelectorAll('input[type="text"]');
                    const key = inputs[0].value.trim();
                    const value = inputs[1].value.trim();
                    if (key) {
                        env[key] = value;
                    }
                });
                data.stdio_env = env;
                
                const cwd = formData.get('stdio_cwd');
                if (cwd && cwd.trim()) {
                    data.stdio_cwd = cwd.trim();
                }
            }
        } else {
            // API type - optional base URL
            const mcpUrlValue = formData.get('mcp_url');
            if (mcpUrlValue && mcpUrlValue.trim()) {
                data.mcp_url = mcpUrlValue.trim();
            }
        }
        
        // Collect headers for both API and MCP types
        const headerRows = document.querySelectorAll('#headers-container .key-value-row');
        headerRows.forEach(row => {
            const inputs = row.querySelectorAll('input[type="text"]');
            const key = inputs[0].value.trim();
            const value = inputs[1].value.trim();
            if (key) {
                data.common_headers[key] = value;
            }
        });
        
        // Create the app
        const response = await fetch('/api/apps', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            const app = await response.json();
            const appId = app.id;
            
            // For API templates with capabilities, register them
            if (serviceType === 'api' && templateCapabilities && templateCapabilities.length > 0) {
                console.log(`Registering ${templateCapabilities.length} capabilities...`);
                
                for (const capTemplate of templateCapabilities) {
                    try {
                        // Parse headers and body_params if they are strings
                        let headers = capTemplate.headers || {};
                        let bodyParams = capTemplate.body_params || {};
                        
                        if (typeof headers === 'string') {
                            try {
                                headers = JSON.parse(headers);
                            } catch (e) {
                                headers = {};
                            }
                        }
                        
                        if (typeof bodyParams === 'string') {
                            try {
                                bodyParams = JSON.parse(bodyParams);
                            } catch (e) {
                                bodyParams = {};
                            }
                        }
                        
                        const capData = {
                            name: capTemplate.name,
                            capability_type: capTemplate.capability_type,
                            url: capTemplate.endpoint_path || '',
                            headers: headers,
                            body_params: bodyParams,
                            description: capTemplate.description || '',
                            method: capTemplate.method || 'GET'
                        };
                        
                        const capResponse = await fetch(`/api/apps/${appId}/capabilities`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(capData)
                        });
                        
                        if (!capResponse.ok) {
                            console.error(`Failed to register capability: ${capTemplate.name}`);
                        }
                    } catch (error) {
                        console.error(`Error registering capability ${capTemplate.name}:`, error);
                    }
                }
                
                console.log('All capabilities registered');
            }
            
            // Clear template data from sessionStorage after successful registration
            sessionStorage.removeItem('app_template_data');
            
            window.location.href = `/mcp-services/${mcpServiceId}/apps`;
        } else {
            const error = await response.json();
            await modal.error(t('app_register_failed') + ': ' + (error.error || t('error_unknown')));
        }
    });
})();
