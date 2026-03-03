import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) return
          if (
            id.includes('react/') ||
            id.includes('react-dom/') ||
            id.includes('react-router-dom/') ||
            id.includes('zustand/')
          ) {
            return 'vendor'
          }
          if (id.includes('@clerk/')) {
            return 'clerk'
          }
          if (
            id.includes('katex') ||
            id.includes('remark-math') ||
            id.includes('rehype-katex') ||
            id.includes('react-syntax-highlighter')
          ) {
            return 'markdown-enhanced'
          }
          if (
            id.includes('react-markdown') ||
            id.includes('remark-') ||
            id.includes('rehype-')
          ) {
            return 'markdown-base'
          }
        },
      },
    },
  },
  server: {
    host: '0.0.0.0', // Listen on all interfaces for Docker
    port: 5173,
    strictPort: true,
    watch: {
      usePolling: true, // Required for Docker hot reload
    },
    proxy: {
      '/api': {
        target: 'http://app:8000/api/v1',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
