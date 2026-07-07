import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ToastProvider } from "@/components/Toast";
import DashboardLayout from "@/components/DashboardLayout";
import AppWalletProvider from "@/components/AppWalletProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AlgoBounty — Decentralized Bounty Marketplace",
  description: "Find and create bounties on the Algorand blockchain. Earn crypto for building.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} dark`}>
      <body className="min-h-screen flex flex-col bg-[#0a0a0a] text-[#ededed] font-sans antialiased">
        <AppWalletProvider>
          <ToastProvider>
            <DashboardLayout>
              {children}
            </DashboardLayout>
          </ToastProvider>
        </AppWalletProvider>
      </body>
    </html>
  );
}
