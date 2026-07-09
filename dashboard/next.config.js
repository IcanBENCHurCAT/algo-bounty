/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for multi-stage Docker builds — outputs a self-contained server
  // in .next/standalone that only needs `node server.js` to run.
  output: 'standalone',

  // Silence Turbopack warning when custom webpack config is present in Next.js 16+
  turbopack: {},

  webpack: (config, { isServer }) => {
    // Treat optional/peer dependencies of use-wallet as external so webpack does not fail on missing imports
    config.externals = [...(config.externals || []), {
      '@agoralabs-sh/avm-web-provider': 'commonjs @agoralabs-sh/avm-web-provider',
      '@walletconnect/modal': 'commonjs @walletconnect/modal',
      '@walletconnect/sign-client': 'commonjs @walletconnect/sign-client',
      'lute-connect': 'commonjs lute-connect',
      '@walletconnect/types': 'commonjs @walletconnect/types'
    }]

    if (!isServer) {
      try {
        const { webpackFallback } = require('@txnlab/use-wallet-react')
        config.resolve.fallback = {
          ...config.resolve.fallback,
          ...webpackFallback,
          '@agoralabs-sh/avm-web-provider': false,
          '@walletconnect/modal': false,
          '@walletconnect/sign-client': false,
          'lute-connect': false,
          '@walletconnect/types': false,
        }
      } catch {
        // use-wallet not yet installed, skip
      }
    }
    return config
  },
}

module.exports = nextConfig
