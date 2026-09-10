(function () {
    class ApiError extends Error {
        constructor(message, status, data) {
            super(message);
            this.name = 'ApiError';
            this.status = status;
            this.data = data;
        }
    }

    async function request(url, options = {}) {
        const headers = new Headers(options.headers || {});
        if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json');
        }

        const response = await fetch(url, { ...options, headers });
        const contentType = response.headers.get('content-type') || '';
        const data = contentType.includes('application/json')
            ? await response.json().catch(() => null)
            : await response.text();

        if (!response.ok) {
            const message = data && typeof data === 'object'
                ? data.error || data.message
                : null;
            throw new ApiError(message || `Request failed (${response.status})`, response.status, data);
        }

        return data;
    }

    window.AppApi = { ApiError, request };
})();