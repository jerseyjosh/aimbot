import { writable } from 'svelte/store';

const STORAGE_KEY_PREFIX = 'renderedEmailStore';

// Helper to get storage key for email type
function getStorageKey(emailType: string): string {
    return `${STORAGE_KEY_PREFIX}_${emailType}`;
}

// Helper to load from localStorage
function loadFromStorage(emailType: string): string {
    if (typeof window === 'undefined') return "<i><h1>Preview</h1></i>";
    try {
        const stored = localStorage.getItem(getStorageKey(emailType));
        return stored || "<i><h1>Preview</h1></i>";
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return "<i><h1>Preview</h1></i>";
    }
}

// Helper to save to localStorage
function saveToStorage(emailType: string, html: string) {
    if (typeof window === 'undefined') return;
    try {
        localStorage.setItem(getStorageKey(emailType), html);
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

function createRenderedEmailStore() {
    const { subscribe, set, update } = writable<Record<string, string>>({});

    return {
        subscribe,
        get: (emailType: string) => {
            let value: string = "<i><h1>Preview</h1></i>";
            subscribe(stores => { value = stores[emailType] || "<i><h1>Preview</h1></i>"; })();
            return value;
        },
        set: (emailType: string, value: string) => {
            update(stores => {
                saveToStorage(emailType, value);
                return { ...stores, [emailType]: value };
            });
        },
        async render(emailType: string, emailData: any) {
            try {
                const res = await fetch(`/emails/${emailType}/render`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(emailData)
                });
                const html = await res.text();
                update(stores => {
                    saveToStorage(emailType, html);
                    return { ...stores, [emailType]: html };
                });
                return html;
            } catch (error) {
                console.error('Failed to render email:', error);
                throw error;
            }
        },
        clear(emailType: string) {
            const defaultHtml = "<i><h1>Preview</h1></i>";
            update(stores => {
                saveToStorage(emailType, defaultHtml);
                return { ...stores, [emailType]: defaultHtml };
            });
        }
    };
}

export const renderedEmailStore = createRenderedEmailStore();
