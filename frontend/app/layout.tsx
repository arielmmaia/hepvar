import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "HepVar — Hepatology Variant Intelligence",
  description: "Clinician-facing rare-variant interpretation for liver disease, powered by Opus 4.7.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="paper min-h-screen antialiased">{children}</body>
    </html>
  );
}
