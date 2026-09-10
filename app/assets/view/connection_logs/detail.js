/**
 * Connection Log Detail Page
 * Shows full details of a single log entry
 */

document.addEventListener('DOMContentLoaded', async () => {
    await initLanguageSwitcher();
    await loadLogDetail();
    setupBackButton();
});

function setupBackButton() {
    const backBtn = document.getElementById('back-btn');
    const referrer = document.referrer;
    
    if (referrer && referrer.includes('/connection-logs')) {
        backBtn.href = referrer;
    } else {
        backBtn.href = '/connection-logs';
    }
    
    // Update breadcrumb list link
    const breadcrumbList = document.getElementById('breadcrumb-list');
    if (referrer && referrer.includes('/connection-logs/list')) {
        breadcrumbList.href = referrer;
    } else {
        breadcrumbList.href = '/connection-logs/list';
    }
}

async function loadLogDetail() {
    const container = document.getElementById('log-detail');
    
    try {
        const log = await AppApi.request(`/api/connection-logs/${logId}`);
        
        // Update subtitle
        document.getElementById('log-subtitle').textContent = 
            `${formatDateTime(log.created_at)} - ${log.mcp_method}`;
        
        container.innerHTML = `
            <!-- Basic Info Section -->
            <div class="detail-section">
                <div class="detail-section-header">${t('log_detail_basic')}</div>
                <div class="detail-section-body">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_datetime')}</span>
                            <span class="detail-value">${formatDateTime(log.created_at)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_duration')}</span>
                            <span class="detail-value">${log.duration_ms !== null ? `${log.duration_ms}ms` : '-'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_status')}</span>
                            <span class="status-badge ${log.is_success ? 'success' : 'error'}">
                                ${log.is_success ? t('log_success') : t('log_error')}
                            </span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_method')}</span>
                            <span class="method-badge">${AppDom.escapeHtml(log.mcp_method)}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Account & Resource Section -->
            <div class="detail-section">
                <div class="detail-section-header">${t('log_detail_account_resource')}</div>
                <div class="detail-section-body">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_account')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.account_name)}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_access_control')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.access_control || '-')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_mcp_service')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.mcp_service_name || '-')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_app')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.app_name || '-')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_capability')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.capability_name || '-')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_tool')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.tool_name || '-')}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Client Info Section -->
            <div class="detail-section">
                <div class="detail-section-header">${t('log_detail_client')}</div>
                <div class="detail-section-body">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">${t('log_col_ip')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.ip_address || '-')}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_user_agent')}</span>
                            <span class="detail-value" style="word-break: break-all;">${AppDom.escapeHtml(log.user_agent) || '-'}</span>
                        </div>
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_request_id')}</span>
                            <span class="detail-value">${AppDom.escapeHtml(log.request_id || '-')}</span>
                        </div>
                    </div>
                </div>
            </div>
            
            ${!log.is_success ? `
            <!-- Error Section -->
            <div class="detail-section" style="border-color: #ffcdd2;">
                <div class="detail-section-header" style="background: #ffebee; color: #c62828;">
                    ${t('log_detail_error')}
                </div>
                <div class="detail-section-body">
                    <div class="detail-grid">
                        <div class="detail-item">
                            <span class="detail-label">${t('log_detail_error_code')}</span>
                            <span class="detail-value error">${AppDom.escapeHtml(log.error_code || '-')}</span>
                        </div>
                        <div class="detail-item" style="grid-column: span 2;">
                            <span class="detail-label">${t('log_detail_error_message')}</span>
                            <span class="detail-value error">${AppDom.escapeHtml(log.error_message) || '-'}</span>
                        </div>
                    </div>
                </div>
            </div>
            ` : ''}
            
            <!-- Request Body Section -->
            <div class="detail-section">
                <div class="detail-section-header">
                    ${t('log_detail_request_body')}
                    ${log.request_body && log.request_body.includes('[MASKED]') ? 
                        `<span class="masked-indicator">⚠️ ${t('log_masked_indicator')}</span>` : ''}
                </div>
                <div class="detail-section-body">
                    ${log.request_body ? 
                        `<pre class="json-viewer">${formatJson(log.request_body)}</pre>` :
                        `<p class="empty-body">${t('log_no_body')}</p>`
                    }
                </div>
            </div>
            
            <!-- Response Body Section -->
            <div class="detail-section">
                <div class="detail-section-header">
                    ${t('log_detail_response_body')}
                    ${log.response_body && log.response_body.includes('[MASKED]') ? 
                        `<span class="masked-indicator">⚠️ ${t('log_masked_indicator')}</span>` : ''}
                </div>
                <div class="detail-section-body">
                    ${log.response_body ? 
                        `<pre class="json-viewer">${formatJson(log.response_body)}</pre>` :
                        `<p class="empty-body">${t('log_no_body')}</p>`
                    }
                </div>
            </div>
        `;
        
    } catch (error) {
        console.error('Failed to load log detail:', error);
        container.innerHTML = `
            <div class="detail-section">
                <div class="detail-section-body" style="text-align: center; padding: 60px;">
                    <div style="font-size: 3rem; margin-bottom: 16px;">⚠️</div>
                    <p>${t('error_loading')}</p>
                </div>
            </div>
        `;
    }
}

function formatJson(jsonString) {
    try {
        const obj = JSON.parse(jsonString);
        return syntaxHighlight(JSON.stringify(obj, null, 2));
    } catch (e) {
        // If not valid JSON, just escape and return
        return AppDom.escapeHtml(jsonString);
    }
}

function syntaxHighlight(json) {
    json = AppDom.escapeHtml(json);
    return json.replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g, function (match) {
        let cls = 'number';
        if (/^"/.test(match)) {
            if (/:$/.test(match)) {
                cls = 'key';
            } else {
                cls = 'string';
            }
        } else if (/true|false/.test(match)) {
            cls = 'boolean';
        } else if (/null/.test(match)) {
            cls = 'null';
        }
        return '<span class="' + cls + '">' + match + '</span>';
    });
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    const lang = document.documentElement.lang || 'ja';
    return date.toLocaleString(lang === 'ja' ? 'ja-JP' : 'en-US');
}
