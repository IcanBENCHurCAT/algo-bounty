/** @type {import('eslint').Linter.Config} */
const eslintConfig = {
  extends: ['next/core-web-vitals'],
  rules: {
    '@typescript-eslint/no-explicit-any': 'warn',
    '@typescript-eslint/no-floating-promises': 'off',
    '@next/next/no-img-element': 'warn',
  }
}

export default eslintConfig

