import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// In dev, /api calls are forwarded to the FastAPI server. In prod FastAPI serves dist/ itself.
export default defineConfig({ plugins: [react()], server: { proxy: { '/api': 'http://localhost:8000' } } });
