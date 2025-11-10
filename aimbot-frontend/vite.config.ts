import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		proxy: {
			// Proxy API calls to FastAPI during development
			'/radio': 'http://localhost:8000',
			'/emails': 'http://localhost:8000',
			'/news_stories': 'http://localhost:8000'
		}
	}
});
