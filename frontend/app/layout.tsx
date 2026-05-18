import type { Metadata } from "next";
import "./globals.css";
import { ParlayProvider } from "@/lib/ParlayContext";
import ParlayPanel from "@/components/ParlayPanel";

export const metadata: Metadata = {
  title: "Parlay Calculator",
  description: "Real-time joint probability for sports betting parlays.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <ParlayProvider>
          {children}
          <ParlayPanel />
        </ParlayProvider>
      </body>
    </html>
  );
}
