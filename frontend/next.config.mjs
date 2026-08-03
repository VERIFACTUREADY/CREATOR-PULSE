/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // No se usa `output: 'standalone'`: haría que `next start` dejase de funcionar
  // y obligaría a arrancar el servidor generado a mano. La imagen de Docker es
  // algo mayor, pero el comando de arranque es el mismo en local y en el
  // contenedor, que es lo que evita errores.
  images: {
    // Las miniaturas públicas de YouTube se sirven desde estos dominios.
    remotePatterns: [
      { protocol: 'https', hostname: 'i.ytimg.com' },
      { protocol: 'https', hostname: 'yt3.ggpht.com' },
      { protocol: 'https', hostname: 'yt3.googleusercontent.com' },
    ],
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};

export default nextConfig;
