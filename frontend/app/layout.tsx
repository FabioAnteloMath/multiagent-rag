import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Support Copilot - AI Technical Assistant",
    description: "Multi-agent RAG system for technical support with intelligent routing",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en">
            <body className={`${inter.className} min-h-screen bg-slate-50 text-slate-900 antialiased`}>
                <nav className="stick top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
                    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="flex items-center justify-between h-16">
                            <Link href="/" className="flex items-center gap-2">
                                <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
                                    <span className="text-white text-sm font-bold">SC</span>
                                </div>
                                <span className="text-lg font-semibold text-slate-900">Support Copilot</span>
                            </Link>
                            <div className="hidden md:flex items-center gap-1">
                                <Link href="/documents" className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors">
                                    Documents
                                </Link>
                                <Link href="/collections" className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors">
                                    Collections
                                </Link>
                                <Link href="/agents" className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors">
                                    Agents
                                </Link>
                                <Link href="/chat" className="ml-2 px-4 py-2 text-sm font-medium bg-blue-500 text-white hover:bg-blue-600 rounded-lg transition-colors">
                                    Chat
                                </Link>
                            </div>
                            <button className="md:hidden p-2 text-slate-600">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                                </svg>
                            </button>
                        </div>
                    </div>
                </nav>
                <main className="flex-1">
                    {children}
                </main>
                <footer className="border-t border-slate-200 bg-white py-6">
                    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-slate-500">
                        Support Copilot v0.3.0
                    </div>
                </footer>
            </body>
        </html>
    );
}