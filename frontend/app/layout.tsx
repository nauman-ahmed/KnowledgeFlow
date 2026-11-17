import { ClerkProvider } from "@clerk/nextjs";
import { AuthRedirectHandler } from "@/components/auth/AuthRedirectHandler";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "KnowledgeFlow",
  description: "AI knowledge assistant with a curated document library",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html
        lang="en"
        className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      >
        {/* Browser extensions (Grammarly, ColorZilla) inject attributes on <body>
            before React hydrates; this only silences attribute diffs on this tag. */}
        <body
          className="min-h-full flex flex-col bg-neutral-900 text-neutral-100"
          suppressHydrationWarning
        >
          <AuthRedirectHandler />
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
