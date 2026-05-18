"use client";

import { useState, useEffect } from "react";
import { getAgents, createAgent, deleteAgent, updateAgent, getCollections, type Agent, type Collection } from "@/lib/api";

const agentAvatars: Record<string, { emoji: string; color: string }> = {
    "API Support Agent": { emoji: "🔧", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
    "Database Agent": { emoji: "🗄️", color: "bg-green-500/20 text-green-400 border-green-500/30" },
    "DevOps Agent": { emoji: "🚀", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
    "Generalist Agent": { emoji: "🤖", color: "bg-slate-500/20 text-slate-400 border-slate-500/30" },
};

const defaultAvatar = { emoji: "👤", color: "bg-slate-500/20 text-slate-400 border-slate-500/30" };

const OLLAMA_MODELS = [
    { value: "llama3.2:3b", label: "llama3.2:3b (3B params - fast)" },
    { value: "llama3.2:7b", label: "llama3.2:7b (7B params - better quality)" },
    { value: "mistral:7b", label: "mistral:7b (7B params)" },
    { value: "codellama:7b", label: "codellama:7b (code focused)" },
    { value: "llama3.1:8b", label: "llama3.1:8b (8B params)" },
];

const MINIMAX_MODELS = [
    { value: "MiniMax-M2.7", label: "MiniMax-M2.7 (cloud - high quality)" },
    { value: "MiniMax-M2.5", label: "MiniMax-M2.5 (cloud - fast)" },
    { value: "MiniMax-M2.1", label: "MiniMax-M2.1 (cloud - efficient)" },
];

const PROVIDERS = [
    { value: "ollama", label: "Ollama (local - free)" },
    { value: "minimax", label: "MiniMax (cloud - paid)" },
];

export default function AgentsPage() {
    const [agents, setAgents] = useState<Agent[]>([]);
    const [collections, setCollections] = useState<Collection[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
    const [formData, setFormData] = useState({
        name: "",
        specialty: "",
        collection_id: "",
        provider: "ollama",
        model_name: "llama3.2:3b",
        temperature: 0.3,
        system_prompt: "",
    });

    useEffect(() => {
        loadData();
    }, []);

    async function loadData() {
        try {
            const [agentsData, collectionsData] = await Promise.all([getAgents(), getCollections()]);
            setAgents(agentsData);
            setCollections(collectionsData);
        } catch (error) {
            console.error("Failed to load:", error);
        } finally {
            setLoading(false);
        }
    }

    async function handleCreate(e: React.FormEvent) {
        e.preventDefault();
        if (!formData.name.trim()) return;
        try {
            await createAgent({
                name: formData.name,
                specialty: formData.specialty,
                collection_id: formData.collection_id || undefined,
                provider: formData.provider,
                model_name: formData.model_name,
                temperature: formData.temperature,
            });
            resetForm();
            await loadData();
        } catch (error) {
            console.error("Failed to create:", error);
            alert("Error creating agent");
        }
    }

    async function handleUpdate(e: React.FormEvent) {
        e.preventDefault();
        if (!editingAgent) return;
        try {
            await updateAgent(editingAgent.id, {
                name: formData.name,
                specialty: formData.specialty,
                collection_id: formData.collection_id || undefined,
                provider: formData.provider,
                model_name: formData.model_name,
                temperature: formData.temperature,
            });
            resetForm();
            await loadData();
        } catch (error) {
            console.error("Failed to update:", error);
            alert("Error updating agent");
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Are you sure?")) return;
        try {
            await deleteAgent(id);
            await loadData();
        } catch (error) {
            console.error("Failed to delete:", error);
        }
    }

    function openEditModal(agent: Agent) {
        setEditingAgent(agent);
        setFormData({
            name: agent.name,
            specialty: agent.specialty,
            collection_id: agent.collection_id || "",
            provider: agent.provider,
            model_name: agent.model_name,
            temperature: agent.temperature,
            system_prompt: agent.system_prompt,
        });
        setShowModal(true);
    }

    function resetForm() {
        setShowModal(false);
        setEditingAgent(null);
        setFormData({
            name: "",
            specialty: "",
            collection_id: "",
            provider: "ollama",
            model_name: "llama3.2:3b",
            temperature: 0.3,
            system_prompt: "",
        });
    }

    function getModelsForProvider(provider: string) {
        return provider === "minimax" ? MINIMAX_MODELS : OLLAMA_MODELS;
    }

    function getAvatar(agentName: string) {
        return agentAvatars[agentName] || defaultAvatar;
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white">Agents</h1>
                    <p className="text-slate-400 mt-1">Specialized agents for knowledge areas</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                    + New Agent
                </button>
            </div>

            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : agents.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                    No agents found. Create one to get started.
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {agents.map((agent) => {
                        const avatar = getAvatar(agent.name);
                        return (
                            <div
                                key={agent.id}
                                className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 hover:border-green-500/50 transition-all"
                            >
                                <div className="flex items-start justify-between mb-4">
                                    <div className="flex items-center gap-3">
                                        <div className={`w-12 h-12 rounded-full flex items-center justify-center text-2xl border ${avatar.color}`}>
                                            {avatar.emoji}
                                        </div>
                                        <div>
                                            <h3 className="text-lg font-semibold text-white">{agent.name}</h3>
                                            {agent.is_active ? (
                                                <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-green-500/20 text-green-400 rounded">
                                                    Active
                                                </span>
                                            ) : (
                                                <span className="inline-block mt-1 px-2 py-0.5 text-xs bg-slate-500/20 text-slate-400 rounded">
                                                    Inactive
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                    <button
                                        onClick={() => openEditModal(agent)}
                                        className="text-slate-500 hover:text-blue-400 transition-colors"
                                    >
                                        ✎
                                    </button>
                                </div>
                                <div className="space-y-2 text-sm">
                                    <div>
                                        <span className="text-slate-500">Specialty:</span>
                                        <span className="text-slate-300 ml-2">{agent.specialty || "N/A"}</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-500">Collection:</span>
                                        <span className="text-slate-300 ml-2">{agent.collection_name || "N/A"}</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-500">Provider:</span>
                                        <span className="text-slate-300 ml-2">{agent.provider}</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-500">Model:</span>
                                        <span className="text-slate-300 ml-2">{agent.model_name}</span>
                                    </div>
                                    <div>
                                        <span className="text-slate-500">Temperature:</span>
                                        <span className="text-slate-300 ml-2">{agent.temperature}</span>
                                    </div>
                                </div>
                                <button
                                    onClick={() => handleDelete(agent.id)}
                                    className="mt-4 text-sm text-red-400 hover:text-red-300 transition-colors"
                                >
                                    Delete agent
                                </button>
                            </div>
                        );
                    })}
                </div>
            )}

            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-md">
                        <h2 className="text-xl font-semibold text-white mb-4">
                            {editingAgent ? "Edit Agent" : "New Agent"}
                        </h2>
                        <form onSubmit={editingAgent ? handleUpdate : handleCreate}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Name
                                </label>
                                <input
                                    type="text"
                                    value={formData.name}
                                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                                    placeholder="Ex: API Support Agent"
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Specialty
                                </label>
                                <input
                                    type="text"
                                    value={formData.specialty}
                                    onChange={(e) => setFormData({ ...formData, specialty: e.target.value })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                                    placeholder="Ex: HTTP errors, debugging"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Collection
                                </label>
                                <select
                                    value={formData.collection_id}
                                    onChange={(e) => setFormData({ ...formData, collection_id: e.target.value })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                                >
                                    <option value="">None</option>
                                    {collections.map((col) => (
                                        <option key={col.id} value={col.id}>
                                            {col.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Provider
                                </label>
                                <select
                                    value={formData.provider}
                                    onChange={(e) => setFormData({ ...formData, provider: e.target.value, model_name: e.target.value === "minimax" ? "MiniMax-Text-01" : "llama3.2:3b" })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                                >
                                    {PROVIDERS.map((p) => (
                                        <option key={p.value} value={p.value}>
                                            {p.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Model
                                </label>
                                <select
                                    value={formData.model_name}
                                    onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                                >
                                    {getModelsForProvider(formData.provider).map((m) => (
                                        <option key={m.value} value={m.value}>
                                            {m.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    Temperature
                                </label>
                                <input
                                    type="number"
                                    step="0.1"
                                    min="0"
                                    max="2"
                                    value={formData.temperature}
                                    onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500"
                                />
                            </div>
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-slate-300 mb-2">
                                    System Prompt (optional)
                                </label>
                                <textarea
                                    value={formData.system_prompt}
                                    onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-green-500 h-20"
                                    placeholder="Custom instructions for the agent..."
                                />
                            </div>
                            <div className="flex items-center justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={resetForm}
                                    className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                                >
                                    {editingAgent ? "Update" : "Create"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}