/**
 * Connection Logs Index Page
 * Shows MCP services list (without global stats)
 */

document.addEventListener('DOMContentLoaded', async () => {
    await initLanguageSwitcher();
    await loadServicesList();
});

async function loadServicesList() {
    const container = document.getElementById('services-list');
    
    try {
        const services = await AppApi.request('/api/connection-logs/by-service');
        
        // Filter out orphan logs for main list, show only registered services
        const registeredServices = services.filter(item => item.mcp_service !== null);
        const orphanLogs = services.find(item => item.mcp_service === null);
        
        if (registeredServices.length === 0) {
            container.innerHTML = `
                <div class="no-services-message">
                    <div class="no-services-icon">📋</div>
                    <p data-i18n="log_no_services">${window.t('log_no_services')}</p>
                    <a href="/mcp-services" class="btn btn-primary" data-i18n="mcp_service_list_title">MCPサービス一覧へ</a>
                </div>
            `;
            return;
        }
        
        // Sort by service name
        registeredServices.sort((a, b) => a.mcp_service.name.localeCompare(b.mcp_service.name));
        
        let html = registeredServices.map(item => {
            const service = item.mcp_service;
            const lastLogAt = item.last_log_at ? formatDateTime(item.last_log_at) : window.t('log_no_access_yet');
            
            return `
                <div class="service-log-card" data-service-id="${service.id}">
                    <div class="service-info">
                        <div class="service-name">${AppDom.escapeHtml(service.name)}</div>
                        <div class="service-meta">
                            <span>${window.t('log_identifier')}: ${AppDom.escapeHtml(service.identifier)}</span>
                            <span>${window.t('log_last_access')}: ${lastLogAt}</span>
                        </div>
                    </div>
                    <div class="log-count-badge ${item.log_count === 0 ? 'zero' : ''}">
                        ${item.log_count.toLocaleString()} ${window.t('log_count_unit')}
                    </div>
                </div>
            `;
        }).join('');
        
        // Add orphan logs card if exists
        if (orphanLogs && orphanLogs.log_count > 0) {
            html += `
                <div class="service-log-card orphan-card" data-service-id="">
                    <div class="service-info">
                        <div class="service-name">${window.t('log_orphan_logs')}</div>
                        <div class="service-meta">
                            <span>${window.t('log_last_access')}: ${formatDateTime(orphanLogs.last_log_at)}</span>
                        </div>
                    </div>
                    <div class="log-count-badge">
                        ${orphanLogs.log_count.toLocaleString()} ${window.t('log_count_unit')}
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
        
        container.addEventListener('click', (event) => {
            const card = event.target.closest('[data-service-id]');
            if (card) navigateToLogs(card.dataset.serviceId || null);
        });
    } catch (error) {
        console.error('Failed to load services:', error);
        container.innerHTML = `
            <div class="no-services-message">
                <div class="no-services-icon">⚠️</div>
                <p>${window.t('error_loading')}</p>
            </div>
        `;
    }
}

function navigateToLogs(mcpServiceId) {
    if (mcpServiceId === null) {
        window.location.href = '/connection-logs/list';
    } else {
        window.location.href = `/connection-logs/list?mcp_service_id=${mcpServiceId}`;
    }
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    const lang = document.documentElement.lang || 'ja';
    return date.toLocaleString(lang === 'ja' ? 'ja-JP' : 'en-US');
}
