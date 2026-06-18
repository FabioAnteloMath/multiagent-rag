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
    tokens_used?: number;
    thinking?: string;
    model_used?: string;
    total_time_ms?: number;
    confidence?: number;
    collection_searched?: string;
    routing?: import("@/lib/api").RoutingInfo | null;
}

const agentConfig: Record<string, { bg: string; border: string; text: string; dot: string; icon: JSX.Element }> = {
    // English names
    "API Support Agent": { 
        bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-600", dot: "bg-blue-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
    },
    "Database Agent": { 
        bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-600", dot: "bg-emerald-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>
    },
    "DevOps Agent": { 
        bg: "bg-purple-50", border: "border-purple-200", text: "text-purple-600", dot: "bg-purple-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
    },
    "Generalist Agent": { 
        bg: "bg-slate-100", border: "border-slate-200", text: "text-slate-600", dot: "bg-slate-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
    },
    "baseline": { 
        bg: "bg-slate-100", border: "border-slate-200", text: "text-slate-600", dot: "bg-slate-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
    },
    // Portuguese names
    "Agente Suporte API": { 
        bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-600", dot: "bg-blue-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
    },
    "Agente Database": { 
        bg: "bg-emerald-50", border: "border-emerald-200", text: "text-emerald-600", dot: "bg-emerald-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>
    },
    "Agente DevOps": { 
        bg: "bg-purple-50", border: "border-purple-200", text: "text-purple-600", dot: "bg-purple-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>
    },
    "Agente Generalista": { 
        bg: "bg-slate-100", border: "border-slate-200", text: "text-slate-600", dot: "bg-slate-500",
        icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>
    },
};

const defaultConfig = { bg: "bg-slate-100", border: "border-slate-200", text: "text-slate-600", dot: "bg-slate-500", icon: <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg> };

function formatTime(ms: number): string {
    if (ms < 1000) return `${Math.round(ms)}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
}

function RoutingBadge({ routing }: { routing: import("@/lib/api").RoutingInfo }) {
    const via = routing.via;
    const conf = typeof routing.llm_confidence === "number" ? routing.llm_confidence : null;

    const viaStyles: Record<string, { bg: string; text: string; label: string }> = {
        llm:                   { bg: "bg-blue-50",    text: "text-blue-700",    label: "via LLM" },
        keyword:               { bg: "bg-emerald-50", text: "text-emerald-700", label: "via keyword" },
        llm_override_keyword:  { bg: "bg-amber-50",   text: "text-amber-700",   label: "keyword override" },
        default:               { bg: "bg-slate-100",  text: "text-slate-600",   label: "default" },
        clarifying:            { bg: "bg-purple-50",  text: "text-purple-700",  label: "clarifying" },
    };
    const style = viaStyles[via] ?? { bg: "bg-slate-100", text: "text-slate-600", label: via };

    return (
        <span
            className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs ${style.bg} ${style.text}`}
            title={routing.reasoning || ""}
        >
            {style.label}
            {conf !== null && (
                <span className="opacity-70">
                    ({Math.round(conf * 100)}%)
                </span>
            )}
            {routing.keyword_matches && routing.keyword_matches.length > 0 && routing.keyword_matches[0] !== "general" && (
                <span className="opacity-70 hidden sm:inline">
                    · kw: {routing.keyword_matches.join(", ")}
                </span>
            )}
        </span>
    );
}

/**
 * RoutingTrace — visual timeline of how a question got routed.
 *
 * Renders a vertical step list showing each decision the router made:
 * classifier → keyword check → (optional) discovery → final agent.
 * Color-coded by what fired (LLM, keyword, override, fallback).
 */
function RoutingTrace({ routing, question }: { routing: import("@/lib/api").RoutingInfo; question?: string }) {
    const steps: Array<{
        label: string;
        detail: string;
        tone: "blue" | "emerald" | "amber" | "slate" | "purple";
        icon: string;
    }> = [];

    const llmCat = routing.llm_category ?? null;
    const llmConf = typeof routing.llm_confidence === "number" ? routing.llm_confidence : null;
    const kw = routing.keyword_matches ?? [];
    const chosen = routing.chosen ?? [];

    // Step 1 — classifier
    if (llmCat) {
        steps.push({
            label: `Classifier → ${llmCat}`,
            detail: llmConf !== null
                ? `LLM confidence ${Math.round(llmConf * 100)}%`
                : "LLM responded (confidence unknown)",
            tone: llmConf !== null && llmConf < 0.6 ? "amber" : "blue",
            icon: llmConf !== null && llmConf < 0.6 ? "⚠️" : "🧠",
        });
    } else {
        steps.push({
            label: "Classifier unavailable",
            detail: routing.llm_raw
                ? `raw: ${routing.llm_raw.slice(0, 60)}${routing.llm_raw.length > 60 ? "…" : ""}`
                : "no usable response from LLM",
            tone: "amber",
            icon: "⚠️",
        });
    }

    // Step 2 — keyword check (always runs)
    if (kw.length > 0 && kw[0] !== "general") {
        steps.push({
            label: `Keyword → ${kw.join(", ")}`,
            detail: "matched terms in the question text",
            tone: "emerald",
            icon: "🔑",
        });
    } else {
        steps.push({
            label: "Keyword → (no specific match)",
            detail: "no keyword hit; fallback to general",
            tone: "slate",
            icon: "·",
        });
    }

    // Step 3 — override / discovery / fallback narrative
    if (routing.via === "llm_override_keyword") {
        steps.push({
            label: "Override → keyword wins",
            detail: "LLM confidence was below threshold; keyword took over",
            tone: "amber",
            icon: "⚖️",
        });
    } else if (routing.discovered) {
        steps.push({
            label: `Discovery → ${chosen[0] ?? "?"}`,
            detail: "retrieval probe picked this specialist (best FAISS distance)",
            tone: "emerald",
            icon: "🔍",
        });
    } else if (routing.via === "default") {
        steps.push({
            label: "Default → general",
            detail: "no usable signal; falling back to last-resort agent",
            tone: "slate",
            icon: "↩️",
        });
    }

    // Step 4 — final choice
    if (chosen.length > 0) {
        steps.push({
            label: `Final → ${chosen.join(", ")}`,
            detail: routing.reasoning || "delegated to this agent",
            tone: "blue",
            icon: "✅",
        });
    } else {
        steps.push({
            label: "Final → no agent",
            detail: "system will ask the user to clarify",
            tone: "purple",
            icon: "❓",
        });
    }

    const toneColors: Record<string, string> = {
        blue: "border-blue-300 bg-blue-50/60",
        emerald: "border-emerald-300 bg-emerald-50/60",
        amber: "border-amber-300 bg-amber-50/60",
        slate: "border-slate-200 bg-slate-50",
        purple: "border-purple-300 bg-purple-50/60",
    };

    return (
        <div className="mt-3 border-t border-slate-100 pt-3">
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Routing trace
            </div>
            <ol className="space-y-1.5">
                {steps.map((s, i) => (
                    <li
                        key={i}
                        className={`flex items-start gap-2 px-2.5 py-1.5 rounded border-l-2 ${toneColors[s.tone] || toneColors.slate}`}
                    >
                        <span className="text-sm leading-none mt-0.5">{s.icon}</span>
                        <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-slate-800">{s.label}</div>
                            <div className="text-[11px] text-slate-500 leading-snug">{s.detail}</div>
                        </div>
                    </li>
                ))}
            </ol>
            {routing.reasoning && (
                <div className="mt-2 text-[11px] italic text-slate-500 px-1">
                    &ldquo;{routing.reasoning}&rdquo;
                </div>
            )}
        </div>
    );
}

function renderMarkdown(text: string): string {
    // Escape HTML first to prevent XSS via LLM/retrieved-doc content.
    // Order matters: & must be replaced first, otherwise we'd double-escape
    // the ampersands introduced by the < and > replacements below.
    let html = text
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');
    
    // Code blocks with syntax highlighting appearance
    html = html.replace(/```(\w*)\n([\s\S]*?)```/g, (match, lang, code) => {
        return `<div class="my-3 rounded-lg overflow-hidden border border-slate-200 bg-slate-900">
            <div class="bg-slate-800 px-3 py-1.5 flex items-center gap-2 border-b border-slate-700">
                <span class="text-xs text-slate-400 font-mono">${lang || 'code'}</span>
                <div class="flex gap-1.5 ml-auto">
                    <span class="w-2.5 h-2.5 rounded-full bg-red-500"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-yellow-500"></span>
                    <span class="w-2.5 h-2.5 rounded-full bg-green-500"></span>
                </div>
            </div>
            <pre class="p-4 text-sm text-slate-100 overflow-x-auto font-mono leading-relaxed"><code>${code.trim()}</code></pre>
        </div>`;
    });
    
    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code class="bg-slate-100 text-blue-600 px-1.5 py-0.5 rounded text-sm font-mono">$1</code>');
    
    // Headers - h1 (large, gradient)
    html = html.replace(/^### (.+)$/gm, '<h3 class="text-base font-semibold text-slate-800 mt-4 mb-2 flex items-center gap-2"><span class="w-1 h-1 bg-purple-500 rounded-full"></span>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2 class="text-lg font-semibold text-slate-900 mt-5 mb-3 flex items-center gap-2"><span class="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1 class="text-xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent mt-6 mb-3">$1</h1>');
    
    // Bold and italic
    html = html.replace(/\*\*\*(.*?)\*\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong class="font-semibold text-slate-800">$1</strong>');
    html = html.replace(/\*(.*?)\*/g, '<em class="text-slate-600">$1</em>');
    
    // Horizontal rule as separator
    html = html.replace(/^---$/gm, '<div class="my-4 border-t border-slate-200"></div>');
    html = html.replace(/^---$/gm, '<hr class="my-4 border-slate-200" />');
    
    // Tables with styling
    const tableRegex = /\|(.+)\|\n\|[-:\s|]+\|\n((?:\|.+\|\n?)+)/g;
    html = html.replace(tableRegex, (match, header, body) => {
        const headers = header.split('|').filter(h => h.trim()).map(h => `<th class="px-4 py-2 text-left text-sm font-semibold text-slate-700 bg-slate-50 border-b border-slate-200">${h.trim()}</th>`).join('');
        const rows = body.trim().split('\n').map(row => {
            const cells = row.split('|').filter(c => c !== undefined).map((c, i) => `<td class="px-4 py-2 text-sm text-slate-600 border-b border-slate-100 ${i === 0 ? '' : ''}">${c.trim()}</td>`).join('');
            return `<tr class="${row.index % 2 === 0 ? 'bg-white' : 'bg-slate-50'}">${cells}</tr>`;
        }).join('');
        return `<div class="my-4 rounded-lg overflow-hidden border border-slate-200"><table class="w-full text-sm"><thead>${headers}</thead><tbody>${rows}</tbody></table></div>`;
    });
    
    // Lists
    html = html.replace(/^- (.*$)/gim, '<li class="text-slate-700 ml-4 mb-1 flex items-start gap-3"><span class="text-blue-500 mt-0.5">▹</span>$1</li>');
    html = html.replace(/^(\d+)\. (.*$)/gim, '<li class="text-slate-700 ml-4 mb-1 flex items-start gap-3"><span class="text-blue-500 font-medium min-w-[1.5rem]">$1.</span>$2</li>');
    
    // Blockquotes with icon
    html = html.replace(/^> (.+)$/gm, '<blockquote class="my-3 pl-4 border-l-4 border-blue-400 bg-blue-50 py-2 rounded-r"><span class="text-blue-400 mr-2">💡</span><span class="text-slate-700">$1</span></blockquote>');
    
    // Process paragraphs
    html = html
        .split('\n\n')
        .map(p => p.trim())
        .filter(p => p)
        .map(p => {
            if (p.startsWith('<h') || p.startsWith('<li') || p.startsWith('<div') || p.startsWith('<table') || p.startsWith('<blockquote') || p.startsWith('<hr')) return p;
            if (p.startsWith('<ul>')) return p;
            if (p.startsWith('<ol>')) return p;
            if (p.startsWith('<pre>')) return p;
            return `<p class="text-slate-700 mb-3 leading-relaxed">${p.replace(/\n/g, '<br/>')}</p>`;
        })
        .join('');
    
    // Wrap loose list items in ul
    const lines = html.split('\n');
    const result: string[] = [];
    let inList = false;
    let listContent = '';
    
    for (const line of lines) {
        if (line.startsWith('<li')) {
            if (!inList) {
                if (listContent) result.push(listContent);
                listContent = '<ul class="my-3 space-y-1">';
                inList = true;
            }
            listContent += line;
        } else {
            if (inList) {
                listContent += '</ul>';
                result.push(listContent);
                listContent = '';
                inList = false;
            }
            result.push(line);
        }
    }
    if (inList && listContent) {
        listContent += '</ul>';
        result.push(listContent);
    }
    
    return result.join('\n');
}

export default function ChatPage() {
    const [messages, setMessages] = useState<Message[]>([]);
    const [input, setInput] = useState("");
    // Multi-Agent is the only mode exposed to the user. The mode is locked
    // here so any future addition has to be deliberate.
    const MODE: "auto" = "auto";
    const [forceAgent, setForceAgent] = useState<string>("");
    const [loading, setLoading] = useState(false);
    const [apiOnline, setApiOnline] = useState(false);
    const [showDetails, setShowDetails] = useState<string | null>(null);
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

    const MIN_QUESTION_LENGTH = 3;
    const trimmedInput = input.trim();
    const inputTooShort = trimmedInput.length > 0 && trimmedInput.length < MIN_QUESTION_LENGTH;
    const canSend = trimmedInput.length >= MIN_QUESTION_LENGTH && !loading;

    async function handleSend() {
        if (!canSend) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: "user",
            content: trimmedInput,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput("");
        setLoading(true);

        try {
            const response: AskResponse = await askQuestion(
                trimmedInput,
                4,
                MODE,
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
                tokens_used: response.tokens_used,
                thinking: response.thinking,
                model_used: response.model_used,
                total_time_ms: response.total_time_ms,
                confidence: response.confidence,
                collection_searched: response.collection_searched,
                routing: response.routing,
            };
            setMessages((prev) => [...prev, assistantMessage]);
        } catch (error) {
            console.error("Failed to ask:", error);
            const errorMessage: Message = {
                id: (Date.now() + 1).toString(),
                role: "assistant",
                content: (error as Error).message || "Erro desconhecido. Verifique se o backend esta rodando.",
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

    function getAgentStyle(agentName: string) {
        return agentConfig[agentName] || defaultConfig;
    }

    return (
        <div className="flex flex-col h-[calc(100vh-64px)]">
            <div className="bg-white border-b border-slate-200 px-4 py-3">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <span className={`flex items-center gap-2 text-sm ${apiOnline ? "text-emerald-600" : "text-red-500"}`}>
                            <span className={`w-2 h-2 rounded-full ${apiOnline ? "bg-emerald-500" : "bg-red-500"}`} />
                            {apiOnline ? "Connected" : "Disconnected"}
                        </span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="hidden sm:inline-flex items-center gap-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 px-2.5 py-1 rounded-full">
                            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                            Multi-Agent
                        </span>
                        <select
                            value={forceAgent}
                            onChange={(e) => setForceAgent(e.target.value)}
                            className="bg-slate-100 border-0 rounded-lg px-3 py-1.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                            title="Force a specific specialist instead of letting the router decide"
                        >
                            <option value="">Auto Route</option>
                            <option value="suporte_api">Force: API Support</option>
                            <option value="database">Force: Database</option>
                            <option value="devops">Force: DevOps</option>
                            <option value="rag">Force: RAG</option>
                            <option value="general">Force: Generalist (fallback)</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="flex-1 overflow-y-auto">
                <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
                    {messages.length === 0 && (
                        <div className="text-center py-16">
                            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-2xl flex items-center justify-center mx-auto mb-4">
                                <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                                </svg>
                            </div>
                            <h2 className="text-xl font-semibold text-slate-900 mb-2">Start a conversation</h2>
                            <p className="text-slate-500">Ask questions about your technical documentation</p>
                        </div>
                    )}

                    {messages.map((msg) => {
                        const isUser = msg.role === "user";
                        const agentName = msg.agent_used?.[0] || "Assistant";
                        const agentStyle = getAgentStyle(agentName);

                        return (
                            <div key={msg.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                                <div
                                    className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                                        isUser
                                            ? "bg-blue-500 text-white"
                                            : "bg-white border border-slate-200 shadow-sm"
                                    }`}
                                >
                                    {!isUser && msg.agent_used && (
                                        <div className="flex flex-wrap items-center gap-2 mb-3 pb-2 border-b border-slate-100">
                                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${agentStyle.bg} ${agentStyle.border} ${agentStyle.text}`}>
                                                <span className={`w-1.5 h-1.5 rounded-full ${agentStyle.dot}`} />
                                                {agentName}
                                            </span>
                                            {msg.routing && (
                                                <RoutingBadge routing={msg.routing} />
                                            )}
                                            {msg.confidence !== undefined && (
                                                <span className="text-xs text-slate-400">
                                                    {Math.round(msg.confidence * 100)}% confidence
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    <div className={isUser ? "text-white" : "text-slate-700"}>
                                        {isUser ? (
                                            <p className="whitespace-pre-wrap">{msg.content}</p>
                                        ) : (
                                            <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                                        )}
                                    </div>

                                    {!isUser && (
                                        <div className="mt-3 pt-3 border-t border-slate-100">
                                            <div className="flex items-center justify-between">
                                                <button
                                                    onClick={() => setShowDetails(showDetails === msg.id ? null : msg.id)}
                                                    className="text-xs text-slate-400 hover:text-slate-600 flex items-center gap-1"
                                                >
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                    {showDetails === msg.id ? "Hide" : "Show"} details
                                                </button>
                                                <span className="text-xs text-slate-400">
                                                    {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                                </span>
                                            </div>

                            {showDetails === msg.id && (
                                <div className="mt-3 pt-3 border-t border-slate-100 space-y-1.5 text-xs">
                                    {msg.sources && msg.sources.length > 0 && (
                                        <div className="flex flex-wrap gap-1">
                                            <span className="text-slate-500">Sources:</span>
                                            {msg.sources.map((s, i) => (
                                                <span key={i} className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded">
                                                    {s.split('/').pop()}
                                                </span>
                                            ))}
                                        </div>
                                    )}
                                    {msg.tokens_used !== undefined && (
                                        <div className="flex justify-between">
                                            <span className="text-slate-500">Tokens:</span>
                                            <span className="text-slate-700 font-mono">{msg.tokens_used}</span>
                                        </div>
                                    )}
                                    {msg.model_used && (
                                        <div className="flex justify-between">
                                            <span className="text-slate-500">Model:</span>
                                            <span className="text-slate-700 font-mono">{msg.model_used}</span>
                                        </div>
                                    )}
                                    {msg.total_time_ms !== undefined && (
                                        <div className="flex justify-between">
                                            <span className="text-slate-500">Response time:</span>
                                            <span className="text-slate-700 font-mono">{formatTime(msg.total_time_ms)}</span>
                                        </div>
                                    )}
                                    {msg.routing && (
                                        <RoutingTrace routing={msg.routing} question={msg.content} />
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
                            <div className="bg-white border border-slate-200 rounded-2xl px-5 py-4 shadow-sm">
                                <div className="flex items-center gap-3 text-slate-500">
                                    <div className="flex gap-1">
                                        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                                        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                                        <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                                    </div>
                                    <span className="text-sm">Thinking...</span>
                                </div>
                            </div>
                        </div>
                    )}

                    <div ref={messagesEndRef} />
                </div>
            </div>

            <div className="bg-white border-t border-slate-200 px-4 py-4">
                <div className="max-w-4xl mx-auto">
                    <div className="flex items-center gap-3 bg-slate-100 rounded-2xl px-4 py-2">
                        <textarea
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={handleKeyPress}
                            placeholder="Type your question..."
                            className="flex-1 bg-transparent text-slate-900 placeholder-slate-400 focus:outline-none resize-none py-1"
                            rows={1}
                        />
                        <button
                            onClick={handleSend}
                            disabled={!canSend}
                            className="p-2 bg-blue-500 hover:bg-blue-600 disabled:bg-slate-300 text-white rounded-xl transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                        </button>
                    </div>
                    <p className="text-xs text-slate-400 mt-2 text-center">
                        {inputTooShort
                            ? `Faltam ${MIN_QUESTION_LENGTH - trimmedInput.length} caractere${MIN_QUESTION_LENGTH - trimmedInput.length > 1 ? "s" : ""} (minimo ${MIN_QUESTION_LENGTH})`
                            : "Press Enter to send, Shift+Enter for new line"}
                    </p>
                </div>
            </div>
        </div>
    );
}