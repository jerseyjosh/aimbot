import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			// Proxy all /api/* calls to FastAPI backend
			'/api': {
				target: 'http://localhost:8000',
				changeOrigin: true
			}
		}
	}
});
