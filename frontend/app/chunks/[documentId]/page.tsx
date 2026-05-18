"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import {
    getDocument,
    getDocumentChunks,
    createChunk,
    updateChunk,
    deleteChunk,
    rebuildDocumentIndex,
    type Chunk,
    type Document
} from "@/lib/api";

export default function ChunksPage() {
    const params = useParams();
    const router = useRouter();
    const documentId = params.documentId as string;

    const [document, setDocument] = useState<Document | null>(null);
    const [chunks, setChunks] = useState<Chunk[]>([]);
    const [loading, setLoading] = useState(true);
    const [rebuilding, setRebuilding] = useState(false);
    const [editingChunk, setEditingChunk] = useState<string | null>(null);
    const [editContent, setEditContent] = useState("");
    const [showAddForm, setShowAddForm] = useState(false);
    const [newContent, setNewContent] = useState("");
    const [newIndex, setNewIndex] = useState<string>("");

    useEffect(() => {
        loadData();
    }, [documentId]);

    async function loadData() {
        try {
            const [docData, chunksData] = await Promise.all([
                getDocument(documentId),
                getDocumentChunks(documentId)
            ]);
            setDocument(docData);
            setChunks(chunksData);
        } catch (error) {
            console.error("Failed to load:", error);
            alert("Failed to load document chunks");
        } finally {
            setLoading(false);
        }
    }

    async function handleSave(chunkId: string) {
        try {
            await updateChunk(documentId, chunkId, editContent);
            setEditingChunk(null);
            await loadData();
            await handleRebuildIndex();
        } catch (error) {
            console.error("Failed to update:", error);
            alert("Failed to update chunk");
        }
    }

    async function handleDelete(chunkId: string) {
        if (!confirm("Are you sure you want to delete this chunk?")) return;
        try {
            const result = await deleteChunk(documentId, chunkId);
            await loadData();
            await handleRebuildIndex();
        } catch (error) {
            console.error("Failed to delete:", error);
            alert("Failed to delete chunk");
        }
    }

    async function handleAdd() {
        if (!newContent.trim()) return;
        try {
            const index = newIndex ? parseInt(newIndex) : undefined;
            await createChunk(documentId, newContent, index);
            setNewContent("");
            setNewIndex("");
            setShowAddForm(false);
            await loadData();
            await handleRebuildIndex();
        } catch (error) {
            console.error("Failed to create:", error);
            alert("Failed to create chunk");
        }
    }

    async function handleRebuildIndex() {
        if (!document?.collection_id) {
            alert("Document has no collection. Cannot rebuild index.");
            return;
        }
        setRebuilding(true);
        try {
            const result = await rebuildDocumentIndex(documentId);
            if (result.success) {
                alert(`Index rebuilt successfully! ${result.chunks_indexed} chunks indexed.`);
            } else {
                alert(`Failed to rebuild index: ${result.error}`);
            }
        } catch (error) {
            console.error("Failed to rebuild:", error);
            alert("Failed to rebuild index");
        } finally {
            setRebuilding(false);
        }
    }

    function startEdit(chunk: Chunk) {
        setEditingChunk(chunk.id);
        setEditContent(chunk.content);
    }

    function cancelEdit() {
        setEditingChunk(null);
        setEditContent("");
    }

    if (loading) {
        return (
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12 text-slate-400">Loading...</div>
            </div>
        );
    }

    if (!document) {
        return (
            <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="text-center py-12 text-slate-500">Document not found</div>
            </div>
        );
    }

    return (
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center gap-4 mb-6">
                <button
                    onClick={() => router.push("/documents")}
                    className="text-slate-400 hover:text-white transition-colors"
                >
                    ← Back
                </button>
                <div className="flex-1">
                    <h1 className="text-2xl font-bold text-white">{document.filename}</h1>
                    <p className="text-slate-400 text-sm">
                        {chunks.length} chunks | Status: <span className="capitalize">{document.status}</span>
                        {document.collection_id && (
                            <span className="ml-2 text-blue-400">Collection ID: {document.collection_id}</span>
                        )}
                    </p>
                </div>
                {document.collection_id && (
                    <button
                        onClick={handleRebuildIndex}
                        disabled={rebuilding}
                        className="px-4 py-2 bg-amber-600 hover:bg-amber-700 disabled:bg-slate-600 text-white rounded-lg transition-colors"
                    >
                        {rebuilding ? "Rebuilding..." : "Rebuild Index"}
                    </button>
                )}
            </div>

            <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-white">Chunks</h2>
                <button
                    onClick={() => setShowAddForm(!showAddForm)}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                >
                    + Add Chunk
                </button>
            </div>

            {showAddForm && (
                <div className="mb-6 bg-slate-800/70 border border-slate-600 rounded-xl p-4">
                    <h3 className="text-white font-medium mb-3">Add New Chunk</h3>
                    <div className="mb-3">
                        <label className="block text-sm text-slate-400 mb-1">Content</label>
                        <textarea
                            value={newContent}
                            onChange={(e) => setNewContent(e.target.value)}
                            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-green-500"
                            rows={4}
                            placeholder="Enter chunk content..."
                        />
                    </div>
                    <div className="mb-3">
                        <label className="block text-sm text-slate-400 mb-1">Chunk Index (optional)</label>
                        <input
                            type="number"
                            value={newIndex}
                            onChange={(e) => setNewIndex(e.target.value)}
                            className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-green-500"
                            placeholder="Leave empty to add at end"
                        />
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleAdd}
                            className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                        >
                            Add
                        </button>
                        <button
                            onClick={() => {
                                setShowAddForm(false);
                                setNewContent("");
                                setNewIndex("");
                            }}
                            className="px-4 py-2 text-slate-400 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                    </div>
                </div>
            )}

            {chunks.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-slate-800/50 rounded-xl">
                    No chunks found. Process the document or add chunks manually.
                </div>
            ) : (
                <div className="space-y-4">
                    {chunks.map((chunk) => (
                        <div key={chunk.id} className="bg-slate-800/50 border border-slate-700 rounded-xl p-4">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-blue-400 text-sm font-medium">Chunk #{chunk.chunk_index}</span>
                                <div className="flex items-center gap-2">
                                    <span className={`inline-flex px-2 py-0.5 text-xs rounded-full ${
                                        chunk.embedding_status === "completed"
                                            ? "bg-green-500/20 text-green-400"
                                            : chunk.embedding_status === "error"
                                            ? "bg-red-500/20 text-red-400"
                                            : "bg-yellow-500/20 text-yellow-400"
                                    }`}>
                                        {chunk.embedding_status}
                                    </span>
                                    {editingChunk === chunk.id ? (
                                        <>
                                            <button
                                                onClick={() => handleSave(chunk.id)}
                                                className="text-green-400 hover:text-green-300 text-sm px-2 py-1"
                                            >
                                                Save
                                            </button>
                                            <button
                                                onClick={cancelEdit}
                                                className="text-slate-400 hover:text-white text-sm px-2 py-1"
                                            >
                                                Cancel
                                            </button>
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                onClick={() => startEdit(chunk)}
                                                className="text-blue-400 hover:text-blue-300 text-sm px-2 py-1"
                                            >
                                                Edit
                                            </button>
                                            <button
                                                onClick={() => handleDelete(chunk.id)}
                                                className="text-red-400 hover:text-red-300 text-sm px-2 py-1"
                                            >
                                                Delete
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                            {editingChunk === chunk.id ? (
                                <textarea
                                    value={editContent}
                                    onChange={(e) => setEditContent(e.target.value)}
                                    className="w-full bg-slate-700 border border-slate-600 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                                    rows={6}
                                />
                            ) : (
                                <p className="text-slate-300 text-sm whitespace-pre-wrap">{chunk.content}</p>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}