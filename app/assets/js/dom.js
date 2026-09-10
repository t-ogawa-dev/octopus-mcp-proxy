(function () {
    function escapeHtml(value) {
        const element = document.createElement('span');
        element.textContent = value == null ? '' : String(value);
        return element.innerHTML;
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