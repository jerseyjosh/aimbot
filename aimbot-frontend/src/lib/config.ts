// API configuration
export const API_BASE_URL = import.meta.env.DEV 
    ? 'http://localhost:8000'  // Development
    : '';  // Production (relative URLs)

export function apiUrl(path: string): string {
    return `${API_BASE_URL}${path}`;
}