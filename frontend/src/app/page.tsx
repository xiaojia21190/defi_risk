import { Dashboard } from "./components/Dashboard";
import { ConnectButton } from "./components/ConnectButton";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex items-center h-14">
          <div className="flex items-center space-x-2">
            <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-primary-foreground">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-primary">DeFi Risk Monitor</h1>
          </div>
          <div className="flex items-center justify-end flex-1 space-x-4">
            <ConnectButton />
          </div>
        </div>
      </header>

      <main className="container flex-1 py-6">
        <div className="space-y-8">
          <Dashboard />
        </div>
      </main>

      <footer className="py-6 border-t">
        <div className="container flex flex-col items-center justify-between gap-4 md:h-24 md:flex-row">
          <p className="text-sm leading-loose text-center text-muted-foreground md:text-left">© {new Date().getFullYear()} DeFi Risk Monitor. 保护您的DeFi投资安全。</p>
        </div>
      </footer>
    </div>
  );
}
