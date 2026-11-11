import "@fontsource-variable/bricolage-grotesque/wdth.css";
import "@fontsource-variable/hanken-grotesk/wght.css";
import "@fontsource-variable/spline-sans-mono/wght.css";
import "./globals.css";

import type { Metadata, Viewport } from "next";

import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "Intern Radar: student roles at UAE employers, read hourly", template: "%s · Intern Radar" },
  description:
    "Internships, graduate programmes and first jobs at UAE employers, read every hour from the employers' own career systems. Each role shows who can apply, when it starts and how long it runs, beside the sentence it was read from.",
  applicationName: "Intern Radar",
  alternates: {
    canonical: "/",
    types: { "application/atom+xml": "/feed.xml", "application/feed+json": "/feed.json" },
  },
  openGraph: { type: "website", siteName: "Intern Radar", locale: "en_AE" },
  twitter: { card: "summary_large_image" },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fafafa" },
    { media: "(prefers-color-scheme: dark)", color: "#111111" },
  ],
};

// Runs before first paint so a saved theme never flashes the other one. Light is the default; dark follows a
// saved choice only, because most readers of this site open it in daylight between classes.
const themeScript = `try{var t=localStorage.getItem("ir-theme");if(t==="dark"||t==="light")document.documentElement.dataset.theme=t;else document.documentElement.dataset.theme="light"}catch(e){document.documentElement.dataset.theme="light"}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <a className="skip" href="#main">
          Skip to the list
        </a>
        <Header />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
