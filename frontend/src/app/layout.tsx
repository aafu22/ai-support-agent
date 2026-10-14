import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Helpdesk AI — customer support that knows your business",
  description: "Upload your knowledge, let an AI agent answer customers with sources, and hand over to humans when it matters.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
