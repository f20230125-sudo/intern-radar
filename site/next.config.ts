import type { NextConfig } from "next";

const isDev = process.env.NODE_ENV === "development";

// The page loads nothing from another site: fonts, scripts and data are its own. Posting text comes from
// employers' feeds, so it is treated as untrusted: it is only ever rendered as text, and this policy means a
// stray string could not pull in a script or send what it read anywhere even if that failed.
// 'unsafe-inline' is for the small scripts Next.js writes into each page and the one that sets the theme before
// first paint; nonces would stop pages being built ahead of time.
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self'${isDev ? " ws: wss:" : ""}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'self' https://uzair-khan-lac.vercel.app",
].join("; ");

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1"],
  devIndicators: false,
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
