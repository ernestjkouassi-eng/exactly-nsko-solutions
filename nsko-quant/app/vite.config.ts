import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { viteStaticCopy } from 'vite-plugin-static-copy'

// CesiumJS needs its Workers, Assets, ThirdParty and Widgets served as static files under /cesium.
const cesium = 'node_modules/cesium/Build/Cesium'
export default defineConfig({
  plugins: [
    react(),
    viteStaticCopy({ targets: ['Workers', 'ThirdParty', 'Assets', 'Widgets'].map(d => ({ src: `${cesium}/${d}`, dest: 'cesium', rename: { stripBase: 4 } })) }),
  ],
  define: { CESIUM_BASE_URL: JSON.stringify('./cesium/') },
  // Tauri: fixed port for `tauri dev`, and keep the terminal readable
  server: { port: 5173, strictPort: true },
  clearScreen: false,
  build: {
    target: 'es2022',
    chunkSizeWarningLimit: 6000,   // the lazily loaded Cesium chunk is large by nature
  },
})
