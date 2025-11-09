import { writable } from 'svelte/store';
import type { components } from '$lib/types/api';

type BEEmailData = components['schemas']['BEEmailData'];

const STORAGE_KEY_PREFIX = 'emailStore';

// Helper to get storage key for email type
function getStorageKey(emailType: string): string {
    return `${STORAGE_KEY_PREFIX}_${emailType}`;
}

// Helper to load from localStorage
function loadFromStorage(emailType: string): BEEmailData | undefined {
    if (typeof window === 'undefined') return undefined;
    try {
        const stored = localStorage.getItem(getStorageKey(emailType));
        return stored ? JSON.parse(stored) : undefined;
    } catch (error) {
        console.error('Failed to load from localStorage:', error);
        return undefined;
    }
}

// Helper to save to localStorage
function saveToStorage(emailType: string, data: BEEmailData | undefined) {
    if (typeof window === 'undefined') return;
    try {
        if (data) {
            localStorage.setItem(getStorageKey(emailType), JSON.stringify(data));
        } else {
            localStorage.removeItem(getStorageKey(emailType));
        }
    } catch (error) {
        console.error('Failed to save to localStorage:', error);
    }
}

function createEmailStore() {
    const { subscribe, set, update } = writable<Record<string, any>>({});

    return {
        subscribe,
        get: (emailType: string) => {
            let value: any;
            subscribe(stores => { value = stores[emailType]; })();
            return value;
        },
        set: (emailType: string, value: any) => {
            update(stores => {
                const updated = { ...stores, [emailType]: value };
                saveToStorage(emailType, value);
                return updated;
            });
        },
        async fetch(emailType: string = 'be') {
            try {
                const response = await fetch(`http://localhost:8000/emails/${emailType}`);
                const data = await response.json();
                update(stores => {
                    saveToStorage(emailType, data);
                    return { ...stores, [emailType]: data };
                });
                return data;
            } catch (error) {
                console.error('Failed to fetch email data:', error);
                throw error;
            }
        },
        clear(emailType: string) {
            update(stores => {
                const updated = { ...stores };
                delete updated[emailType];
                saveToStorage(emailType, undefined);
                return updated;
            });
        }
    };
}

export const emailStore = createEmailStore();
