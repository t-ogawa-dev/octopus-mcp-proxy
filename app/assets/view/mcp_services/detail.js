/**
 * MCPサービス詳細画面
 * v1.1 - アクセス制御表示追加
 */

const mcpServiceId = Number.parseInt(window.location.pathname.split('/')[2], 10);

async function copyEndpoint(btn) {
    const endpoint = document.getElementById('mcp-endpoint').textContent;
    
    // Create temporary textarea element
    const textarea = document.createElement('textarea');
    textarea.value = endpoint;
    textarea.style.position = 'fixed';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    
    try {
        textarea.select();
        textarea.setSelectionRange(0, 99999); // For mobile devices
        
        const successful = document.execCommand('copy');
        
        if (successful) {
            // Show success feedback
            const originalText = btn.textContent;
            const copiedText = currentLanguage === 'ja' ? '✓ コピーしました' : '✓ Copied';
            btn.textContent = copiedText;
            btn.style.backgroundColor = '#10b981';
            btn.style.borderColor = '#10b981';
            btn.style.color = 'white';
            
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.backgroundColor = '';
                btn.style.borderColor = '';
                btn.style.color = '';
            }, 2000);
        } else {
            const errorMsg = currentLanguage === 'ja' ? 'コピーに失敗しました' : 'Failed to copy';
            await modal.error(errorMsg);
        }
    } catch (err) {
        console.error('Failed to copy:', err);
        const errorMsg = currentLanguage === 'ja' ? 'コピーに失敗しました: ' : 'Failed to copy: ';
        await modal.error(errorMsg + err.message);
    } finally {
        document.body.removeChild(textarea);
    }
}

async function exportMcpService() {
    try {
        const response = await fetch(`/api/mcp-services/${mcpServiceId}/export`);
        if (!response.ok) throw new Error('Export failed');
        
        // Get YAML content as text
        const yamlContent = await response.text();
        
        // Extract filename from Content-Disposition header or use default
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = 'mcp-service.yaml';
        if (contentDisposition) {
            const matches = /filename="(.+)"/.exec(contentDisposition);
            if (matches) filename = matches[1];
        }
        
        // Download as YAML file
        const blob = new Blob([yamlContent], { type: 'application/x-yaml' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        // Show success message
        const successMsg = currentLanguage === 'ja' ? 'エクスポートしました' : 'Exported successfully';
        await modal.success(successMsg);
    } catch (error) {
        console.error('Export failed:', error);
        const errorMsg = currentLanguage === 'ja' ? 'エクスポートに失敗しました' : 'Export failed';
        await modal.error(errorMsg);
    }
}

async function loadMcpService() {
    const service = await AppApi.request(`/api/mcp-services/${mcpServiceId}`);
    
    // Update breadcrumb with service name
    const breadcrumbCurrent = document.querySelector('.breadcrumb-current');
    if (breadcrumbCurrent && service.name) {
        breadcrumbCurrent.textContent = service.name;
    }
    
    // Basic info
    document.getElementById('service-name').textContent = service.name;
    document.getElementById('name').textContent = service.name;
    document.getElementById('identifier').textContent = service.identifier;
    
    // Generate endpoint based on routing type
    const currentHost = window.location.host;
    const protocol = window.location.protocol;
    
    let endpoint;
    if (service.routing_type === 'path') {
        endpoint = `${protocol}//${currentHost}/${service.identifier}/mcp`;
    } else {
        // For subdomain routing
        const hostWithoutPort = currentHost.split(':')[0];
        const port = currentHost.includes(':') ? ':' + currentHost.split(':')[1] : '';
        const hostParts = hostWithoutPort.split('.');
        
        let subdomainHost;
        if (hostParts.length >= 4 || (hostParts.length === 3 && !['com', 'net', 'org', 'io', 'dev', 'app'].includes(hostParts[hostParts.length-1]))) {
            // Has subdomain: replace first part
            hostParts[0] = service.identifier;
            subdomainHost = hostParts.join('.') + port;
        } else if (hostParts.length === 3) {
            // 3 parts with common TLD: replace first
            hostParts[0] = service.identifier;
            subdomainHost = hostParts.join('.') + port;
        } else {
            // 2 or less parts: add prefix
            subdomainHost = `${service.identifier}.${currentHost}`;
        }
        endpoint = `${protocol}//${subdomainHost}/mcp`;
    }
    document.getElementById('mcp-endpoint').textContent = endpoint;
    
    document.getElementById('description').textContent = service.description || '-';
    
    // Access control
    const badge = document.getElementById('access-control-badge');
    const isPublic = service.access_control === 'public';
    
    if (isPublic) {
        badge.textContent = t('access_control_public');
        badge.style.cssText = 'padding: 4px 12px; border-radius: 4px; background-color: #d1fae5; color: #065f46; font-weight: 500; font-size: 0.875rem;';
    } else {
        badge.textContent = t('access_control_restricted');
        badge.style.cssText = 'padding: 4px 12px; border-radius: 4px; background-color: #fef3c7; color: #92400e; font-weight: 500; font-size: 0.875rem;';
    }

    // Render client configuration snippets
    renderServiceSnippets(service, endpoint);
}

(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const actionElement = event.target.closest('[data-action]');
        if (!actionElement) return;

        const action = actionElement.dataset.action;
        if (action === 'export') exportMcpService();
        if (action === 'copy-endpoint') copyEndpoint(actionElement);
        if (action === 'snippet-tab') switchSvcSnippetTab(actionElement.dataset.snippet);
        if (action === 'copy-snippet') copySvcSnippet(actionElement.dataset.snippet);
    });
    await loadMcpService();
})();

// ---- Client Configuration Snippets ----

function renderServiceSnippets(service, endpoint) {
    const key = '<YOUR_BEARER_TOKEN>';
    const serverKey = service.identifier || 'mcp-service';

    const claudeSnippet = JSON.stringify({
        mcpServers: {
            [serverKey]: {
                type: 'http',
                url: endpoint,
                headers: { Authorization: 'Bearer ' + key }
            }
        }
    }, null, 2);

    const cursorSnippet = JSON.stringify({
        mcpServers: {
            [serverKey]: {
                url: endpoint,
                headers: { Authorization: 'Bearer ' + key }
            }
        }
    }, null, 2);

    const vscodeSnippet = JSON.stringify({
        mcp: {
            servers: {
                [serverKey]: {
                    type: 'http',
                    url: endpoint,
                    headers: { Authorization: 'Bearer ' + key }
                }
            }
        }
    }, null, 2);

    const genericSnippet =
`curl -X POST ${endpoint} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${key}" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'`;

    document.getElementById('svc-snippet-claude-code').textContent = claudeSnippet;
    document.getElementById('svc-snippet-cursor-code').textContent = cursorSnippet;
    document.getElementById('svc-snippet-vscode-code').textContent = vscodeSnippet;
    document.getElementById('svc-snippet-generic-code').textContent = genericSnippet;
    document.getElementById('svc-snippet-card').style.display = '';
}

function switchSvcSnippetTab(name) {
    document.querySelectorAll('#svc-snippet-card .snippet-tab').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('#svc-snippet-card .snippet-content').forEach(el => el.classList.remove('active'));
    document.getElementById('svc-snippet-' + name).classList.add('active');
    const order = { claude: 0, cursor: 1, vscode: 2, generic: 3 };
    document.querySelectorAll('#svc-snippet-card .snippet-tab')[order[name]].classList.add('active');
}

async function copySvcSnippet(containerId) {
    const pre = document.getElementById(containerId + '-code');
    if (!pre) return;
    try {
        await navigator.clipboard.writeText(pre.textContent.trim());
        await modal.success(t('guide_snippet_copied'));
    } catch (e) {
        await modal.error(t('copy_failed'));
    }
}
