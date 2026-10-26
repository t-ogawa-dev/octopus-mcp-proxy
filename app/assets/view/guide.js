// guide.js - Connection Guide Page

let _apiKey = null;
let _apiKeyVisible = false;

function getBaseUrl() {
    return window.location.protocol + '//' + window.location.host;
}

function getAdminMcpUrl() {
    return getBaseUrl() + '/admin/mcp';
}

function getMcpServiceUrl(identifier, routingType) {
    if (routingType === 'subdomain') {
        // subdomain routing: identifier.host/mcp
        const host = window.location.hostname;
        const port = window.location.port ? ':' + window.location.port : '';
        return window.location.protocol + '//' + identifier + '.' + host + port + '/mcp';
    }
    // path routing: host/identifier/mcp
    return getBaseUrl() + '/' + identifier + '/mcp';
}

async function loadSystemAccount() {
    try {
        const data = await AppApi.request('/api/admin/system-account');
        _apiKey = data.bearer_token;
    } catch (e) {
        console.error('Failed to load system account', e);
    }
}

function renderEndpointUrl() {
    const url = getAdminMcpUrl();
    document.getElementById('endpoint-url').textContent = url;
}

function renderServiceUrls() {
    document.querySelectorAll('[data-identifier]').forEach(el => {
        const identifier = el.dataset.identifier;
        const routing = el.dataset.routing;
        el.textContent = getMcpServiceUrl(identifier, routing);
    });
}

function renderApiKey() {
    const el = document.getElementById('api-key-display');
    if (_apiKeyVisible && _apiKey) {
        el.textContent = _apiKey;
        el.classList.remove('masked');
    } else {
        el.textContent = '●●●●●●●●●●●●●●●●';
        el.classList.add('masked');
    }
}

function toggleApiKey() {
    _apiKeyVisible = !_apiKeyVisible;
    renderApiKey();
    const btn = document.getElementById('toggle-key-btn');
    btn.textContent = t(_apiKeyVisible ? 'guide_api_key_hide' : 'guide_api_key_show');
}

async function copyApiKey() {
    if (!_apiKey) return;
    try {
        await navigator.clipboard.writeText(_apiKey);
        await modal.success(t('guide_copied'));
    } catch (e) {
        await modal.error(t('copy_failed'));
    }
}

async function copyText(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    try {
        await navigator.clipboard.writeText(el.textContent.trim());
        await modal.success(t('guide_copied'));
    } catch (e) {
        await modal.error(t('copy_failed'));
    }
}

async function regenerateApiKey() {
    const confirmed = await modal.confirm(
        t('guide_api_key_regenerate_confirm'),
        null,
        { confirmText: t('guide_api_key_regenerate'), confirmClass: 'btn-warning' }
    );
    if (!confirmed) return;

    try {
        const data = await AppApi.request('/api/admin/system-account/regenerate', { method: 'POST' });
        _apiKey = data.bearer_token;
        _apiKeyVisible = true;
        renderApiKey();
        document.getElementById('toggle-key-btn').textContent = t('guide_api_key_hide');
        renderSnippets();
        await modal.success(t('guide_api_key_regenerated'));
    } catch (e) {
        await modal.error(t('error_unknown'));
    }
}

function renderSnippets() {
    const url = getAdminMcpUrl();
    const key = _apiKey || '<YOUR_BEARER_TOKEN>';

    const claudeSnippet = JSON.stringify({
        mcpServers: {
            'accelmcp-admin': {
                type: 'http',
                url: url,
                headers: { Authorization: 'Bearer ' + key }
            }
        }
    }, null, 2);

    const cursorSnippet = JSON.stringify({
        mcpServers: {
            'accelmcp-admin': {
                url: url,
                headers: { Authorization: 'Bearer ' + key }
            }
        }
    }, null, 2);

    const vscodeSnippet = JSON.stringify({
        mcp: {
            servers: {
                'accelmcp-admin': {
                    type: 'http',
                    url: url,
                    headers: { Authorization: 'Bearer ' + key }
                }
            }
        }
    }, null, 2);

    const genericSnippet =
`curl -X POST ${url} \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer ${key}" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'`;

    document.getElementById('snippet-claude-code').textContent = claudeSnippet;
    document.getElementById('snippet-cursor-code').textContent = cursorSnippet;
    document.getElementById('snippet-vscode-code').textContent = vscodeSnippet;
    document.getElementById('snippet-generic-code').textContent = genericSnippet;
}

async function copySnippet(containerId) {
    const pre = document.getElementById(containerId + '-code');
    if (!pre) return;
    try {
        await navigator.clipboard.writeText(pre.textContent.trim());
        await modal.success(t('guide_snippet_copied'));
    } catch (e) {
        await modal.error(t('copy_failed'));
    }
}

function switchTab(name) {
    document.querySelectorAll('.snippet-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.snippet-content').forEach(c => c.classList.remove('active'));
    document.getElementById('snippet-' + name).classList.add('active');
    // activate tab button by order: claude=0, cursor=1, vscode=2, generic=3
    const order = { claude: 0, cursor: 1, vscode: 2, generic: 3 };
    document.querySelectorAll('.snippet-tab')[order[name]].classList.add('active');
}

(async () => {
    await initLanguageSwitcher();
    document.addEventListener('click', (event) => {
        const element = event.target.closest('[data-action]');
        if (!element) return;
        const action = element.dataset.action;
        if (action === 'copy-endpoint') copyText('endpoint-url');
        if (action === 'toggle-key') toggleApiKey();
        if (action === 'copy-key') copyApiKey();
        if (action === 'regenerate-key') regenerateApiKey();
        if (action === 'snippet-tab') switchTab(element.dataset.snippet);
        if (action === 'copy-snippet') copySnippet(element.dataset.snippet);
    });
    document.title = t('guide_title') + ' - Octopus MCP Proxy';

    await loadSystemAccount();

    renderEndpointUrl();
    renderApiKey();
    renderSnippets();
})();
