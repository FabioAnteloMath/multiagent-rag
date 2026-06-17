"use client";

import { useState, useEffect } from "react";
import {
    getAgents, createAgent, updateAgent, deleteAgent,
    getCollections,
    PROVIDER_CATALOG, getProviderSpec,
    type Agent, type Collection,
} from "@/lib/api";

const agentAvatars: Record<string, { bg: string; text: string; icon: JSX.Element }> = {
    "API Support Agent": { bg: "bg-blue-100", text: "text-blue-600", icon: <ApiIcon /> },
    "Database Agent":    { bg: "bg-emerald-100", text: "text-emerald-600", icon: <DbIcon /> },
    "DevOps Agent":      { bg: "bg-purple-100", text: "text-purple-600", icon: <DevopsIcon /> },
    "Generalist Agent":  { bg: "bg-slate-100", text: "text-slate-600", icon: <ChatIcon /> },
    "RAG Agent":         { bg: "bg-violet-100", text: "text-violet-600", icon: <BrainIcon /> },
};

function ApiIcon() {
    return <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>;
}
function DbIcon() {
    return <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4" /></svg>;
}
function DevopsIcon() {
    return <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" /></svg>;
}
function ChatIcon() {
    return <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" /></svg>;
}

// ---------------------------------------------------------------------------
// Provider brand logos - hand-crafted inline SVGs (no external CDN)
// ---------------------------------------------------------------------------

function OllamaLogo({ className = "w-4 h-4" }: { className?: string }) {
    // Stylized llama head silhouette
    return (
        <svg className={className} viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2c-3.5 0-6 2.5-6 6 0 1.5.5 2.8 1.3 3.9C5.5 13 4 14.5 4 16.5c0 1.8 1 3.3 2.5 4.2-.3.5-.5 1.1-.5 1.7 0 1.7 1.3 3 3 3 .8 0 1.5-.3 2-.8.5.5 1.2.8 2 .8 1.7 0 3-1.3 3-3 0-.6-.2-1.2-.5-1.7 1.5-.9 2.5-2.4 2.5-4.2 0-2-1.5-3.5-3.3-4.6.8-1.1 1.3-2.4 1.3-3.9 0-3.5-2.5-6-6-6zm-2 7c-.6 0-1-.4-1-1s.4-1 1-1 1 .4 1 1-.4 1-1 1zm4 0c-.6 0-1-.4-1-1s.4-1 1-1 1 .4 1 1-.4 1-1 1z"/>
        </svg>
    );
}

function MiniMaxLogo({ className = "w-4 h-4" }: { className?: string }) {
    // Stylized "M" mark
    return (
        <svg className={className} viewBox="0 0 24 24" fill="currentColor">
            <path d="M3 4l4.5 14h2L12 9l2.5 9h2L21 4h-2.5l-3 11.5L13 4h-2l-2.5 11.5L5.5 4z"/>
        </svg>
    );
}

function GroqLogo({ className = "w-4 h-4" }: { className?: string }) {
    // Stylized "groq" wordmark with circuit accent
    return (
        <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M4 7c2-1 4-1 6 0M4 17c2 1 4 1 6 0" />
            <circle cx="14" cy="12" r="3" fill="currentColor" stroke="none" />
            <path d="M17 9l3-3M17 15l3 3" />
        </svg>
    );
}

function GeminiLogo({ className = "w-4 h-4" }: { className?: string }) {
    // 4-pointed star (Google Gemini mark)
    return (
        <svg className={className} viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2L14 10L22 12L14 14L12 22L10 14L2 12L10 10z" />
        </svg>
    );
}

const PROVIDER_LOGOS: Record<string, { logo: (props: { className?: string }) => JSX.Element; bg: string; text: string; label: string }> = {
    ollama:  { logo: OllamaLogo,  bg: "bg-slate-100",  text: "text-slate-700",  label: "Ollama" },
    minimax:  { logo: MiniMaxLogo,  bg: "bg-violet-100", text: "text-violet-700", label: "MiniMax" },
    groq:     { logo: GroqLogo,     bg: "bg-orange-100", text: "text-orange-700", label: "Groq" },
    gemini:   { logo: GeminiLogo,   bg: "bg-emerald-100",text: "text-emerald-700",label: "Gemini" },
};

function ProviderBadge({ provider, modelName, size = "sm" }: { provider: string; modelName?: string; size?: "sm" | "md" }) {
    const spec = PROVIDER_LOGOS[provider];
    if (!spec) {
        return <span className="text-xs text-slate-500 font-mono">{provider}{modelName ? ` / ${modelName}` : ""}</span>;
    }
    const Logo = spec.logo;
    const dim = size === "md" ? "w-5 h-5" : "w-4 h-4";
    const containerSize = size === "md" ? "w-7 h-7" : "w-6 h-6";
    return (
        <span className="inline-flex items-center gap-1.5" title={spec.label}>
            <span className={`${containerSize} rounded ${spec.bg} ${spec.text} flex items-center justify-center`}>
                <Logo className={dim} />
            </span>
            {modelName && <span className="text-xs text-slate-400 font-mono">{modelName}</span>}
        </span>
    );
}
function BrainIcon() {
    return <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" /></svg>;
}

const defaultAvatar = { bg: "bg-slate-100", text: "text-slate-600", icon: (
    <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
)};

interface EditForm {
    name: string;
    specialty: string;
    provider: string;
    model_name: string;
    temperature: number;
    collection_id: string;
    is_active: boolean;
    is_fallback: boolean;
    system_prompt: string;
    guidelines: string;
    personality: string;
    response_format: string;
    examples: string;
}

const EMPTY_FORM: EditForm = {
    name: "",
    specialty: "",
    provider: "ollama",
    model_name: "llama3.2:3b",
    temperature: 0.3,
    collection_id: "",
    is_active: true,
    is_fallback: false,
    system_prompt: "",
    guidelines: "",
    personality: "",
    response_format: "",
    examples: "",
};

export default function AgentsPage() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [collections, setCollections] = useState<Collection[]>([]);
    const [loading, setLoading] = useState(true);
    const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
    const [isCreating, setIsCreating] = useState(false);
    const [editForm, setEditForm] = useState<EditForm>(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [filterProvider, setFilterProvider] = useState<string>("all");

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            const [agentData, collData] = await Promise.all([getAgents(), getCollections()]);
            setAgents(agentData);
            setCollections(collData);
        } catch (err) {
            console.error("Failed to load:", err);
            setError(err instanceof Error ? err.message : "Failed to load data");
        } finally {
            setLoading(false);
        }
    }

    async function handleDelete(id: string, name: string) {
        if (!confirm(`Delete agent "${name}"? This cannot be undone.`)) return;
        try {
            await deleteAgent(id);
            await loadData();
        } catch (err) {
            console.error("Failed to delete:", err);
            setError(err instanceof Error ? err.message : "Failed to delete agent");
        }
    }

    function openEditModal(agent: Agent) {
        setEditingAgent(agent);
        setIsCreating(false);
        setError(null);
        setEditForm({
            name: agent.name || "",
            specialty: agent.specialty || "",
            provider: agent.provider || "ollama",
            model_name: agent.model_name || "llama3.2:3b",
            temperature: agent.temperature ?? 0.3,
            collection_id: agent.collection_id || "",
            is_active: agent.is_active,
            is_fallback: !!agent.is_fallback,
            system_prompt: agent.system_prompt || "",
            guidelines: agent.guidelines || "",
            personality: agent.personality || "",
            response_format: agent.response_format || "",
            examples: agent.examples || "",
        });
    }

    function openCreateModal() {
        setEditingAgent(null);
        setIsCreating(true);
        setError(null);
        setEditForm({ ...EMPTY_FORM, collection_id: collections[0]?.id || "" });
    }

    function closeModal() {
        setEditingAgent(null);
        setIsCreating(false);
        setEditForm(EMPTY_FORM);
        setError(null);
    }

    async function handleSave() {
        if (!isCreating && !editingAgent) return;
        setSaving(true);
        setError(null);
        try {
            const payload = {
                name: editForm.name.trim() || "Unnamed Agent",
                specialty: editForm.specialty.trim(),
                provider: editForm.provider,
                model_name: editForm.model_name.trim() || getProviderSpec(editForm.provider)?.models[0] || "",
                temperature: editForm.temperature,
                collection_id: editForm.collection_id || null,
                is_active: editForm.is_active,
                is_fallback: editForm.is_fallback,
                system_prompt: editForm.system_prompt,
                guidelines: editForm.guidelines,
                personality: editForm.personality,
                response_format: editForm.response_format,
                examples: editForm.examples,
            };
            if (isCreating) {
                await createAgent(payload);
            } else if (editingAgent) {
                await updateAgent(editingAgent.id, payload);
            }
            await loadData();
            closeModal();
        } catch (err) {
            console.error("Failed to save:", err);
            setError(err instanceof Error ? err.message : "Failed to save agent");
        } finally {
            setSaving(false);
        }
    }

    async function toggleActive(agent: Agent) {
        try {
            await updateAgent(agent.id, { is_active: !agent.is_active });
            await loadData();
        } catch (err) {
            console.error("Failed to toggle:", err);
        }
    }

    function getAvatar(agentName: string) {
        return agentAvatars[agentName] || defaultAvatar;
    }

    const visibleAgents = filterProvider === "all"
        ? agents
        : agents.filter((a) => a.provider === filterProvider);

    return (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Agents</h1>
                    <p className="text-slate-500 mt-1">
                        {agents.length} agent{agents.length === 1 ? "" : "s"} configured &middot; each tied to one collection
                    </p>
                </div>
                <button
                    onClick={openCreateModal}
                    className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors font-medium text-sm"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                    </svg>
                    New Agent
                </button>
            </div>

            {/* Filter bar */}
            <div className="mb-6 flex items-center gap-2 flex-wrap">
                <span className="text-sm text-slate-500">Filter by provider:</span>
                <button
                    onClick={() => setFilterProvider("all")}
                    className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${filterProvider === "all" ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                >
                    All ({agents.length})
                </button>
                {PROVIDER_CATALOG.map((p) => {
                    const count = agents.filter((a) => a.provider === p.id).length;
                    if (count === 0) return null;
                    return (
                        <button
                            key={p.id}
                            onClick={() => setFilterProvider(p.id)}
                            className={`text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${filterProvider === p.id ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
                        >
                            {p.name.split(" ")[0]} ({count})
                        </button>
                    );
                })}
            </div>

            {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                    {error}
                </div>
            )}

            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : visibleAgents.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
                    {filterProvider === "all"
                        ? "No agents found. Click \"New Agent\" to create one."
                        : `No agents using ${filterProvider}.`}
                </div>
            ) : (
                <div className="space-y-6">
                    {visibleAgents.map((agent) => {
                        const avatar = getAvatar(agent.name);
                        const providerSpec = getProviderSpec(agent.provider);
                        return (
                            <div
                                key={agent.id}
                                className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow"
                            >
                                <div className="p-6">
                                    <div className="flex items-start justify-between mb-6">
                                        <div className="flex items-center gap-4">
                                            <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${avatar.bg} ${avatar.text}`}>
                                                {avatar.icon}
                                            </div>
                                            <div>
                                                <h3 className="text-xl font-semibold text-slate-900">{agent.name}</h3>
                                                <div className="flex items-center gap-3 mt-2 flex-wrap">
                                                    <button
                                                        onClick={() => toggleActive(agent)}
                                                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-full transition-colors ${agent.is_active ? "bg-emerald-50 text-emerald-600 hover:bg-emerald-100" : "bg-slate-100 text-slate-500 hover:bg-slate-200"}`}
                                                        title="Click to toggle active/inactive"
                                                    >
                                                        <span className={`w-1.5 h-1.5 rounded-full ${agent.is_active ? "bg-emerald-500" : "bg-slate-400"}`} />
                                                        {agent.is_active ? "Active" : "Inactive"}
                                                    </button>
                                                    <ProviderBadge provider={agent.provider} modelName={agent.model_name} size="sm" />
                                                    {providerSpec?.free && (
                                                        <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded bg-emerald-50 text-emerald-600">Free</span>
                                                    )}
                                                </div>
                                            </div>
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => openEditModal(agent)}
                                                className="text-sm bg-blue-50 text-blue-600 hover:bg-blue-100 font-medium py-2 px-4 rounded-lg transition-colors"
                                            >
                                                Edit Prompts
                                            </button>
                                            <button
                                                onClick={() => handleDelete(agent.id, agent.name)}
                                                className="text-sm text-red-500 hover:text-red-600 font-medium px-3"
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </div>

                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                        <PromptField
                                            label="System Prompt" color="blue"
                                            value={agent.system_prompt}
                                            placeholder="Not configured"
                                        />
                                        <PromptField
                                            label="Guidelines" color="purple"
                                            value={agent.guidelines}
                                            placeholder="Not configured"
                                        />
                                        <PromptField
                                            label="Personality" color="emerald"
                                            value={agent.personality}
                                            placeholder="Not configured"
                                            rows={2}
                                        />
                                        <PromptField
                                            label="Response Format" color="amber"
                                            value={agent.response_format}
                                            placeholder="Not configured"
                                            mono
                                            rows={2}
                                        />
                                    </div>

                                    {agent.examples && (
                                        <div className="mt-4 bg-gradient-to-r from-slate-50 to-blue-50 rounded-lg p-4 border border-slate-100">
                                            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                                                <span className="w-4 h-4 rounded bg-blue-400 text-white flex items-center justify-center text-[10px]">E</span>
                                                Examples (Few-Shot)
                                            </h4>
                                            <p className="text-xs text-slate-600 line-clamp-2 font-mono whitespace-pre-wrap">
                                                {agent.examples}
                                            </p>
                                        </div>
                                    )}

                                    <div className="mt-4 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400 flex-wrap gap-2">
                                        <span>Specialty: <span className="text-slate-600 font-mono">{agent.specialty || "general"}</span></span>
                                        <span>Collection: <span className="text-slate-600 font-mono">{agent.collection_name || "— none —"}</span></span>
                                        <span>Temp: <span className="text-slate-600 font-mono">{agent.temperature}</span></span>
                                        {agent.is_fallback && (
                                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 text-xs font-medium">
                                                Fallback
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {(editingAgent || isCreating) && (
                <AgentEditModal
                    form={editForm}
                    setForm={setEditForm}
                    collections={collections}
                    agents={agents}
                    editingAgent={editingAgent}
                    isCreating={isCreating}
                    saving={saving}
                    error={error}
                    onClose={closeModal}
                    onSave={handleSave}
                />
            )}
        </div>
    );
}

function PromptField({ label, color, value, placeholder, mono, rows = 3 }: {
    label: string;
    color: "blue" | "purple" | "emerald" | "amber";
    value: string;
    placeholder: string;
    mono?: boolean;
    rows?: number;
}) {
    const colorClass = { blue: "bg-blue-500", purple: "bg-purple-500", emerald: "bg-emerald-500", amber: "bg-amber-500" }[color];
    return (
        <div className="bg-slate-50 rounded-lg p-4">
            <h4 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-2">
                <span className={`w-4 h-4 rounded ${colorClass} text-white flex items-center justify-center text-[10px]`}>{label[0]}</span>
                {label}
            </h4>
            <p className={`text-sm text-slate-700 leading-relaxed line-clamp-${rows} ${mono ? "font-mono whitespace-pre-wrap" : ""}`}>
                {value || <span className="text-slate-400 italic">{placeholder}</span>}
            </p>
        </div>
    );
}

function AgentEditModal({ form, setForm, collections, agents, editingAgent, isCreating, saving, error, onClose, onSave }: {
    form: EditForm;
    setForm: (f: EditForm) => void;
    collections: Collection[];
    agents: Agent[];
    editingAgent: Agent | null;
    isCreating: boolean;
    saving: boolean;
    error: string | null;
    onClose: () => void;
    onSave: () => void;
}) {
    const providerSpec = getProviderSpec(form.provider);
    const modelList = providerSpec?.models || [];
    // If the current model_name isn't in the list, keep it (user might have a custom Ollama model)
    const showCustomModel = form.model_name && !modelList.includes(form.model_name);

    return (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col">
                <div className="p-6 border-b border-slate-200 flex items-center justify-between">
                    <div>
                        <h2 className="text-xl font-semibold text-slate-900">
                            {isCreating ? "Create New Agent" : "Edit Agent Prompts"}
                        </h2>
                        <p className="text-sm text-slate-500 mt-1">
                            {isCreating ? "Configure a new specialized agent" : editingAgent?.name}
                        </p>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-slate-600 p-2">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {error && (
                        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
                            {error}
                        </div>
                    )}

                    {/* Identity */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">Name *</label>
                            <input
                                type="text"
                                value={form.name}
                                onChange={(e) => setForm({ ...form, name: e.target.value })}
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="RAG Agent"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Specialty (category key)
                            </label>
                            <input
                                type="text"
                                value={form.specialty}
                                onChange={(e) => setForm({ ...form, specialty: e.target.value.toLowerCase().replace(/\s+/g, "_") })}
                                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="rag, suporte_api, database, devops..."
                            />
                            <p className="text-xs text-slate-500 mt-1">
                                Used by the classifier to route questions. Lowercase, no spaces.
                            </p>
                        </div>
                    </div>

                    {/* Model config */}
                    <div className="bg-gradient-to-r from-slate-50 to-blue-50 rounded-lg p-4 border border-slate-200">
                        <h3 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
                            <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                            Model &amp; Collection
                        </h3>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1.5">Provider</label>
                                <div className="flex items-center gap-2 mb-1.5">
                                    <ProviderBadge provider={form.provider} size="md" />
                                    <select
                                        value={form.provider}
                                        onChange={(e) => {
                                            const newProv = e.target.value;
                                            const spec = getProviderSpec(newProv);
                                            const newModel = spec?.models[0] || "";
                                            setForm({ ...form, provider: newProv, model_name: newModel });
                                        }}
                                        className="flex-1 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    >
                                        {PROVIDER_CATALOG.map((p) => (
                                            <option key={p.id} value={p.id}>
                                                {p.name}
                                            </option>
                                        ))}
                                    </select>
                                </div>
                                {providerSpec && (
                                    <p className="text-xs text-slate-500 mt-1">{providerSpec.notes}</p>
                                )}
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1.5">Model</label>
                                <input
                                    type="text"
                                    list={`models-${form.provider}`}
                                    value={form.model_name}
                                    onChange={(e) => setForm({ ...form, model_name: e.target.value })}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="llama3.2:3b"
                                />
                                <datalist id={`models-${form.provider}`}>
                                    {modelList.map((m) => (
                                        <option key={m} value={m} />
                                    ))}
                                </datalist>
                                {showCustomModel && (
                                    <p className="text-xs text-amber-600 mt-1">
                                        Custom model name (not in the default list). Make sure it&apos;s available.
                                    </p>
                                )}
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1.5">Collection</label>
                                <select
                                    value={form.collection_id}
                                    onChange={(e) => setForm({ ...form, collection_id: e.target.value })}
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                                >
                                    <option value="">— No collection —</option>
                                    {collections.map((c) => (
                                        <option key={c.id} value={c.id}>
                                            {c.name} {c.is_default ? "(default)" : ""} — {c.document_count} doc{c.document_count === 1 ? "" : "s"}
                                        </option>
                                    ))}
                                </select>
                                <p className="text-xs text-slate-500 mt-1">
                                    The agent will search this collection&apos;s FAISS index.
                                </p>
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-slate-600 mb-1.5">Temperature</label>
                                <div className="flex items-center gap-3">
                                    <input
                                        type="range"
                                        min="0"
                                        max="1"
                                        step="0.1"
                                        value={form.temperature}
                                        onChange={(e) => setForm({ ...form, temperature: parseFloat(e.target.value) })}
                                        className="flex-1 h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer"
                                    />
                                    <span className="text-sm font-mono text-slate-600 w-12 text-center">{form.temperature}</span>
                                </div>
                            </div>
                        </div>

                        <div className="mt-4 flex items-center gap-3">
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, is_active: !form.is_active })}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.is_active ? "bg-emerald-500" : "bg-slate-300"}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.is_active ? "translate-x-6" : "translate-x-1"}`} />
                            </button>
                            <span className="text-sm text-slate-700">
                                {form.is_active ? "Active" : "Inactive"} (inactive agents are skipped by the router)
                            </span>
                        </div>

                        <div className="mt-3 flex items-center gap-3">
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, is_fallback: !form.is_fallback })}
                                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${form.is_fallback ? "bg-amber-500" : "bg-slate-300"}`}
                            >
                                <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${form.is_fallback ? "translate-x-6" : "translate-x-1"}`} />
                            </button>
                            <div className="text-sm text-slate-700">
                                <div className="font-medium">Fallback agent</div>
                                <div className="text-xs text-slate-500">
                                    Só é chamado quando nenhum specialist tiver contexto relevante. Use para um agent "coringa" que cobre perguntas genéricas.
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* System prompt */}
                    <div>
                        <div className="flex items-center justify-between mb-2">
                            <label className="block text-sm font-medium text-slate-700">System Prompt</label>
                                <button
                                    type="button"
                                    onClick={() => setForm({ ...form, system_prompt: enhancePrompt(form.system_prompt) })}
                                    className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                                >
                                    ✨ Make concise
                                </button>
                        </div>
                        <p className="text-xs text-slate-500 mb-2">
                            Base instructions. The "Make concise" button appends a one-word directive that the model can&apos;t meta-think about. The provider also post-processes to strip chain-of-thought leakage.
                        </p>
                        <textarea
                            value={form.system_prompt}
                            onChange={(e) => setForm({ ...form, system_prompt: e.target.value })}
                            rows={4}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="You are an expert in..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Guidelines</label>
                        <p className="text-xs text-slate-500 mb-2">Operational directives the model should follow.</p>
                        <textarea
                            value={form.guidelines}
                            onChange={(e) => setForm({ ...form, guidelines: e.target.value })}
                            rows={4}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="1. Always cite source documents&#10;2. Prefer bullet lists for comparisons&#10;3. If unsure, say so"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Personality</label>
                        <p className="text-xs text-slate-500 mb-2">Tone and communication style.</p>
                        <textarea
                            value={form.personality}
                            onChange={(e) => setForm({ ...form, personality: e.target.value })}
                            rows={2}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Professional, concise, and educational."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Response Format</label>
                        <p className="text-xs text-slate-500 mb-2">Markdown template for responses.</p>
                        <textarea
                            value={form.response_format}
                            onChange={(e) => setForm({ ...form, response_format: e.target.value })}
                            rows={4}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="### Answer&#10;Start directly with the substantive content. Use bullet lists."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-700 mb-2">Examples (Few-Shot)</label>
                        <p className="text-xs text-slate-500 mb-2">Q&amp;A examples to guide style.</p>
                        <textarea
                            value={form.examples}
                            onChange={(e) => setForm({ ...form, examples: e.target.value })}
                            rows={3}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                            placeholder="Q: Example question&#10;A: Example answer"
                        />
                    </div>
                </div>

                <div className="p-6 border-t border-slate-200 flex justify-between items-center bg-slate-50">
                    <div className="text-xs text-slate-500">
                        {isCreating ? "New agent will use the active flag above" : "Changes save immediately on click"}
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={onSave}
                            disabled={saving || !form.name.trim()}
                            className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
                        >
                            {saving ? "Saving..." : isCreating ? "Create Agent" : "Save Changes"}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

function enhancePrompt(current: string): string {
    // We tried adding a "no preamble" rule but MiniMax-M2.7 has a strong
    // RLHF pattern that makes it META-ACKNOWLEDGE the rule (e.g. "I need to
    // follow the strict output format"), making the preamble WORSE.
    // Instead, we add a single-word directive at the END that the model can't
    // meta-think about. The post-processing in MiniMaxProvider strips any
    // remaining chain-of-thought leakage.
    const directive = "\n\nBe concise.";
    if (current.trim().endsWith("Be concise.")) {
        return current;
    }
    return (current.trim() + directive).trim();
}
