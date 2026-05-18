"use client";

import { useState, useRef, useEffect } from "react";
import { askQuestion, healthCheck, type AskResponse } from "@/lib/api";

interface Message {
    id: string;
    role: "user" | "assistant";
    content: string;
    sources?: string[];
    agent_used?: string[];
    steps?: string[];
    timestamp: Date;
    needs_clarifying?: boolean;
    tokens_used?: number;
    thinking?: string;
    model_used?: string;
    total_time_ms?: number;
    confidence?: number;
    collection_searched?: string;
}

const agentColors: Record<string, string> = {
    "API Support Agent": "bg-blue-500/20 text-blue-400",
    "Database Agent": "bg-green-500/20 text-green-400",
    "DevOps Agent": "bg-purple-500/20 text-purple-400",
    "Generalist Agent": "bg-slate-500/20 text-slate-400",
    "baseline": "bg-slate-500/20 text-slate-400",
};

const defaultAgentColor = "bg-slate-500/20 text-slate-400";

const baselineInfo = {
    title: "Baseline Mode",
    icon: "📊",
    description: "Simple vector search + LLM response without agent delegation. Uses a single FAISS index containing all documents.",
    useCases: [
        "Performance comparison - measure multi-agent gains",
        "Fallback if agents fail",
        "Simple benchmark baseline",
    ],
};

const masterAgentInfo = {
    title: "MasterAgent Mode",
    icon: "🎯",
    description: "Intelligent routing that classifies your question and delegates to specialized agents running in parallel.",
    howItWorks: [
        { step: "1. Classify", desc: "LLM determines which knowledge areas are relevant" },
        { step: "2. Delegate", desc: "Selected agents search their collection-specific indexes" },
        { step: "3. Aggregate", desc: "Responses from all agents are combined" },
    ],
    agents: [
        { name: "API Support Agent", color: "text-blue-400", icon: "🔧", docs: "HTTP errors, authentication, JWT, gateway" },
        { name: "Database Agent", color: "text-green-400", icon: "🗄️", docs: "Postgres, Redis, queries, cache" },
        { name: "DevOps Agent", color: "text-purple-400", icon: "🚀", docs: "Deploy, rollback, CI/CD, monitoring" },
        { name: "Generalist Agent", color: "text-slate-400", icon: "🤖", docs: "General questions, fallback" },
    ],
};

const singleRagInfo = {
    title: "Single RAG Mode",
    icon: "🎯",
    description: "Classifies your question and routes to ONE best-matching specialized agent. Returns a single clean answer from the selected collection.",
    howItWorks: [
        { step: "1. Classify", desc: "LLM determines which single knowledge area is most relevant" },
        { step: "2. Search", desc: "Only the selected collection is searched" },
        { step: "3. Answer", desc: "A single response is generated from one agent" },
    ],
    benefits: [
        "Cleaner responses (no conflicting answers)",
        "Faster execution (single agent)",
        "Easier to debug",
        "Lower token usage",
    ],
};

function getDisplayContent(msg: Message): { agentName: string; content: string } {
    if (msg.agent_used && msg.agent_used.length > 0) {
        return { agentName: "MasterAgent", content: msg.content };
    }
    return { agentName: msg.agent_used?.[0] || "MasterAgent", content: msg.content };
}

function formatTime(ms: number): string {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
}

function renderContent(text: string): string {
    return text
        .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold text-white mt-4 mb-2">$1</h3>')
        .replace(/^## (.*$)/gim, '<h2 class="text-xl font-semibold text-white mt-4 mb-2">$1</h2>')
        .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold text-white mt-4 mb-2">$1</h1>')
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
        .replace(/\*(.*?)\*/g, '<em class="text-slate-300">$1</em>')
        .replace(/^- (.*$)/gim, '<li class="text-slate-300 ml-4 list-none">• $1</li>')
        .replace(/^(\d+)\. (.*$)/gim, '<li class="text-slate-300 ml-4 list-none">$1. $2</li>')
        .replace(/\|(.*?)\|/g, (match) => {
            const cells = match.split('|').filter(c => c.trim());
            return `<div class="flex border-b border-slate-600 py-1"><span class="flex-1 text-slate-300">${cells.join('</span><span class="flex-1 text-slate-300">')}</span></div>`;
        })
        .split('\n\n')
        .map(p => p.trim())
        .filter(p => p)
        .map(p => {
            if (p.startsWith('<h') || p.startsWith('<li')) {
                return p;
            }
            return `<p class="text-slate-200 mb-3 leading-relaxed">${p.replace(/\n/g, '<br/>')}</p>`;
        })
        .join('');
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    const [mode, setMode] = useState<"baseline" | "auto" | "single_rag">("auto");
    const [forceAgent, setForceAgent] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [apiOnline, setApiOnline] = useState(false);
    const [showInfo, setShowInfo] = useState<"baseline" | "masteragent" | "single_rag" | null>(null);
    const [expandedMeta, setExpandedMeta] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        checkHealth();
        const interval = setInterval(checkHealth, 30000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    async function checkHealth() {
        try {
            await healthCheck();
            setApiOnline(true);
        } catch {
            setApiOnline(false);
        }
    }

    async function handleSend() {
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setLoading(true);

        try {
            const response: AskResponse = await askQuestion(
                input.trim(),
                4,
                mode,
                forceAgent || undefined
            );

            const assistantMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: response.answer,
                sources: response.sources,
                agent_used: response.agent_used,
                steps: response.steps,
                timestamp: new Date(),
                needs_clarifying: response.needs_clarifying,
                tokens_used: response.tokens_used,
                thinking: response.thinking,
                model_used: response.model_used,
                total_time_ms: response.total_time_ms,
                confidence: response.confidence,
                collection_searched: response.collection_searched,
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Failed to ask:", error);
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: "Error processing response. Try again.",
                timestamp: new Date(),
            };
            setMessages((prev) => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    }

    function handleKeyPress(e: React.KeyboardEvent) {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    }

    return (
        <div className="flex flex-col h-[calc(100vh-64px)] max-w-5xl mx-auto px-4">
            <div className="flex items-center justify-between py-4 border-b border-slate-700">
                <div className="flex items-center gap-4">
                    <span className={`flex items-center gap-2 text-sm ${apiOnline ? "text-green-400" : "text-red-400"}`}>
                        <span className={`w-2 h-2 rounded-full ${apiOnline ? "bg-green-500" : "bg-red-500"}`} />
                        {apiOnline ? "API Online" : "API Offline"}
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-sm text-slate-400 mr-2">Mode:</span>
                    <button
                        onClick={() => setMode("baseline")}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            mode === "baseline"
                                ? "bg-slate-600 text-white"
                                : "bg-slate-700 text-slate-400 hover:text-white"
                        }`}
                    >
                        Baseline
                    </button>
                    <button
                        onClick={() => setMode("auto")}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            mode === "auto"
                                ? "bg-blue-600 text-white"
                                : "bg-slate-700 text-slate-400 hover:text-white"
                        }`}
                    >
                        MasterAgent
                    </button>
                    <button
                        onClick={() => setMode("single_rag")}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            mode === "single_rag"
                                ? "bg-emerald-600 text-white"
                                : "bg-slate-700 text-slate-400 hover:text-white"
                        }`}
                    >
                        Single RAG
                    </button>
                    <button
                        onClick={() => setShowInfo(showInfo ? null : mode === "baseline" ? "baseline" : mode === "single_rag" ? "single_rag" : "masteragent")}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                            showInfo ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-400 hover:text-white"
                        }`}
                    >
                        ?
                    </button>
                </div>
            </div>

            {showInfo && showInfo === "baseline" && (
                <div className="bg-slate-800/70 border border-slate-600 rounded-xl p-5 mb-4">
                    <div className="flex items-start gap-4">
                        <span className="text-3xl">{baselineInfo.icon}</span>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-white mb-2">{baselineInfo.title}</h3>
                            <p className="text-slate-300 text-sm mb-3">{baselineInfo.description}</p>
                            <div className="flex flex-wrap gap-2">
                                {baselineInfo.useCases.map((use, idx) => (
                                    <span key={idx} className="inline-flex items-center gap-1 bg-slate-700/50 px-3 py-1 rounded-full text-xs text-slate-300">
                                        {use}
                                    </span>
                                ))}
                            </div>
                        </div>
                        <button
                            onClick={() => setShowInfo(null)}
                            className="text-slate-500 hover:text-white transition-colors"
                        >
                            ✕
                        </button>
                    </div>
                </div>
            )}

            {showInfo && showInfo === "masteragent" && (
                <div className="bg-slate-800/70 border border-slate-600 rounded-xl p-5 mb-4">
                    <div className="flex items-start gap-4 mb-4">
                        <span className="text-3xl">{masterAgentInfo.icon}</span>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-white mb-2">{masterAgentInfo.title}</h3>
                            <p className="text-slate-300 text-sm">{masterAgentInfo.description}</p>
                        </div>
                        <button
                            onClick={() => setShowInfo(null)}
                            className="text-slate-500 hover:text-white transition-colors"
                        >
                            ✕
                        </button>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                        {masterAgentInfo.agents.map((agent) => (
                            <div key={agent.name} className="bg-slate-700/50 rounded-lg p-3">
                                <div className="flex items-center gap-2 mb-1">
                                    <span>{agent.icon}</span>
                                    <span className={`text-sm font-medium ${agent.color}`}>{agent.name}</span>
                                </div>
                                <p className="text-xs text-slate-400">{agent.docs}</p>
                            </div>
                        ))}
                    </div>
                    <div className="border-t border-slate-600 pt-3">
                        <p className="text-xs text-slate-400 mb-2">How it works:</p>
                        <div className="flex flex-wrap gap-3">
                            {masterAgentInfo.howItWorks.map((item) => (
                                <div key={item.step} className="flex items-center gap-2">
                                    <span className="text-blue-400 text-sm font-medium">{item.step}</span>
                                    <span className="text-slate-300 text-xs">{item.desc}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}

            {showInfo && showInfo === "single_rag" && (
                <div className="bg-slate-800/70 border border-slate-600 rounded-xl p-5 mb-4">
                    <div className="flex items-start gap-4 mb-4">
                        <span className="text-3xl">{singleRagInfo.icon}</span>
                        <div className="flex-1">
                            <h3 className="text-lg font-semibold text-white mb-2">{singleRagInfo.title}</h3>
                            <p className="text-slate-300 text-sm">{singleRagInfo.description}</p>
                        </div>
                        <button
                            onClick={() => setShowInfo(null)}
                            className="text-slate-500 hover:text-white transition-colors"
                        >
                            ✕
                        </button>
                    </div>
                    <div className="border-t border-slate-600 pt-3 mb-3">
                        <p className="text-xs text-slate-400 mb-2">How it works:</p>
                        <div className="flex flex-wrap gap-3">
                            {singleRagInfo.howItWorks.map((item) => (
                                <div key={item.step} className="flex items-center gap-2">
                                    <span className="text-emerald-400 text-sm font-medium">{item.step}</span>
                                    <span className="text-slate-300 text-xs">{item.desc}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {singleRagInfo.benefits.map((benefit) => (
                            <span key={benefit} className="inline-flex items-center gap-1 bg-emerald-600/20 text-emerald-400 px-3 py-1 rounded-full text-xs">
                                ✓ {benefit}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {(mode === "auto" || mode === "single_rag") && !showInfo && (
                <div className="py-3 border-b border-slate-700">
                    <div className="flex items-center gap-3">
                        <label className="text-sm text-slate-400">Force Agent:</label>
                        <select
                            value={forceAgent}
                            onChange={(e) => setForceAgent(e.target.value)}
                            className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500"
                        >
                            <option value="">Auto (MasterAgent)</option>
                            <option value="suporte_api">API Support Agent</option>
                            <option value="database">Database Agent</option>
                            <option value="devops">DevOps Agent</option>
                        </select>
                    </div>
                </div>
            )}

            <div className="flex-1 overflow-y-auto py-4 space-y-4">
                {messages.length === 0 && (
                    <div className="text-center text-slate-500 py-12">
                        <div className="text-4xl mb-4">💬</div>
                        <p className="text-lg mb-2">Welcome to Support Copilot</p>
                        <p className="text-sm">
                            Select a mode and start asking questions
                        </p>
                    </div>
                )}

                {messages.map((msg) => {
                    const { agentName, content } = msg.role === "assistant" ? getDisplayContent(msg) : { agentName: "", content: msg.content };

                    return (
                        <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                            <div
                                className={`max-w-[90%] rounded-2xl px-5 py-4 ${
                                    msg.role === "user"
                                        ? "bg-blue-600 text-white"
                                        : "bg-slate-800 border border-slate-700"
                                }`}
                            >
                                {msg.role === "assistant" && (
                                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-slate-700">
                                        <span className={`inline-flex px-3 py-1 text-xs font-medium rounded-full ${agentColors[agentName] || defaultAgentColor}`}>
                                            {agentName}
                                        </span>
                                        {msg.confidence !== undefined && (
                                            <span className="text-xs text-slate-500">
                                                confidence: {(msg.confidence * 100).toFixed(0)}%
                                            </span>
                                        )}
                                    </div>
                                )}

                                <div className="text-slate-100 leading-relaxed">
                                    {msg.role === "user" ? (
                                        <p className="whitespace-pre-wrap">{content}</p>
                                    ) : (
                                        <div dangerouslySetInnerHTML={{ __html: renderContent(content) }} />
                                    )}
                                </div>

                                {msg.role === "assistant" && (
                                    <div className="mt-3 pt-3 border-t border-slate-700/50 space-y-2">
                                        {msg.sources && msg.sources.length > 0 && (
                                            <div className="text-xs">
                                                <span className="text-slate-400 font-medium">Sources: </span>
                                                <span className="text-slate-500">{msg.sources.join(", ")}</span>
                                            </div>
                                        )}

                                        <div className="flex items-center justify-between">
                                            <button
                                                onClick={() => setExpandedMeta(expandedMeta === msg.id ? null : msg.id)}
                                                className="text-xs text-blue-400 hover:text-blue-300 flex items-center gap-1"
                                            >
                                                {expandedMeta === msg.id ? "▼" : "▶"} Details
                                            </button>
                                            <span className="text-xs text-slate-500">
                                                {msg.timestamp.toLocaleTimeString("en-US")}
                                            </span>
                                        </div>

                                        {expandedMeta === msg.id && (
                                            <div className="bg-slate-900/50 rounded-lg p-3 mt-2 space-y-2 text-xs">
                                                {msg.tokens_used !== undefined && (
                                                    <div className="flex justify-between">
                                                        <span className="text-slate-400">Tokens used:</span>
                                                        <span className="text-white font-mono">{msg.tokens_used}</span>
                                                    </div>
                                                )}
                                                {msg.model_used && (
                                                    <div className="flex justify-between">
                                                        <span className="text-slate-400">Model:</span>
                                                        <span className="text-white font-mono">{msg.model_used}</span>
                                                    </div>
                                                )}
                                                {msg.total_time_ms !== undefined && (
                                                    <div className="flex justify-between">
                                                        <span className="text-slate-400">Response time:</span>
                                                        <span className="text-white font-mono">{formatTime(msg.total_time_ms)}</span>
                                                    </div>
                                                )}
                                                {msg.thinking && (
                                                    <div className="mt-2 pt-2 border-t border-slate-700">
                                                        <span className="text-slate-400 block mb-1">Thinking process:</span>
                                                        <span className="text-slate-300 font-mono text-xs whitespace-pre-wrap">{msg.thinking}</span>
                                                    </div>
                                                )}
                                                {msg.steps && msg.steps.length > 0 && (
                                                    <div className="flex justify-between mt-1">
                                                        <span className="text-slate-400">Pipeline steps:</span>
                                                        <span className="text-blue-300 font-mono">{msg.steps.join(" → ")}</span>
                                                    </div>
                                                )}
                                                {msg.collection_searched && (
                                                    <div className="flex justify-between mt-1">
                                                        <span className="text-slate-400">Collection searched:</span>
                                                        <span className="text-emerald-400 font-mono">{msg.collection_searched}</span>
                                                    </div>
                                                )}
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        </div>
                    );
                })}

                {loading && (
                    <div className="flex justify-start">
                        <div className="bg-slate-800 rounded-2xl px-5 py-4">
                            <div className="flex items-center gap-3 text-slate-400">
                                <div className="flex gap-1">
                                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                    <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                                </div>
                                <span className="text-sm">Thinking...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            <div className="py-4 border-t border-slate-700">
                <div className="flex items-center gap-3">
                    <textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyPress}
                        placeholder="Type your question..."
                        className="flex-1 bg-slate-800 border border-slate-700 rounded-2xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 resize-none"
                        rows={1}
                    />
                    <button
                        onClick={handleSend}
                        disabled={!input.trim() || loading}
                        className="px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-700 disabled:text-slate-500 text-white font-medium rounded-2xl transition-colors"
                    >
                        Send
                    </button>
                </div>
                <p className="text-xs text-slate-500 mt-2 text-center">
                    Press Enter to send, Shift+Enter for new line
                </p>
            </div>
        </div>
    );
}