const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

export const api = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const defaultHeaders = {
            'Accept': 'application/json',
        };

        if (token) {
            defaultHeaders['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
        };

        // If no content-type is set in options, and body is not FormData, default to JSON
        if (!config.headers['Content-Type'] && !(options.body instanceof FormData) && options.body) {
            config.headers['Content-Type'] = 'application/json';
        }

        const maxRetries = 3;
        let attempt = 0;

        const executeRequest = async () => {
            try {
                const response = await fetch(`${BASE_URL}${endpoint}`, config);

                // Check for download responses
                const contentType = response.headers.get('content-type');
                if (contentType && (
                    contentType.includes('application/vnd.openxmlformats-officedocument.wordprocessingml.document') ||
                    contentType.includes('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                )) {
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;

                    // Try to get filename from content-disposition
                    const contentDisposition = response.headers.get('content-disposition');
                    let filename = contentType.includes('spreadsheetml') ? 'download.xlsx' : 'download.docx';
                    if (contentDisposition) {
                        const matches = /filename="([^"]+)"/.exec(contentDisposition);
                        if (matches != null && matches[1]) filename = matches[1];
                    }

                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    a.remove();
                    window.URL.revokeObjectURL(url);
                    return { success: true, message: "Download started" };
                }

                const data = await response.json();

                if (!response.ok) {
                    if (response.status === 401) {
                        localStorage.removeItem('token');
                        localStorage.removeItem('user');
                        window.dispatchEvent(new Event('unauthorized'));
                    }
                    let errorMessage = 'API Request Failed';
                    if (data.detail) {
                        if (typeof data.detail === 'string') {
                            errorMessage = data.detail;
                        } else if (Array.isArray(data.detail)) {
                            errorMessage = data.detail.map(e => `${e.loc ? e.loc.join('.') : 'Field'}: ${e.msg}`).join(', ');
                        } else {
                            errorMessage = JSON.stringify(data.detail);
                        }
                    }
                    throw new Error(errorMessage);
                }
                return data;
            } catch (error) {
                // If it's a "Failed to fetch" (Network Error) and we have retries left
                if (error.name === 'TypeError' && error.message.includes('fetch') && attempt < maxRetries) {
                    attempt++;
                    const delay = Math.pow(2, attempt) * 1000; // 2s, 4s, 8s
                    console.warn(`Fetch failed, retrying attempt ${attempt} in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                    return executeRequest();
                }
                console.error('API Error:', error);
                throw error;
            }
        };

        return executeRequest();
    }
};
