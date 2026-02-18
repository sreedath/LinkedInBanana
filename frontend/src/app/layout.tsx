import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { AuthGuard } from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "LinkedInBanana by Vizuara",
  description:
    "Generate visually compelling LinkedIn images from YouTube playlists using AI",
  icons: {
    icon: "/favicon.ico",
    apple: "/apple-touch-icon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <Providers>
          <header className="border-b bg-white">
            <div className="mx-auto max-w-5xl px-4 py-4 flex items-center gap-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/favicon.png" alt="Vizuara" className="h-8 w-8" />
              <h1 className="text-xl font-bold text-gray-900">
                LinkedInBanana
              </h1>
              <span className="text-sm text-gray-500">
                by Vizuara
              </span>
            </div>
          </header>
          <main className="mx-auto max-w-5xl px-4 py-8">
            <AuthGuard>{children}</AuthGuard>
          </main>
        </Providers>
      </body>
    </html>
  );
}
