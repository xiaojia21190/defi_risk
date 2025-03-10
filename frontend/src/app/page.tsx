import type { Metadata } from "next";
import { Dashboard } from "./components/Dashboard";
import { ConnectButton } from "./components/ConnectButton";
import Link from "next/link";
import ProtocolList from "./components/ProtocolList";

export const metadata: Metadata = {
  title: "DeFi Risk Monitor",
  description: "Monitor and analyze your DeFi portfolio risks",
  metadataBase: new URL("http://localhost:3000"),
};

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-br from-background to-background/80">
      <header className="sticky top-0 z-10 backdrop-blur-sm bg-background/80 border-b border-border">
        <div className="container mx-auto px-4 py-4 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-r from-primary to-accent flex items-center justify-center">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-white">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">DeFi Risk Monitor</h1>
          </div>
          <div className="flex items-center space-x-4">
            <Link href="/guide" className="px-4 py-2 rounded-full bg-accent/10 text-accent text-sm font-medium hover:bg-accent/20 transition-colors">
              黑客松指南
            </Link>
            <ConnectButton />
          </div>
        </div>
      </header>

      <main className="flex-1 container mx-auto px-4 py-6">
        <div className="space-y-8">
          <Dashboard />
          <ProtocolList />
        </div>
      </main>

      <footer className="border-t border-border py-6 text-center text-sm text-muted">
        <div className="container mx-auto px-4">
          <p>© {new Date().getFullYear()} DeFi Risk Monitor. 保护您的DeFi投资安全。</p>
        </div>
      </footer>
    </div>
  );
}
