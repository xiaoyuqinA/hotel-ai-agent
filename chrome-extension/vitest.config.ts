import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['tests/unit/**/*.test.ts', 'tests/integration/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.ts'],
      exclude: ['src/**/*.d.ts', 'src/popup/index.html'],
    },
  },
})
