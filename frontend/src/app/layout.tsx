import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Inter } from "next/font/google";

// 加载Inter字体
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f8fafc" },
    { media: "(prefers-color-scheme: dark)", color: "#0f172a" },
  ],
};

export const metadata: Metadata = {
  title: "DeFi Risk Monitor | 分析和监控您的DeFi投资风险",
  description: "全面的DeFi风险监控平台，帮助您分析和管理加密货币投资组合的风险",
  keywords: "DeFi, 风险监控, 加密货币, 区块链, 投资组合分析",
  authors: [{ name: "DeFi Risk Team" }],
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body className="min-h-screen bg-background text-foreground">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
