import { Dashboard } from "./components/Dashboard";
import { ConnectButton } from "./components/ConnectButton";
import { GasPrice } from "./components/GasPrice";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex items-center h-14">
          <div className="flex items-center space-x-2">
            <div className="flex justify-center items-center w-8 h-8 rounded-full bg-primary">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-primary-foreground">
                <path d="M12 2L2 7l10 5 10-5-10-5z" />
                <path d="M2 17l10 5 10-5" />
                <path d="M2 12l10 5 10-5" />
              </svg>
            </div>
            <h1 className="text-xl font-bold text-primary">DeFi Risk Monitor</h1>
          </div>
          <div className="flex flex-1 justify-end items-center space-x-4">
            <div className="hidden md:block">
              <GasPrice />
            </div>
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
        <div className="container flex flex-col gap-4 justify-between items-center md:h-24 md:flex-row">
          <p className="text-sm leading-loose text-center text-muted-foreground md:text-left">© {new Date().getFullYear()} DeFi Risk Monitor. 保护您的DeFi投资安全。</p>
        </div>
      </footer>
    </div>
  );
}
