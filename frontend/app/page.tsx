import Link from "next/link";

export default function Home() {
    return (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center mb-16">
                <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-600 rounded-full text-sm font-medium mb-6">
                    <span className="w-2 h-2 bg-blue-500 rounded-full"></span>
                    AI-Powered Technical Support
                </div>
                <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4 tracking-tight">
                    Support Copilot
                </h1>
                <p className="text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
                    Intelligent technical support system with multi-agent routing.
                    Get accurate answers from your documentation in seconds.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-16">
                <Link
                    href="/chat"
                    className="group bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-lg hover:border-blue-200 transition-all duration-300"
                >
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-semibold text-slate-900 mb-2">Chat</h2>
                    <p className="text-slate-600 text-sm">
                        Ask questions and get answers from specialized agents
                    </p>
                </Link>

                <Link
                    href="/documents"
                    className="group bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-lg hover:border-emerald-200 transition-all duration-300"
                >
                    <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-emerald-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-semibold text-slate-900 mb-2">Documents</h2>
                    <p className="text-slate-600 text-sm">
                        Upload and manage your support documentation
                    </p>
                </Link>

                <Link
                    href="/collections"
                    className="group bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-lg hover:border-purple-200 transition-all duration-300"
                >
                    <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-semibold text-slate-900 mb-2">Collections</h2>
                    <p className="text-slate-600 text-sm">
                        Organize documents by knowledge area
                    </p>
                </Link>

                <Link
                    href="/usage"
                    className="group bg-white border border-slate-200 rounded-2xl p-6 hover:shadow-lg hover:border-slate-400 transition-all duration-300"
                >
                    <div className="w-12 h-12 bg-gradient-to-br from-slate-700 to-slate-900 rounded-xl flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                        </svg>
                    </div>
                    <h2 className="text-xl font-semibold text-slate-900 mb-2">Usage</h2>
                    <p className="text-slate-600 text-sm">
                        Provider quota, fallback chain &amp; circuit-breaker state
                    </p>
                </Link>
            </div>

            <div className="bg-white border border-slate-200 rounded-2xl p-8">
                <h2 className="text-2xl font-semibold text-slate-900 mb-6">How it works</h2>
                <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                    <div className="text-center">
                        <div className="w-10 h-10 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-3">1</div>
                        <h3 className="font-medium text-slate-900 mb-1">Upload Documents</h3>
                        <p className="text-sm text-slate-600">Add PDF, MD, or TXT files to your knowledge base</p>
                    </div>
                    <div className="text-center">
                        <div className="w-10 h-10 bg-emerald-100 text-emerald-600 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-3">2</div>
                        <h3 className="font-medium text-slate-900 mb-1">Organize</h3>
                        <p className="text-sm text-slate-600">Group documents into collections by topic</p>
                    </div>
                    <div className="text-center">
                        <div className="w-10 h-10 bg-purple-100 text-purple-600 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-3">3</div>
                        <h3 className="font-medium text-slate-900 mb-1">Ask</h3>
                        <p className="text-sm text-slate-600">Chat with the copilot using natural language</p>
                    </div>
                    <div className="text-center">
                        <div className="w-10 h-10 bg-orange-100 text-orange-600 rounded-full flex items-center justify-center text-lg font-bold mx-auto mb-3">4</div>
                        <h3 className="font-medium text-slate-900 mb-1">Get Answers</h3>
                        <p className="text-sm text-slate-600">Receive accurate answers with source citations</p>
                    </div>
                </div>
            </div>
        </div>
    );
}