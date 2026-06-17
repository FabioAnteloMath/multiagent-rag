"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";
import {
    getCollections, createCollection, updateCollection, deleteCollection,
    getCollectionDocuments, updateDocument, getDocuments, deleteDocument,
    rebuildDocumentIndex, rebuildAllIndexes,
    type Collection, type Document,
} from "@/lib/api";

interface CollectionFormState {
    name: string;
    description: string;
    is_default: boolean;
}

const EMPTY_FORM: CollectionFormState = { name: "", description: "", is_default: false };

export default function CollectionsPage() {
    const router = useRouter();
    const [collections, setCollections] = useState<Collection[]>([]);
    const [loading, setLoading] = useState(true);

    // Modal state (shared by create + edit)
    const [modalOpen, setModalOpen] = useState(false);
    const [editingCollection, setEditingCollection] = useState<Collection | null>(null);
    const [form, setForm] = useState<CollectionFormState>(EMPTY_FORM);
    const [saving, setSaving] = useState(false);
    const [formError, setFormError] = useState<string | null>(null);

    // Expanded collection (shows its documents)
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [expandedDocs, setExpandedDocs] = useState<Document[]>([]);
    const [expandedLoading, setExpandedLoading] = useState(false);

    // All unassigned documents (for "move into collection" dropdown)
    const [allDocs, setAllDocs] = useState<Document[]>([]);

    // Toast for action feedback
    const [toast, setToast] = useState<{ type: "ok" | "err"; msg: string } | null>(null);
    const showToast = (type: "ok" | "err", msg: string) => {
        setToast({ type, msg });
        window.setTimeout(() => setToast(null), 3500);
    };

    const loadCollections = useCallback(async () => {
        try {
            const data = await getCollections();
            setCollections(data);
        } catch (error) {
            console.error("Failed to load:", error);
            showToast("err", "Falha ao carregar collections");
        } finally {
            setLoading(false);
        }
    }, []);

    const loadAllDocs = useCallback(async () => {
        try {
            setAllDocs(await getDocuments());
        } catch (error) {
            console.error("Failed to load all docs:", error);
        }
    }, []);

    useEffect(() => {
        loadCollections();
        loadAllDocs();
    }, [loadCollections, loadAllDocs]);

    // Unassigned docs available to move into the currently expanded collection
    const availableToMoveIn = useMemo(() => {
        if (!expandedId) return [];
        const inExpanded = new Set(expandedDocs.map((d) => d.id));
        return allDocs.filter((d) => !d.collection_id || (!inExpanded.has(d.id) && d.collection_id !== expandedId));
    }, [allDocs, expandedDocs, expandedId]);

    async function openCreate() {
        setEditingCollection(null);
        setForm(EMPTY_FORM);
        setFormError(null);
        setModalOpen(true);
    }

    function openEdit(col: Collection, e: React.MouseEvent) {
        e.stopPropagation();
        setEditingCollection(col);
        setForm({
            name: col.name,
            description: col.description ?? "",
            is_default: col.is_default,
        });
        setFormError(null);
        setModalOpen(true);
    }

    async function handleSaveForm() {
        if (!form.name.trim()) {
            setFormError("Nome é obrigatório");
            return;
        }
        setSaving(true);
        setFormError(null);
        try {
            if (editingCollection) {
                await updateCollection(editingCollection.id, {
                    name: form.name.trim(),
                    description: form.description.trim(),
                });
                showToast("ok", `Collection "${form.name}" atualizada`);
            } else {
                await createCollection({
                    name: form.name.trim(),
                    description: form.description.trim(),
                    is_default: form.is_default,
                });
                showToast("ok", `Collection "${form.name}" criada`);
            }
            setModalOpen(false);
            await loadCollections();
        } catch (error) {
            const msg = error instanceof Error ? error.message : "Erro ao salvar";
            setFormError(msg);
        } finally {
            setSaving(false);
        }
    }

    async function handleDelete(col: Collection, e: React.MouseEvent) {
        e.stopPropagation();
        if (col.is_default) {
            showToast("err", "Não é possível excluir a collection padrão");
            return;
        }
        if (!confirm(`Excluir "${col.name}"? Os documentos associados serão desvinculados (não excluídos).`)) return;
        try {
            await deleteCollection(col.id);
            showToast("ok", `Collection "${col.name}" excluída`);
            if (expandedId === col.id) setExpandedId(null);
            await Promise.all([loadCollections(), loadAllDocs()]);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao excluir");
        }
    }

    async function toggleExpand(col: Collection) {
        if (expandedId === col.id) {
            setExpandedId(null);
            setExpandedDocs([]);
            return;
        }
        setExpandedId(col.id);
        setExpandedLoading(true);
        try {
            const docs = await getCollectionDocuments(col.id);
            setExpandedDocs(docs as Document[]);
        } catch (error) {
            showToast("err", "Erro ao carregar documentos da collection");
        } finally {
            setExpandedLoading(false);
        }
    }

    async function moveDocument(docId: string, targetCollectionId: string | null) {
        try {
            await updateDocument(docId, targetCollectionId);
            showToast("ok", targetCollectionId ? "Documento movido" : "Documento desvinculado");
            // Refresh: collection doc list + global doc list
            if (expandedId) {
                const docs = await getCollectionDocuments(expandedId);
                setExpandedDocs(docs as Document[]);
            }
            await Promise.all([loadCollections(), loadAllDocs()]);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao mover documento");
        }
    }

    async function removeDocFromCollection(docId: string) {
        await moveDocument(docId, null);
    }

    async function handleDeleteDoc(doc: Document) {
        if (!confirm(`Excluir "${doc.filename}" permanentemente? Os chunks e o índice FAISS serão removidos.`)) return;
        try {
            await deleteDocument(doc.id);
            showToast("ok", "Documento excluído");
            if (expandedId) {
                const docs = await getCollectionDocuments(expandedId);
                setExpandedDocs(docs as Document[]);
            }
            await Promise.all([loadCollections(), loadAllDocs()]);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao excluir documento");
        }
    }

    async function handleReindexDoc(doc: Document) {
        try {
            await rebuildDocumentIndex(doc.id);
            showToast("ok", `Reindexação de "${doc.filename}" concluída`);
        } catch (error) {
            showToast("err", error instanceof Error ? error.message : "Erro ao reindexar");
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
            {/* Header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Collections</h1>
                    <p className="text-slate-500 mt-1">Organize documents by knowledge area</p>
                </div>
                <div className="flex items-center gap-2">
                    <button
                        onClick={handleRebuildAll}
                        className="inline-flex items-center gap-2 bg-slate-100 hover:bg-slate-200 text-slate-700 px-4 py-2 rounded-lg transition-colors font-medium text-sm"
                        title="Rebuild FAISS index for every collection"
                    >
                        Rebuild all indexes
                    </button>
                    <button
                        onClick={openCreate}
                        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors font-medium text-sm"
                    >
                        + New Collection
                    </button>
                </div>
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
            ) : collections.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
                    No collections found — crie a primeira com o botão acima.
                </div>
            ) : (
                <div className="space-y-4">
                    {collections.map((col) => {
                        const isExpanded = expandedId === col.id;
                        return (
                            <div
                                key={col.id}
                                className="bg-white border border-slate-200 rounded-xl overflow-hidden hover:shadow-md transition-shadow"
                            >
                                <div
                                    className="p-6 cursor-pointer flex items-center gap-4"
                                    onClick={() => toggleExpand(col)}
                                >
                                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center shrink-0">
                                        <span className="text-white text-sm font-bold">{col.name.charAt(0).toUpperCase()}</span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <h3 className="text-lg font-semibold text-slate-900 truncate">{col.name}</h3>
                                            {col.is_default && (
                                                <span className="inline-block px-2 py-0.5 text-xs bg-amber-50 text-amber-600 rounded">Default</span>
                                            )}
                                        </div>
                                        {col.description && (
                                            <p className="text-slate-500 text-sm truncate">{col.description}</p>
                                        )}
                                    </div>
                                    <div className="text-sm text-slate-500 shrink-0">
                                        {col.document_count} doc{col.document_count !== 1 ? "s" : ""}
                                    </div>
                                    <div className="flex items-center gap-2 shrink-0" onClick={(e) => e.stopPropagation()}>
                                        <button
                                            onClick={(e) => openEdit(col, e)}
                                            className="text-blue-600 hover:text-blue-700 text-sm font-medium px-2 py-1"
                                        >
                                            Edit
                                        </button>
                                        <button
                                            onClick={(e) => handleDelete(col, e)}
                                            className="text-red-500 hover:text-red-600 text-sm font-medium px-2 py-1"
                                        >
                                            Delete
                                        </button>
                                    </div>
                                    <svg
                                        className={`w-5 h-5 text-slate-400 transition-transform shrink-0 ${isExpanded ? "rotate-180" : ""}`}
                                        fill="none" stroke="currentColor" viewBox="0 0 24 24"
                                    >
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>

                                {isExpanded && (
                                    <div className="border-t border-slate-200 bg-slate-50 p-6">
                                        <div className="flex items-center justify-between mb-3">
                                            <h4 className="text-sm font-medium text-slate-700">Documentos nesta collection</h4>
                                            <button
                                                onClick={() => router.push("/documents")}
                                                className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                                            >
                                                + Adicionar via Documents →
                                            </button>
                                        </div>
                                        {expandedLoading ? (
                                            <p className="text-sm text-slate-400">Carregando...</p>
                                        ) : expandedDocs.length === 0 ? (
                                            <p className="text-sm text-slate-400">Nenhum documento. Faça upload em /documents e atribua a esta collection.</p>
                                        ) : (
                                            <div className="bg-white rounded-lg border border-slate-200 divide-y divide-slate-100">
                                                {expandedDocs.map((doc) => (
                                                    <div key={doc.id} className="px-4 py-3 flex items-center gap-3">
                                                        <div className="flex-1 min-w-0">
                                                            <p className="text-sm font-medium text-slate-800 truncate">{doc.filename}</p>
                                                            <p className="text-xs text-slate-400">
                                                                {doc.file_type.toUpperCase()} • {doc.chunks_count} chunks • {doc.status}
                                                            </p>
                                                        </div>
                                                        <button
                                                            onClick={() => router.push(`/documents/${doc.id}/chunks`)}
                                                            className="text-xs text-purple-600 hover:text-purple-700 font-medium"
                                                        >
                                                            Chunks
                                                        </button>
                                                        <button
                                                            onClick={() => handleReindexDoc(doc)}
                                                            className="text-xs text-slate-600 hover:text-slate-800 font-medium"
                                                        >
                                                            Reindex
                                                        </button>
                                                        <button
                                                            onClick={() => removeDocFromCollection(doc.id)}
                                                            className="text-xs text-amber-600 hover:text-amber-700 font-medium"
                                                            title="Desvincula deste collection (o documento continua existindo)"
                                                        >
                                                            Unlink
                                                        </button>
                                                        <button
                                                            onClick={() => handleDeleteDoc(doc)}
                                                            className="text-xs text-red-500 hover:text-red-600 font-medium"
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}

                                        {/* Move existing unassigned doc into this collection */}
                                        {availableToMoveIn.length > 0 && (
                                            <div className="mt-4 pt-4 border-t border-slate-200">
                                                <h4 className="text-sm font-medium text-slate-700 mb-2">Vincular documento existente</h4>
                                                <div className="flex flex-wrap gap-2">
                                                    {availableToMoveIn.map((doc) => (
                                                        <button
                                                            key={doc.id}
                                                            onClick={() => moveDocument(doc.id, col.id)}
                                                            className="inline-flex items-center gap-2 text-xs bg-white border border-slate-200 hover:border-blue-400 hover:bg-blue-50 text-slate-700 px-3 py-1.5 rounded-lg transition-colors"
                                                            title={doc.collection_id ? `Currently in another collection` : "Sem collection"}
                                                        >
                                                            <span className="truncate max-w-[200px]">{doc.filename}</span>
                                                            <span className="text-blue-500">+</span>
                                                        </button>
                                                    ))}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Modal: Create / Edit collection */}
            {modalOpen && (
                <div
                    className="fixed inset-0 z-50 bg-slate-900/50 flex items-center justify-center p-4"
                    onClick={() => !saving && setModalOpen(false)}
                >
                    <div
                        className="bg-white rounded-xl shadow-xl max-w-md w-full p-6"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <h2 className="text-lg font-semibold text-slate-900 mb-4">
                            {editingCollection ? "Edit Collection" : "New Collection"}
                        </h2>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Nome *</label>
                                <input
                                    type="text"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    disabled={!!editingCollection}  // name is the natural key; backend lets you change it but we lock to keep IDs stable
                                    placeholder="ex: api-docs"
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-500"
                                    autoFocus
                                />
                                {editingCollection && (
                                    <p className="text-xs text-slate-400 mt-1">Renomear collection é desabilitado nesta versão para manter a estabilidade do índice FAISS.</p>
                                )}
                            </div>
                            <div>
                                <label className="block text-sm font-medium text-slate-700 mb-1">Descrição</label>
                                <textarea
                                    value={form.description}
                                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    rows={3}
                                    placeholder="O que esta collection cobre?"
                                    className="w-full px-3 py-2 border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                />
                            </div>
                            {!editingCollection && (
                                <label className="flex items-center gap-2 text-sm text-slate-700">
                                    <input
                                        type="checkbox"
                                        checked={form.is_default}
                                        onChange={(e) => setForm({ ...form, is_default: e.target.checked })}
                                        className="rounded border-slate-300 text-blue-500 focus:ring-blue-500"
                                    />
                                    Marcar como collection padrão (docs sem collection vão pra cá)
                                </label>
                            )}
                            {formError && (
                                <div className="text-sm text-red-600 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
                                    {formError}
                                </div>
                            )}
                        </div>
                        <div className="flex justify-end gap-3 mt-6">
                            <button
                                onClick={() => setModalOpen(false)}
                                disabled={saving}
                                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-lg transition-colors disabled:opacity-50"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSaveForm}
                                disabled={saving || !form.name.trim()}
                                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white rounded-lg transition-colors"
                            >
                                {saving ? "Saving..." : (editingCollection ? "Save" : "Create")}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
