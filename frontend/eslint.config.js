import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import importX from 'eslint-plugin-import-x'
import vitest from '@vitest/eslint-plugin'
import testingLibrary from 'eslint-plugin-testing-library'
import prettier from 'eslint-config-prettier'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'coverage']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommendedTypeChecked,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
      importX.flatConfigs.recommended,
      importX.flatConfigs.typescript,
    ],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    settings: {
      'import-x/resolver': { typescript: true, node: true },
    },
    rules: {
      'import-x/no-cycle': 'error',
      // Bulletproof React boundaries: shared -> features -> app. Features never import each
      // other, except that feed renders paper's CardActions on its cards (feed -> paper only).
      'import-x/no-restricted-paths': [
        'error',
        {
          basePath: import.meta.dirname,
          zones: [
            {
              target: './src/features/feed',
              from: './src/features',
              except: ['./feed', './paper'],
            },
            { target: './src/features/paper', from: './src/features', except: ['./paper'] },
            { target: './src/features/profile', from: './src/features', except: ['./profile'] },
            { target: './src/features/auth', from: './src/features', except: ['./auth'] },
            { target: './src/features/landing', from: './src/features', except: ['./landing'] },
            { target: './src/features', from: './src/app' },
            {
              target: ['./src/components', './src/lib', './src/stores', './src/types'],
              from: ['./src/features', './src/app'],
            },
          ],
        },
      ],
      'import-x/no-named-as-default': 'off', // clsx and friends export the same name both ways
      'import-x/no-unresolved': 'off', // tsc owns module resolution (?raw imports etc.)
      'import-x/order': [
        'error',
        {
          groups: ['builtin', 'external', 'internal', ['parent', 'sibling', 'index'], 'type'],
          'newlines-between': 'never',
        },
      ],
      // Async handlers passed to JSX props are a normal React pattern.
      '@typescript-eslint/no-misused-promises': [
        'error',
        { checksVoidReturn: { attributes: false } },
      ],
    },
  },
  {
    files: ['tests/**/*.{ts,tsx}'],
    extends: [vitest.configs.recommended, testingLibrary.configs['flat/react']],
    languageOptions: { globals: { ...globals.browser, ...vitest.environments.env.globals } },
    rules: {
      // Test bodies mock freely; the strictness belongs in src.
      '@typescript-eslint/no-unsafe-assignment': 'off',
      '@typescript-eslint/no-unsafe-member-access': 'off',
      '@typescript-eslint/no-unsafe-argument': 'off',
      '@typescript-eslint/no-unsafe-return': 'off',
      '@typescript-eslint/no-unsafe-call': 'off',
      '@typescript-eslint/unbound-method': 'off',
      // DOM-level assertions (KaTeX output, generated ids) are legitimate here.
      'testing-library/no-container': 'off',
      'testing-library/no-node-access': 'off',
    },
  },
  {
    files: ['*.config.{ts,js}', 'vite.config.ts', 'vitest.config.ts'],
    extends: [tseslint.configs.disableTypeChecked],
  },
  prettier,
])
