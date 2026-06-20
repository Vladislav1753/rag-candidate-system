import type { Metadata } from "next";
import { Space_Grotesk, Space_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/Nav";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  display: "swap",
});

const spaceMono = Space_Mono({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-space-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "signal — candidate search",
  description:
    "A relevance instrument for recruiters. Semantic candidate search and onboarding over pgvector + OpenAI.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${spaceMono.variable}`}>
      <body className="min-h-screen grain">
        <Nav />
        <main className="mx-auto w-full max-w-5xl px-5 pb-24 sm:px-8">
          {children}
        </main>
      </body>
    </html>
  );
}
