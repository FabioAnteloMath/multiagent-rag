"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
    getCollections,
    createCollection,
    deleteCollection,
    updateCollection,
    getCollectionDocuments,
    getDocuments,
    updateDocument,
    deleteDocument,
    processDocument,
    type Collection,
    type Document
} from "@/lib/api";

const statusColors: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    processing: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    indexed: "bg-green-500/20 text-green-400 border-green-500/30",
    error: "bg-red-500/20 text-red-400 border-red-500/30",
};

interface CollectionWithDocs extends Collection {
    documents: Document[];
    isExpanded: boolean;
    loadingDocs: boolean;
}

export default function CollectionsPage() {
    const [collections, setCollections] = useState<CollectionWithDocs[]>([]);
    const [allDocuments, setAllDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [showModal, setShowModal] = useState(false);
    const [newName, setNewName] = useState("");
    const [newDescription, setNewDescription] = useState("");
    const [editingCollection, setEditingCollection] = useState<CollectionWithDocs | null>(null);
    const [editName, setEditName] = useState("");
    const [editDescription, setEditDescription] = useState("");
    const [addingDocsTo, setAddingDocsTo] = useState<string | null>(null);

    useEffect(() => {
        loadCollections();
        loadAllDocuments();
    }, []);

    async function loadCollections() {
        try {
            const cols = await getCollections();
            setCollections(cols.map(c => ({ ...c, documents: [], isExpanded: false, loadingDocs: false })));
        } catch (error) {
            console.error("Failed to load:", error);
        } finally {
            setLoading(false);
        }
    }

    async function loadAllDocuments() {
        try {
            const docs = await getDocuments();
            setAllDocuments(docs);
        } catch (error) {
            console.error("Failed to load documents:", error);
        }
    }

    async function toggleCollection(collectionId: string) {
        const col = collections.find(c => c.id === collectionId);
        if (!col) return;

        if (col.isExpanded) {
            setCollections(collections.map(c => c.id === collectionId ? { ...c, isExpanded: false } : c));
        } else {
            setCollections(collections.map(c => c.id === collectionId ? { ...c, loadingDocs: true } : c));
            try {
                const docs = await getCollectionDocuments(collectionId);
                setCollections(collections.map(c =>
                    c.id === collectionId
                        ? { ...c, documents: docs, isExpanded: true, loadingDocs: false }
                        : c
                ));
            } catch (error) {
                console.error("Failed to load documents:", error);
                setCollections(collections.map(c => c.id === collectionId ? { ...c, loadingDocs: false } : c));
            }
        }
    }

    async function handleCreate(e: React.FormEvent) {
        e.preventDefault();
        if (!newName.trim()) return;
        try {
            await createCollection({ name: newName, description: newDescription });
            setNewName("");
            setNewDescription("");
            setShowModal(false);
            await loadCollections();
        } catch (error) {
            console.error("Failed to create:", error);
            alert("Error creating collection");
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Are you sure? This will not delete the documents, only remove them from this collection.")) return;
        try {
            await deleteCollection(id);
            await loadCollections();
        } catch (error) {
            console.error("Failed to delete:", error);
        }
    }

    async function startEdit(col: CollectionWithDocs) {
        setEditingCollection(col);
        setEditName(col.name);
        setEditDescription(col.description);
    }

    async function handleUpdate(e: React.FormEvent) {
        e.preventDefault();
        if (!editingCollection || !editName.trim()) return;
        try {
            await updateCollection(editingCollection.id, { name: editName, description: editDescription });
            setEditingCollection(null);
            await loadCollections();
        } catch (error) {
            console.error("Failed to update:", error);
            alert("Error updating collection");
        }
    }

    async function handleAddDocumentToCollection(collectionId: string, documentId: string) {
        try {
            await updateDocument(documentId, collectionId);
            await loadAllDocuments();
            const docs = await getCollectionDocuments(collectionId);
            setCollections(collections.map(c =>
                c.id === collectionId ? { ...c, documents: docs } : c
            ));
        } catch (error) {
            console.error("Failed to add document:", error);
            alert("Error adding document to collection");
        }
    }

    async function handleRemoveDocument(collectionId: string, documentId: string) {
        try {
            await updateDocument(documentId, undefined);
            await loadAllDocuments();
            const docs = await getCollectionDocuments(collectionId);
            setCollections(collections.map(c =>
                c.id === collectionId ? { ...c, documents: docs } : c
            ));
        } catch (error) {
            console.error("Failed to remove document:", error);
            alert("Error removing document from collection");
        }
    }

    async function handleDeleteDoc(documentId: string) {
        if (!confirm("Are you sure you want to delete this document? This action cannot be undone.")) return;
        try {
            await deleteDocument(documentId);
            await loadAllDocuments();
            for (const col of collections) {
                if (col.isExpanded) {
                    const docs = await getCollectionDocuments(col.id);
                    setCollections(collections.map(c =>
                        c.id === col.id ? { ...c, documents: docs } : c
                    ));
                }
            }
        } catch (error) {
            console.error("Failed to delete:", error);
        }
    }

    async function handleProcess(collectionId: string, docId: string) {
        try {
            await processDocument(docId);
            const docs = await getCollectionDocuments(collectionId);
            setCollections(collections.map(c =>
                c.id === collectionId ? { ...c, documents: docs } : c
            ));
        } catch (error) {
            console.error("Failed to process:", error);
        }
    }

    function getAvailableDocuments(collectionId: string): Document[] {
        const assignedIds = new Set(
            collections.find(c => c.id === collectionId)?.documents.map(d => d.id) || []
        );
        return allDocuments.filter(d => !assignedIds.has(d.id));
    }

    return (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white">Collections</h1>
                    <p className="text-slate-400 mt-1">Organize your documents into collections</p>
                </div>
                <button
                    onClick={() => setShowModal(true)}
                    className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors"
                >
                    + New Collection
                </button>
            </div>

            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : collections.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                    No collections found. Create one to get started.
                </div>
            ) : (
                <div className="space-y-4">
                    {collections.map((col) => (
                        <div key={col.id} className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
                            <div
                                className="flex items-center justify-between p-4 cursor-pointer hover:bg-slate-700/30"
                                onClick={() => toggleCollection(col.id)}
                            >
                                <div className="flex items-center gap-4">
                                    <span className={`transform transition-transform ${col.isExpanded ? "rotate-90" : ""}`}>
                                        ▶
                                    </span>
                                    <div>
                                        <h3 className="text-lg font-semibold text-white">{col.name}</h3>
                                        <div className="flex items-center gap-3 mt-1">
                                            {col.is_default && (
                                                <span className="inline-block px-2 py-0.5 text-xs bg-purple-500/20 text-purple-400 rounded">
                                                    Default
                                                </span>
                                            )}
                                            <span className="text-slate-500 text-sm">
                                                {col.document_count} document{col.document_count !== 1 ? "s" : ""}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                                    <button
                                        onClick={() => startEdit(col)}
                                        className="text-blue-400 hover:text-blue-300 text-sm px-2 py-1"
                                    >
                                        Edit
                                    </button>
                                    <button
                                        onClick={() => handleDelete(col.id)}
                                        className="text-red-400 hover:text-red-300 text-sm px-2 py-1"
                                    >
                                        Delete
                                    </button>
                                </div>
                            </div>

                            {col.isExpanded && (
                                <div className="border-t border-slate-700 p-4 bg-slate-800/30">
                                    {col.loadingDocs ? (
                                        <div className="text-center py-8 text-slate-400">Loading documents...</div>
                                    ) : (
                                        <>
                                            <div className="flex items-center justify-between mb-4">
                                                <h4 className="text-sm font-medium text-slate-400">Documents in this collection</h4>
                                                <button
                                                    onClick={() => setAddingDocsTo(col.id)}
                                                    className="inline-flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg text-sm transition-colors"
                                                >
                                                    + Add Documents
                                                </button>
                                            </div>

                                            {col.documents.length === 0 ? (
                                                <div className="text-center py-8 text-slate-500 bg-slate-800/50 rounded-lg">
                                                    No documents in this collection. Click "Add Documents" to assign existing documents.
                                                </div>
                                            ) : (
                                                <div className="bg-slate-800 rounded-lg overflow-hidden mb-4">
                                                    <table className="w-full">
                                                        <thead className="bg-slate-700/50">
                                                            <tr>
                                                                <th className="text-left px-4 py-2 text-xs font-medium text-slate-400">Name</th>
                                                                <th className="text-left px-4 py-2 text-xs font-medium text-slate-400">Type</th>
                                                                <th className="text-left px-4 py-2 text-xs font-medium text-slate-400">Status</th>
                                                                <th className="text-left px-4 py-2 text-xs font-medium text-slate-400">Chunks</th>
                                                                <th className="text-right px-4 py-2 text-xs font-medium text-slate-400">Actions</th>
                                                            </tr>
                                                        </thead>
                                                        <tbody className="divide-y divide-slate-700">
                                                            {col.documents.map((doc) => (
                                                                <tr key={doc.id} className="hover:bg-slate-700/30">
                                                                    <td className="px-4 py-3">
                                                                        <Link href={`/chunks/${doc.id}`} className="text-white hover:text-blue-400 transition-colors">
                                                                            {doc.filename}
                                                                        </Link>
                                                                    </td>
                                                                    <td className="px-4 py-3">
                                                                        <span className="text-slate-400 uppercase text-sm">{doc.file_type}</span>
                                                                    </td>
                                                                    <td className="px-4 py-3">
                                                                        <span className={`inline-flex px-2 py-0.5 text-xs font-medium rounded-full border ${statusColors[doc.status] || statusColors.pending}`}>
                                                                            {doc.status}
                                                                        </span>
                                                                    </td>
                                                                    <td className="px-4 py-3 text-slate-400">{doc.chunks_count}</td>
                                                                    <td className="px-4 py-3">
                                                                        <div className="flex items-center justify-end gap-2">
                                                                            <Link
                                                                                href={`/chunks/${doc.id}`}
                                                                                className="text-purple-400 hover:text-purple-300 text-sm px-2 py-1"
                                                                            >
                                                                                Chunks
                                                                            </Link>
                                                                            {doc.status !== "indexed" && (
                                                                                <button
                                                                                    onClick={() => handleProcess(col.id, doc.id)}
                                                                                    className="text-blue-400 hover:text-blue-300 text-sm px-2 py-1"
                                                                                >
                                                                                    Process
                                                                                </button>
                                                                            )}
                                                                            <button
                                                                                onClick={() => handleRemoveDocument(col.id, doc.id)}
                                                                                className="text-yellow-400 hover:text-yellow-300 text-sm px-2 py-1"
                                                                            >
                                                                                Remove
                                                                            </button>
                                                                            <button
                                                                                onClick={() => handleDeleteDoc(doc.id)}
                                                                                className="text-red-400 hover:text-red-300 text-sm px-2 py-1"
                                                                            >
                                                                                Delete
                                                                            </button>
                                                                        </div>
                                                                    </td>
                                                                </tr>
                                                            ))}
                                                        </tbody>
                                                    </table>
                                                </div>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {showModal && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-md">
                        <h2 className="text-xl font-semibold text-white mb-4">New Collection</h2>
                        <form onSubmit={handleCreate}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">Name</label>
                                <input
                                    type="text"
                                    value={newName}
                                    onChange={(e) => setNewName(e.target.value)}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                                    placeholder="Ex: API Support"
                                    required
                                />
                            </div>
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                                <textarea
                                    value={newDescription}
                                    onChange={(e) => setNewDescription(e.target.value)}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                                    placeholder="Optional description..."
                                    rows={3}
                                />
                            </div>
                            <div className="flex items-center justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setShowModal(false)}
                                    className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                                >
                                    Create
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {editingCollection && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-md">
                        <h2 className="text-xl font-semibold text-white mb-4">Edit Collection</h2>
                        <form onSubmit={handleUpdate}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium text-slate-300 mb-2">Name</label>
                                <input
                                    type="text"
                                    value={editName}
                                    onChange={(e) => setEditName(e.target.value)}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                                    required
                                />
                            </div>
                            <div className="mb-6">
                                <label className="block text-sm font-medium text-slate-300 mb-2">Description</label>
                                <textarea
                                    value={editDescription}
                                    onChange={(e) => setEditDescription(e.target.value)}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-purple-500"
                                    rows={3}
                                />
                            </div>
                            <div className="flex items-center justify-end gap-3">
                                <button
                                    type="button"
                                    onClick={() => setEditingCollection(null)}
                                    className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors"
                                >
                                    Save
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {addingDocsTo && (
                <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 w-full max-w-lg">
                        <h2 className="text-xl font-semibold text-white mb-4">Add Documents to Collection</h2>
                        <p className="text-slate-400 text-sm mb-4">Select documents to add to this collection:</p>

                        {getAvailableDocuments(addingDocsTo).length === 0 ? (
                            <div className="text-center py-8 text-slate-500">
                                No available documents to add. Upload new documents first.
                            </div>
                        ) : (
                            <div className="max-h-96 overflow-y-auto">
                                {getAvailableDocuments(addingDocsTo).map((doc) => (
                                    <div
                                        key={doc.id}
                                        className="flex items-center justify-between p-3 hover:bg-slate-700/50 rounded-lg cursor-pointer"
                                        onClick={() => handleAddDocumentToCollection(addingDocsTo, doc.id)}
                                    >
                                        <div>
                                            <span className="text-white">{doc.filename}</span>
                                            <span className="text-slate-500 text-sm ml-2">({doc.file_type})</span>
                                        </div>
                                        <span className="text-green-400">+ Add</span>
                                    </div>
                                ))}
                            </div>
                        )}

                        <div className="flex items-center justify-end mt-4">
                            <button
                                onClick={() => setAddingDocsTo(null)}
                                className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}