import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/AuthContext";
import { ParlayProvider } from "@/lib/ParlayContext";
import AuthHeader from "@/components/AuthHeader";
import ParlayPanel from "@/components/ParlayPanel";

export const metadata: Metadata = {
  title: "Parlay Pros",
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
        <AuthProvider>
          <ParlayProvider>
            <AuthHeader />
            {children}
            <ParlayPanel />
          </ParlayProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
