(function () {
    // Quotes are escaped too so the result is safe inside attribute values
    const HTML_ESCAPES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

    function escapeHtml(value) {
        return (value == null ? '' : String(value)).replace(/[&<>"']/g, (ch) => HTML_ESCAPES[ch]);
    }

    function safeHttpUrl(value) {
        try {
            const url = new URL(value, window.location.origin);
            return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
        } catch (error) {
            return null;
        }
    }

    window.AppDom = { escapeHtml, safeHttpUrl };
})();