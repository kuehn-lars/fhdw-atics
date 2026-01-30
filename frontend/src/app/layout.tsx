import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "FHDW Atics",
  description: "LLM Chatbot with RAG Capabilities",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className="dark">
      <body className={`${inter.className} bg-[#131314] text-[#E3E3E3] antialiased`}>
        {children}
      </body>
    </html>
  );
}
