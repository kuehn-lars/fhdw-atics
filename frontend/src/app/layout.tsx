import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atics | AI Platform",
  description: "Next Generation Agentic Workspace",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="dark">
      <body className="antialiased min-h-screen">
        {children}
      </body>
    </html>
  );
}
