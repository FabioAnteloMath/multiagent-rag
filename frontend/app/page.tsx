import Link from "next/link";

export default function Home() {
    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
            <div className="text-center mb-12">
                <h1 className="text-4xl font-bold text-white mb-4">
                    Multiagent RAG - Support Copilot
                </h1>
                <p className="text-lg text-slate-400 max-w-2xl mx-auto">
                    Technical support system with RAG, specialized multi-agents, and document management
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
                <Link
                    href="/documents"
                    className="group bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-blue-500 transition-all"
                >
                    <div className="text-3xl mb-3">📄</div>
                    <h2 className="text-xl font-semibold text-white mb-2 group-hover:text-blue-400 transition-colors">
                        Documents
                    </h2>
                    <p className="text-slate-400 text-sm">
                        Upload, view, and manage documents
                    </p>
                </Link>

                <Link
                    href="/collections"
                    className="group bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-purple-500 transition-all"
                >
                    <div className="text-3xl mb-3">📚</div>
                    <h2 className="text-xl font-semibold text-white mb-2 group-hover:text-purple-400 transition-colors">
                        Collections
                    </h2>
                    <p className="text-slate-400 text-sm">
                        Organize documents by knowledge area
                    </p>
                </Link>

                <Link
                    href="/agents"
                    className="group bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-green-500 transition-all"
                >
                    <div className="text-3xl mb-3">🤖</div>
                    <h2 className="text-xl font-semibold text-white mb-2 group-hover:text-green-400 transition-colors">
                        Agents
                    </h2>
                    <p className="text-slate-400 text-sm">
                        Specialized agents for knowledge areas
                    </p>
                </Link>

                <Link
                    href="/chat"
                    className="group bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-amber-500 transition-all"
                >
                    <div className="text-3xl mb-3">💬</div>
                    <h2 className="text-xl font-semibold text-white mb-2 group-hover:text-amber-400 transition-colors">
                        Chat
                    </h2>
                    <p className="text-slate-400 text-sm">
                        Chat with the copilot using Baseline or Multi-agent
                    </p>
                </Link>
            </div>

            <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
                <h2 className="text-xl font-semibold text-white mb-4">About the Project</h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                        <h3 className="text-blue-400 font-medium mb-2">Tech Stack</h3>
                        <ul className="text-slate-400 text-sm space-y-1">
                            <li>Backend: FastAPI + SQLAlchemy + SQLite</li>
                            <li>Frontend: Next.js 14 + Tailwind</li>
                            <li>RAG: LangChain + LangGraph</li>
                            <li>Vector Store: FAISS / ChromaDB</li>
                            <li>LLM: Ollama (llama3.2:3b)</li>
                        </ul>
                    </div>
                    <div>
                        <h3 className="text-purple-400 font-medium mb-2">Features</h3>
                        <ul className="text-slate-400 text-sm space-y-1">
                            <li>Document management</li>
                            <li>Collections for organization</li>
                            <li>Specialized agents</li>
                            <li>Toggle Baseline vs Multi-agent</li>
                            <li>Source citations</li>
                        </ul>
                    </div>
                    <div>
                        <h3 className="text-green-400 font-medium mb-2">How to Use</h3>
                        <ul className="text-slate-400 text-sm space-y-1">
                            <li>1. Upload documents at /documents</li>
                            <li>2. Create collections to organize</li>
                            <li>3. Configure specialized agents</li>
                            <li>4. Use chat to ask questions</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
}