import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
    title: "Multiagent RAG - Support Copilot",
    description: "Technical support assistant with RAG and multi-agents",
};

export default function RootLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return (
        <html lang="en" className="dark">
            <body className={`${inter.className} min-h-screen bg-slate-900 text-slate-100`}>
                <nav className="border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm sticky top-0 z-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <div className="flex items-center justify-between h-16">
                            <div className="flex items-center gap-8">
                                <Link href="/" className="text-xl font-semibold text-blue-400">
                                    Support Copilot
                                </Link>
                                <div className="hidden md:flex items-center gap-6">
                                    <Link href="/documents" className="text-slate-300 hover:text-white transition-colors">
                                        Documents
                                    </Link>
                                    <Link href="/collections" className="text-slate-300 hover:text-white transition-colors">
                                        Collections
                                    </Link>
                                    <Link href="/agents" className="text-slate-300 hover:text-white transition-colors">
                                        Agents
                                    </Link>
                                    <Link href="/chat" className="text-slate-300 hover:text-white transition-colors">
                                        Chat
                                    </Link>
                                </div>
                            </div>
                            <div className="flex items-center gap-4">
                                <span className="text-xs text-slate-500">v0.2.0</span>
                            </div>
                        </div>
                    </div>
                </nav>
                <main className="flex-1">
                    {children}
                </main>
            </body>
        </html>
    );
}