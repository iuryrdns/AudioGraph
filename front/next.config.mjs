/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          {
            key: 'Content-Security-Policy',
            value:
              "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.mzstatic.com https://*.dzcdn.net https://*.deezer.com; media-src 'self' data: blob: https://audio-ssl.itunes.apple.com https://*.dzcdn.net https://*.deezer.com; font-src 'self' data:; connect-src 'self' http://127.0.0.1:8000 http://localhost:8000 http://backend:8000 https://itunes.apple.com ws://localhost:3000 ws://127.0.0.1:3000; worker-src 'self' blob:; child-src 'self' blob:; object-src 'none'; base-uri 'self';",
          },
        ],
      },
    ]
  },
}

export default nextConfig
