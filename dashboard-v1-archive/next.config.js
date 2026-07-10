/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        ...require('@txnlab/use-wallet-react').webpackFallback
      }
    }
    return config
  },
  turbopack: {}
}

module.exports = nextConfig
