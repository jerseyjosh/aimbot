import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [sveltekit()],
	base: '/app/',  // Set base path for production builds
	server: {
		proxy: {
			// Proxy everything to FastAPI
			'/': 'http://localhost:8000'
		}
	}
});
