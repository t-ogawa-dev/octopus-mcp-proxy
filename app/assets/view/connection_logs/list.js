/**
 * Connection Logs List Page
 * Shows logs for a specific MCP service with filtering and pagination
 */

let currentPage = 1;
let currentFilters = {};
let mcpServiceId = null;
let mcpServiceName = '';

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize language switcher
    await initLanguageSwitcher();
    
    // Get mcp_service_id from URL
    const urlParams = new URLSearchParams(window.location.search);
    mcpServiceId = urlParams.get('mcp_service_id');
    
    // Load accounts for filter
    await loadAccountsFilter();
    
    // Load MCP service info
    if (mcpServiceId) {
        await loadServiceInfo();
    }
    
    // Setup event listeners
    setupEventListeners();
    
    // Load stats for this service
    await loadStats();
    
    // Load logs
    await loadLogs();
});

async function loadStats() {
    try {
        const params = mcpServiceId ? `?mcp_service_id=${mcpServiceId}` : '';
        const stats = await AppApi.request(`/api/connection-logs/stats${params}`);
        
        document.getElementById('stat-total').textContent = stats.total.toLocaleString();
        document.getElementById('stat-success').textContent = stats.success.toLocaleString();
        document.getElementById('stat-error').textContent = stats.error.toLocaleString();
        document.getElementById('stat-24h').textContent = stats.last_24h.toLocaleString();
        
        document.getElementById('log-stats').style.display = 'grid';
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

async function loadServiceInfo() {
    try {
        const service = await AppApi.request(`/api/mcp-services/${mcpServiceId}`);
        mcpServiceName = service.name;
        document.getElementById('breadcrumb-service').textContent = service.name;
        document.getElementById('page-title').textContent = `${service.name} - ${t('connection_logs_list_title')}`;
    } catch (error) {
        console.error('Failed to load service info:', error);
    }
}

async function loadAccountsFilter() {
    try {
        const accounts = await AppApi.request('/api/accounts');
        const select = document.getElementById('filter-account');
        accounts.forEach(account => {
            const option = document.createElement('option');
            option.value = account.id;
            option.textContent = account.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Failed to load accounts:', error);
    }
}

function setupEventListeners() {
    // Apply filter
    document.getElementById('apply-filter-btn').addEventListener('click', () => {
        currentPage = 1;
        collectFilters();
        loadLogs();
    });
    
    // Clear filter
    document.getElementById('clear-filter-btn').addEventListener('click', () => {
        document.getElementById('filter-search').value = '';
        document.getElementById('filter-date-from').value = '';
        document.getElementById('filter-date-to').value = '';
        document.getElementById('filter-method').value = '';
        document.getElementById('filter-status').value = '';
        document.getElementById('filter-account').value = '';
        currentPage = 1;
        currentFilters = {};
        loadLogs();
    });
    
    // Export CSV
    document.getElementById('export-btn').addEventListener('click', exportCsv);
    document.getElementById('logs-body').addEventListener('click', (event) => {
        const row = event.target.closest('[data-log-id]');
        if (row) viewLogDetail(row.dataset.logId);
    });
    document.getElementById('pagination').addEventListener('click', (event) => {
        const button = event.target.closest('[data-page]');
        if (button && !button.disabled) goToPage(Number(button.dataset.page));
    });
}

function collectFilters() {
    currentFilters = {};
    
    const search = document.getElementById('filter-search').value;
    if (search) currentFilters.search = search;
    
    const dateFrom = document.getElementById('filter-date-from').value;
    if (dateFrom) currentFilters.date_from = new Date(dateFrom).toISOString();
    
    const dateTo = document.getElementById('filter-date-to').value;
    if (dateTo) currentFilters.date_to = new Date(dateTo).toISOString();
    
    const method = document.getElementById('filter-method').value;
    if (method) currentFilters.mcp_method = method;
    
    const status = document.getElementById('filter-status').value;
    if (status !== '') currentFilters.is_success = status;
    
    const account = document.getElementById('filter-account').value;
    if (account) currentFilters.account_id = account;
}

async function loadLogs() {
    const tbody = document.getElementById('logs-body');
    tbody.innerHTML = `<tr><td colspan="7" class="empty-state">${t('loading')}</td></tr>`;
    
    try {
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 50,
            ...currentFilters
        });
        
        if (mcpServiceId) {
            params.set('mcp_service_id', mcpServiceId);
        }
        
        const data = await AppApi.request(`/api/connection-logs?${params}`);
        
        if (data.items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="empty-state">
                        <div class="empty-icon">📋</div>
                        <p>${t('log_no_results')}</p>
                    </td>
                </tr>
            `;
            document.getElementById('pagination').innerHTML = '';
            return;
        }
        
        tbody.innerHTML = data.items.map(log => `
            <tr data-log-id="${log.id}">
                <td>${formatDateTime(log.created_at)}</td>
                <td>${AppDom.escapeHtml(log.account_name)}</td>
                <td><span class="method-badge">${AppDom.escapeHtml(log.mcp_method)}</span></td>
                <td>${log.tool_name ? AppDom.escapeHtml(log.tool_name) : '-'}</td>
                <td>
                    <span class="status-badge ${log.is_success ? 'success' : 'error'}">
                        ${log.is_success ? t('log_success') : t('log_error')}
                    </span>
                </td>
                <td>${log.duration_ms !== null ? `${log.duration_ms}ms` : '-'}</td>
                <td>${log.ip_address ? AppDom.escapeHtml(log.ip_address) : '-'}</td>
            </tr>
        `).join('');
        
        renderPagination(data);
        
    } catch (error) {
        console.error('Failed to load logs:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="empty-state">
                    <div class="empty-icon">⚠️</div>
                    <p>${t('error_loading')}</p>
                </td>
            </tr>
        `;
    }
}

function renderPagination(data) {
    const container = document.getElementById('pagination');
    
    if (data.pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    container.innerHTML = `
        <button type="button" class="pagination-btn" data-page="${data.page - 1}" ${!data.has_prev ? 'disabled' : ''}>
            ← ${t('pagination_prev')}
        </button>
        <span class="pagination-info">
            ${data.page} / ${data.pages} (${t('pagination_total')}: ${data.total.toLocaleString()})
        </span>
        <button type="button" class="pagination-btn" data-page="${data.page + 1}" ${!data.has_next ? 'disabled' : ''}>
            ${t('pagination_next')} →
        </button>
    `;
}

function goToPage(page) {
    currentPage = page;
    loadLogs();
}

function viewLogDetail(logId) {
    window.location.href = `/connection-logs/${logId}`;
}

function exportCsv() {
    const params = new URLSearchParams(currentFilters);
    if (mcpServiceId) {
        params.set('mcp_service_id', mcpServiceId);
    }
    window.location.href = `/api/connection-logs/export?${params}`;
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    const lang = document.documentElement.lang || 'ja';
    return date.toLocaleString(lang === 'ja' ? 'ja-JP' : 'en-US');
}
