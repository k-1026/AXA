import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 환자용(web-platform)은 5173, 병원용은 5175
export default defineConfig({
  plugins: [react()],
  server: { port: 5175 },
});
