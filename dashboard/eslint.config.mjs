import { dirname } from 'path'
import { fileURLToPath } from 'url'
import { FlatCompat } from '@eslint/eslintrc'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const compat = new FlatCompat({
  baseDirectory: __dirname,
})

/** @type {import('eslint').Linter.Config[]} */
const eslintConfig = [
  ...compat.extends('next/core-web-vitals', 'next/typescript'),
  {
    rules: {
      // Allow explicit `any` in places where SDK types are too loose
      '@typescript-eslint/no-explicit-any': 'warn',
      // Allow void-returning async callbacks (common with useEffect / onClick)
      '@typescript-eslint/no-floating-promises': 'off',
      // Next.js handles img optimisation — allow <img> in edge cases
      '@next/next/no-img-element': 'warn',
    },
  },
]

export default eslintConfig
