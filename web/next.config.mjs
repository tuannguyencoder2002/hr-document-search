/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Proxy API calls to the FastAPI backend (port 8000 by default) so the
  // frontend can call /api/* while the backend serves everything else.
  async rewrites() {
    const backend =
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return [
      { source: "/api/:path*", destination: `${backend}/:path*` },
    ];
  },
};

export default nextConfig;
