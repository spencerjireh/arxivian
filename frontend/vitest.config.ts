import { defineConfig, mergeConfig } from 'vitest/config'
import viteConfig from './vite.config'

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./tests/setup.ts'],
      include: ['tests/**/*.test.{ts,tsx}'],
      coverage: {
        provider: 'v8',
        include: ['src/**/*.{ts,tsx}'],
        exclude: ['src/main.tsx', 'src/vite-env.d.ts', 'src/types/**'],
        reporter: ['text-summary', 'lcov'],
        // Ratchet: set to the measured value on 2026-09-26; raise, never lower.
        thresholds: { lines: 78, statements: 77, functions: 73, branches: 71 },
      },
    },
  })
)
