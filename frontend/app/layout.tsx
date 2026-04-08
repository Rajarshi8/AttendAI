import type { Metadata } from "next";
import { Space_Grotesk, IBM_Plex_Mono } from "next/font/google";

import { Navbar } from "@/components/Navbar";
import { ThemeProvider } from "@/components/ThemeProvider";

import "./globals.css";

const headingFont = Space_Grotesk({ subsets: ["latin"], variable: "--font-heading" });
const monoFont = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "AttendAI - Face Attendance",
  description: "Production-ready Face Recognition Attendance System",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${headingFont.variable} ${monoFont.variable} font-[var(--font-heading)]`}>
        <ThemeProvider>
          <div className="relative min-h-screen">
            <Navbar />
            <main className="mx-auto max-w-6xl px-4 py-6 md:px-6 md:py-8">{children}</main>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}
