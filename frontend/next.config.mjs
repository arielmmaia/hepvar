/** @type {import('next').NextConfig} */
const nextConfig = {
  // Strict Mode double-mounts effects in dev. Each remount opens a new
  // EventSource and the backend replays every event on the new connection,
  // so the streamed reasoning appears to "loop from the start". Production
  // builds aren't affected, but dev is what we use for the demo recording.
  reactStrictMode: false,
  async rewrites() {
    return [
      { source: "/api/:path*", destination: "http://localhost:8000/api/:path*" },
    ];
  },
};
export default nextConfig;
