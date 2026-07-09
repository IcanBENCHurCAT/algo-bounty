/** @type {import('next').NextConfig} */
const nextConfig = {
  // Required for multi-stage Docker builds — outputs a self-contained server
  // in .next/standalone that only needs `node server.js` to run.
  output: 'standalone',

  webpack: (config, { isServer }) => {
    if (!isServer) {
      try {
        const { webpackFallback } = require('@txnlab/use-wallet-react')
        config.resolve.fallback = {
          ...config.resolve.fallback,
          ...webpackFallback,
        }
      } catch {
        // use-wallet not yet installed, skip
      }
    }
    return config
  },
}

module.exports = nextConfig
