"use client";

import { useState, useEffect, use, useMemo } from "react";
import { useRouter } from "next/navigation";
import { getDocumentChunks, updateChunk, deleteChunk, rebuildDocumentIndex, createChunk, type Chunk } from "@/lib/api";

interface PageProps {
    params: Promise<{ id: string }>;
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100];

export default function DocumentChunksPage({ params }: PageProps) {
    const resolvedParams = use(params);
    const documentId = resolvedParams.id;
    const router = useRouter();

    const [allChunks, setAllChunks] = useState<Chunk[]>([]);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [reindexing, setReindexing] = useState(false);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editContent, setEditContent] = useState("");
    const [showAddForm, setShowAddForm] = useState(false);
    const [newChunkContent, setNewChunkContent] = useState("");
    const [documentName, setDocumentName] = useState("");
    const [search, setSearch] = useState("");

    // Pagination state
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(25);

    useEffect(() => {
        loadChunks();
    }, [documentId]);

    // Reset to page 1 when search changes
    useEffect(() => {
        setPage(1);
    }, [search, pageSize]);

    async function loadChunks() {
        try {
            const data = await getDocumentChunks(documentId);
            setAllChunks(data);
            if (data.length > 0) {
                setDocumentName(data[0].source || "Document");
            }
        } catch (error) {
            console.error("Failed to load chunks:", error);
        } finally {
            setLoading(false);
        }
    }

    // Filter chunks by search query
    const filteredChunks = useMemo(() => {
        if (!search.trim()) return allChunks;
        const q = search.toLowerCase();
        return allChunks.filter((c) => c.content.toLowerCase().includes(q));
    }, [allChunks, search]);

    // Pagination
    const totalChunks = filteredChunks.length;
    const totalPages = Math.max(1, Math.ceil(totalChunks / pageSize));
    const currentPage = Math.min(page, totalPages);
    const startIdx = (currentPage - 1) * pageSize;
    const endIdx = Math.min(startIdx + pageSize, totalChunks);
    const visibleChunks = filteredChunks.slice(startIdx, endIdx);

    async function handleSave(id: string) {
        setSaving(true);
        try {
            await updateChunk(documentId, id, editContent);
            await loadChunks();
            setEditingId(null);
        } catch (error) {
            console.error("Failed to save chunk:", error);
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Delete this chunk?")) return;
        try {
            await deleteChunk(documentId, id);
            await loadChunks();
        } catch (error) {
            console.error("Failed to delete chunk:", error);
        }
    }

    async function handleAddChunk() {
        if (!newChunkContent.trim()) return;
        setSaving(true);
        try {
            await createChunk(documentId, newChunkContent);
            setNewChunkContent("");
            setShowAddForm(false);
            await loadChunks();
        } catch (error) {
            console.error("Failed to add chunk:", error);
        } finally {
            setSaving(false);
        }
    }

    async function handleReindex() {
        setReindexing(true);
        try {
            await rebuildDocumentIndex(documentId);
            alert("Document re-indexed successfully!");
        } catch (error) {
            console.error("Failed to reindex:", error);
            alert("Failed to reindex document");
        } finally {
            setReindexing(false);
        }
    }

    function startEdit(chunk: Chunk) {
        setEditingId(chunk.id);
        setEditContent(chunk.content);
    }

    function cancelEdit() {
        setEditingId(null);
        setEditContent("");
    }

    // Build the list of page numbers to show (with ellipses)
    function getPageNumbers(): (number | "...")[] {
        const pages: (number | "...")[] = [];
        if (totalPages <= 7) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
            return pages;
        }
        pages.push(1);
        if (currentPage > 4) pages.push("...");
        const start = Math.max(2, currentPage - 1);
        const end = Math.min(totalPages - 1, currentPage + 1);
        for (let i = start; i <= end; i++) pages.push(i);
        if (currentPage < totalPages - 3) pages.push("...");
        pages.push(totalPages);
        return pages;
    }

    return (
        <div className="min-h-screen bg-slate-100">
            {/* Header */}
            <div className="bg-white shadow-sm border-b border-slate-200">
                <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => router.push("/documents")}
                                className="p-2 hover:bg-slate-100 rounded-lg transition-colors"
                            >
                                <svg className="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                                </svg>
                            </button>
                            <div>
                                <h1 className="text-xl font-semibold text-slate-900">Edit Chunks</h1>
                                <p className="text-sm text-slate-500">ID: {documentId}</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setShowAddForm(true)}
                                className="inline-flex items-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white px-4 py-2 rounded-lg transition-colors font-medium text-sm"
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                </svg>
                                Add Chunk
                            </button>
                            <button
                                onClick={handleReindex}
                                disabled={reindexing}
                                className="inline-flex items-center gap-2 bg-purple-500 hover:bg-purple-600 disabled:bg-purple-300 text-white px-4 py-2 rounded-lg transition-colors font-medium text-sm"
                            >
                                {reindexing ? "Reindexing..." : "Reindex"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {/* Content */}
            <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Add Chunk Form */}
                {showAddForm && (
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 mb-6">
                        <h3 className="text-lg font-medium text-slate-900 mb-4">Add New Chunk</h3>
                        <textarea
                            value={newChunkContent}
                            onChange={(e) => setNewChunkContent(e.target.value)}
                            placeholder="Enter chunk content..."
                            rows={6}
                            className="w-full p-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                        />
                        <div className="flex justify-end gap-3 mt-4">
                            <button
                                onClick={() => { setShowAddForm(false); setNewChunkContent(""); }}
                                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleAddChunk}
                                disabled={saving || !newChunkContent.trim()}
                                className="px-4 py-2 bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-300 text-white rounded-lg transition-colors"
                            >
                                {saving ? "Adding..." : "Add Chunk"}
                            </button>
                        </div>
                    </div>
                )}

                {/* Toolbar: search + page size */}
                {allChunks.length > 0 && (
                    <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-4 mb-4 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                        <div className="relative flex-1">
                            <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                            </svg>
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search chunk content..."
                                className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            />
                        </div>
                        <div className="flex items-center gap-2 text-sm text-slate-600">
                            <label htmlFor="page-size" className="whitespace-nowrap">Per page:</label>
                            <select
                                id="page-size"
                                value={pageSize}
                                onChange={(e) => setPageSize(Number(e.target.value))}
                                className="px-2 py-1.5 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            >
                                {PAGE_SIZE_OPTIONS.map((n) => (
                                    <option key={n} value={n}>{n}</option>
                                ))}
                            </select>
                        </div>
                    </div>
                )}

                {/* Chunks List */}
                {loading ? (
                    <div className="text-center py-12 text-slate-400">Loading chunks...</div>
                ) : allChunks.length === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                        <p className="text-slate-500">No chunks found for this document.</p>
                    </div>
                ) : totalChunks === 0 ? (
                    <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
                        <p className="text-slate-500">No chunks match &quot;{search}&quot;.</p>
                    </div>
                ) : (
                    <>
                        <div className="space-y-4">
                            {visibleChunks.map((chunk) => (
                                <div key={chunk.id} className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
                                    <div className="bg-slate-50 px-4 py-2 border-b border-slate-200 flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <span className="bg-blue-100 text-blue-700 text-xs font-medium px-2 py-1 rounded">
                                                Chunk {chunk.chunk_index}
                                            </span>
                                            <span className={`text-xs px-2 py-1 rounded ${
                                                chunk.embedding_status === "embedded"
                                                    ? "bg-emerald-100 text-emerald-700"
                                                    : chunk.embedding_status === "pending"
                                                    ? "bg-amber-100 text-amber-700"
                                                    : "bg-slate-100 text-slate-600"
                                            }`}>
                                                {chunk.embedding_status}
                                            </span>
                                            <span className="text-xs text-slate-400">
                                                {chunk.content.length} chars
                                            </span>
                                        </div>
                                        {editingId !== chunk.id && (
                                            <div className="flex items-center gap-2">
                                                <button
                                                    onClick={() => startEdit(chunk)}
                                                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(chunk.id)}
                                                    className="text-red-500 hover:text-red-600 text-sm font-medium"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                    <div className="p-4">
                                        {editingId === chunk.id ? (
                                            <div>
                                                <textarea
                                                    value={editContent}
                                                    onChange={(e) => setEditContent(e.target.value)}
                                                    rows={8}
                                                    className="w-full p-3 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                                                />
                                                <div className="flex justify-end gap-3 mt-4">
                                                    <button
                                                        onClick={cancelEdit}
                                                        className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors"
                                                    >
                                                        Cancel
                                                    </button>
                                                    <button
                                                        onClick={() => handleSave(chunk.id)}
                                                        disabled={saving}
                                                        className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg transition-colors"
                                                    >
                                                        {saving ? "Saving..." : "Save Changes"}
                                                    </button>
                                                </div>
                                            </div>
                                        ) : (
                                            <pre className="whitespace-pre-wrap text-sm text-slate-700 font-mono leading-relaxed">
                                                {chunk.content}
                                            </pre>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>

                        {/* Pagination footer */}
                        <div className="mt-6 bg-white rounded-xl shadow-sm border border-slate-200 px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3">
                            <p className="text-sm text-slate-600">
                                Showing <span className="font-medium">{startIdx + 1}</span>–
                                <span className="font-medium">{endIdx}</span> of{" "}
                                <span className="font-medium">{totalChunks}</span>
                                {search && <span className="text-slate-400"> (filtered from {allChunks.length})</span>}
                            </p>
                            <div className="flex items-center gap-1">
                                <button
                                    onClick={() => setPage(1)}
                                    disabled={currentPage === 1}
                                    className="px-2.5 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed rounded transition-colors"
                                    title="First page"
                                >
                                    «
                                </button>
                                <button
                                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                                    disabled={currentPage === 1}
                                    className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed rounded transition-colors"
                                >
                                    ‹ Prev
                                </button>
                                {getPageNumbers().map((p, i) =>
                                    p === "..." ? (
                                        <span key={`dots-${i}`} className="px-2 text-slate-400">…</span>
                                    ) : (
                                        <button
                                            key={p}
                                            onClick={() => setPage(p)}
                                            className={`min-w-[36px] px-2 py-1.5 text-sm rounded transition-colors ${
                                                p === currentPage
                                                    ? "bg-blue-500 text-white font-medium"
                                                    : "text-slate-600 hover:bg-slate-100"
                                            }`}
                                        >
                                            {p}
                                        </button>
                                    )
                                )}
                                <button
                                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                                    disabled={currentPage === totalPages}
                                    className="px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed rounded transition-colors"
                                >
                                    Next ›
                                </button>
                                <button
                                    onClick={() => setPage(totalPages)}
                                    disabled={currentPage === totalPages}
                                    className="px-2.5 py-1.5 text-sm text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed rounded transition-colors"
                                    title="Last page"
                                >
                                    »
                                </button>
                            </div>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
