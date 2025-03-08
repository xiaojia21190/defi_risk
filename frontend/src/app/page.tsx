import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Providers } from "./providers";
import { Dashboard } from "./components/Dashboard";
import { ConnectButton } from "./components/ConnectButton";
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "DeFi Risk Monitor",
  description: "Monitor and analyze your DeFi portfolio risks",
  metadataBase: new URL("http://localhost:3000"),
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex flex-col items-center justify-center h-screen w-screen">
      <div className="flex justify-between items-center w-full">
        <h1 className="text-2xl font-bold">DeFi Risk Monitor</h1>
        <ConnectButton></ConnectButton>
      </div>
      <div className="flex-1 w-full h-full">
        <Dashboard />
      </div>
    </div>
  );
}
