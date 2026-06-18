"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
    getDocuments, uploadDocument, deleteDocument, processDocument,
    updateDocument, getCollections, rebuildDocumentIndex, rebuildAllIndexes,
    type Document, type Collection,
} from "@/lib/api";

const statusColors: Record<string, { bg: string; text: string }> = {
    pending: { bg: "bg-amber-50", text: "text-amber-600" },
    processing: { bg: "bg-blue-50", text: "text-blue-600" },
    indexed: { bg: "bg-emerald-50", text: "text-emerald-600" },
    error: { bg: "bg-red-50", text: "text-red-600" },
};

const STATUS_FILTERS = [
    { value: "all", label: "All statuses" },
    { value: "indexed", label: "Indexed" },
    { value: "processing", label: "Processing" },
    { value: "pending", label: "Pending" },
    { value: "error", label: "Error" },
];

export default function DocumentsPage() {
    const router = useRouter();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [collections, setCollections] = useState<Collection[]>([]);
    const [loading, setLoading] = useState(true);

    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);

    // Upload-with-collection state
    const [uploadCollectionId, setUploadCollectionId] = useState<string>("");

    // Filters
    const [filterCollection, setFilterCollection] = useState<string>("all");
    const [filterStatus, setFilterStatus] = useState<string>("all");
    const [searchQuery, setSearchQuery] = useState("");

    // Toast
    const [toast, setToast] = useState<{ type: "ok" | "err"; msg: string } | null>(null);
    const showToast = (type: "ok" | "err", msg: string) => {
        setToast({ type, msg });
        window.setTimeout(() => setToast(null), 3500);
    };

    const loadDocuments = useCallback(async () => {
        try {
            const docs = await getDocuments();
            setDocuments(docs);
        } catch (error) {
            showToast("err", "Falha ao carregar documentos");
            console.error("Failed to load documents:", error);
        } finally {
            setLoading(false);
        }
    }, []);

    const loadCollections = useCallback(async () => {
        try {
            setCollections(await getCollections());
        } catch (error) {
            console.error("Failed to load collections:", error);
        }
    }, []);

    useEffect(() => {
        loadDocuments();
        loadCollections();
    }, [loadDocuments, loadCollections]);

    const collectionNameById = useMemo(() => {
        const m = new Map<string, string>();
        for (const c of collections) m.set(c.id, c.name);
        return m;
    }, [collections]);

    const filteredDocs = useMemo(() => {
        const q = searchQuery.trim().toLowerCase();
        return documents.filter((d) => {
            if (filterCollection === "unassigned" && d.collection_id) return false;
            if (filterCollection !== "all" && filterCollection !== "unassigned" && d.collection_id !== filterCollection) return false;
            if (filterStatus !== "all" && d.status !== filterStatus) return false;
            if (q && !d.filename.toLowerCase().includes(q)) return false;
            return true;
        });
    }, [documents, filterCollection, filterStatus, searchQuery]);

    async function handleUpload(file: File) {
        setUploading(true);
        try {
            const result = await uploadDocument(file, uploadCollectionId || null);
            showToast(
                result.status === "error" ? "err" : "ok",
                result.message || `Upload concluído: ${result.filename}`
            );
            await Promise.all([loadDocuments(), loadCollections()]);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Falha no upload");
        } finally {
            setUploading(false);
        }
    }

    function handleDrop(e: React.DragEvent) {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files[0];
        if (file) handleUpload(file);
    }

    function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
        const file = e.target.files?.[0];
        if (file) handleUpload(file);
        // reset input so the same file can be re-selected
        e.target.value = "";
    }

    async function handleDelete(doc: Document) {
        if (!confirm(`Excluir "${doc.filename}"? Os chunks e o índice serão removidos.`)) return;
        try {
            await deleteDocument(doc.id);
            showToast("ok", "Documento excluído");
            await Promise.all([loadDocuments(), loadCollections()]);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao excluir");
        }
    }

    async function handleProcess(doc: Document) {
        try {
            await processDocument(doc.id);
            showToast("ok", `Processamento iniciado para "${doc.filename}"`);
            await loadDocuments();
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro no processamento");
        }
    }

    async function handleReindex(doc: Document) {
        try {
            await rebuildDocumentIndex(doc.id);
            showToast("ok", `Reindexação de "${doc.filename}" concluída`);
            await loadDocuments();
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao reindexar");
        }
    }

    async function handleChangeCollection(doc: Document, newCollectionId: string) {
        const target = newCollectionId === "" ? null : newCollectionId;
        const previous = doc.collection_id;
        // optimistic-ish: revert on failure
        try {
            await updateDocument(doc.id, target);
            showToast("ok", target ? `Documento movido para "${collectionNameById.get(target) ?? target}"` : "Documento desvinculado");
            await Promise.all([loadDocuments(), loadCollections()]);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao mover");
            // refresh anyway to recover state
            await loadDocuments();
        }
    }

    async function handleRebuildAll() {
        if (!confirm("Reindexar TODAS as collections? Pode levar alguns minutos.")) return;
        try {
            await rebuildAllIndexes();
            showToast("ok", "Reindexação global concluída");
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao reindexar tudo");
        }
    }

    return (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
                    <p className="text-slate-500 mt-1">Manage your support documents</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleRebuildAll}
                        className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg transition-colors font-medium text-sm"
                    >
                        Rebuild all
                    </button>
                </div>
            </div>

            {/* Upload area */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 mb-6">
                <div className="flex flex-col sm:flex-row sm:items-end gap-4">
                    <div className="flex-1">
                        <label className="block text-sm font-medium text-slate-700 mb-1">
                            Collection destino
                        </label>
                        <select
                            value={uploadCollectionId}
                            onChange={(e) => setUploadCollectionId(e.target.value)}
                            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        >
                            <option value="">— Sem collection (vai pro índice geral) —</option>
                            {collections.map((c) => (
                                <option key={c.id} value={c.id}>
                                    {c.name}{c.is_default ? " (default)" : ""}
                                </option>
                            ))}
                        </select>
                        <p className="text-xs text-slate-400 mt-1">
                            O documento será processado em chunks automaticamente após o upload.
                        </p>
                    </div>
                    <label className="cursor-pointer">
                        <input
                            type="file"
                            accept=".pdf,.md,.txt"
                            className="hidden"
                            onChange={handleFileSelect}
                            disabled={uploading}
                        />
                        <span className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg transition-colors font-medium text-sm text-white ${
                            uploading ? "bg-slate-300 cursor-not-allowed" : "bg-blue-500 hover:bg-blue-600 cursor-pointer"
                        }`}>
                            {uploading ? "Enviando..." : "+ Upload"}
                        </span>
                    </label>
                </div>

                <div
                    className={`mt-4 border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
                        dragOver ? "border-blue-400 bg-blue-50" : "border-slate-200 hover:border-slate-300"
                    }`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={handleDrop}
                >
                    <p className="text-sm text-slate-500">
                        Ou arraste arquivos aqui. Formatos: <span className="font-medium">PDF, MD, TXT</span>.
                    </p>
                </div>
            </div>

            {/* Filters */}
            <div className="bg-white rounded-xl border border-slate-200 p-4 mb-4 flex flex-col sm:flex-row gap-3">
                <div className="relative flex-1">
                    <svg className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                    <input
                        type="text"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Buscar por nome do arquivo..."
                        className="w-full pl-10 pr-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                </div>
                <select
                    value={filterCollection}
                    onChange={(e) => setFilterCollection(e.target.value)}
                    className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    <option value="all">Todas as collections</option>
                    <option value="unassigned">Sem collection</option>
                    {collections.map((c) => (
                        <option key={c.id} value={c.id}>
                            {c.name}
                        </option>
                    ))}
                </select>
                <select
                    value={filterStatus}
                    onChange={(e) => setFilterStatus(e.target.value)}
                    className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                    {STATUS_FILTERS.map((s) => (
                        <option key={s.value} value={s.value}>{s.label}</option>
                    ))}
                </select>
            </div>

            {/* Toast */}
            {toast && (
                <div className={`mb-4 px-4 py-2 rounded-lg text-sm ${toast.type === "ok" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : "bg-red-50 text-red-700 border border-red-200"}`}>
                    {toast.msg}
                </div>
            )}

            {/* List */}
            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : filteredDocs.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
                    {documents.length === 0
                        ? "Nenhum documento ainda — faça upload acima."
                        : "Nenhum documento bate com os filtros atuais."}
                </div>
            ) : (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Collection</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Chunks</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Date</th>
                                <th className="text-right px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {filteredDocs.map((doc) => {
                                const colors = statusColors[doc.status] || statusColors.pending;
                                const colName = doc.collection_id ? collectionNameById.get(doc.collection_id) : null;
                                return (
                                    <tr key={doc.id} className="hover:bg-slate-50">
                                        <td className="px-6 py-4">
                                            <span className="text-slate-900 font-medium">{doc.filename}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <select
                                                value={doc.collection_id ?? ""}
                                                onChange={(e) => handleChangeCollection(doc, e.target.value)}
                                                className="text-xs border border-slate-200 rounded px-2 py-1 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 max-w-[180px]"
                                                title="Mover para outra collection"
                                            >
                                                <option value="">— sem —</option>
                                                {collections.map((c) => (
                                                    <option key={c.id} value={c.id}>{c.name}</option>
                                                ))}
                                            </select>
                                            {colName && (
                                                <span className="ml-2 inline-block px-2 py-0.5 text-xs bg-blue-50 text-blue-600 rounded">
                                                    {colName}
                                                </span>
                                            )}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="text-slate-500 uppercase text-sm">{doc.file_type}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full ${colors.bg} ${colors.text}`}>
                                                {doc.status}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-slate-500">{doc.chunks_count}</td>
                                        <td className="px-6 py-4 text-slate-500 text-sm">
                                            {new Date(doc.upload_date).toLocaleDateString()}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center justify-end gap-3">
                                                <button
                                                    onClick={() => router.push(`/documents/${doc.id}/chunks`)}
                                                    className="text-purple-600 hover:text-purple-700 text-sm font-medium"
                                                >
                                                    Chunks
                                                </button>
                                                {doc.status !== "indexed" && (
                                                    <button
                                                        onClick={() => handleProcess(doc)}
                                                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                                                    >
                                                        Process
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleReindex(doc)}
                                                    className="text-slate-600 hover:text-slate-800 text-sm font-medium"
                                                    title="Recalcula embedding e atualiza o índice FAISS"
                                                >
                                                    Reindex
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(doc)}
                                                    className="text-red-500 hover:text-red-600 text-sm font-medium"
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
