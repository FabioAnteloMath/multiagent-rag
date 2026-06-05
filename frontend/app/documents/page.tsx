"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { getDocuments, uploadDocument, deleteDocument, processDocument, type Document } from "@/lib/api";

const statusColors: Record<string, { bg: string; text: string }> = {
    pending: { bg: "bg-amber-50", text: "text-amber-600" },
    processing: { bg: "bg-blue-50", text: "text-blue-600" },
    indexed: { bg: "bg-emerald-50", text: "text-emerald-600" },
    error: { bg: "bg-red-50", text: "text-red-600" },
};

export default function DocumentsPage() {
    const router = useRouter();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [dragOver, setDragOver] = useState(false);

    useEffect(() => {
        loadDocuments();
    }, []);

    async function loadDocuments() {
        try {
            const docs = await getDocuments();
            setDocuments(docs);
        } catch (error) {
            console.error("Failed to load documents:", error);
        } finally {
            setLoading(false);
        }
    }

    async function handleUpload(file: File) {
        setUploading(true);
        try {
            await uploadDocument(file);
            await loadDocuments();
        } catch (error) {
            console.error("Failed to upload:", error);
        } finally {
            setUploading(false);
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Delete this document?")) return;
        try {
            await deleteDocument(id);
            await loadDocuments();
        } catch (error) {
            console.error("Failed to delete:", error);
        }
    }

    async function handleProcess(id: string) {
        try {
            await processDocument(id);
            await loadDocuments();
        } catch (error) {
            console.error("Failed to process:", error);
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
    }

    return (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Documents</h1>
                    <p className="text-slate-500 mt-1">Manage your support documents</p>
                </div>
                <label className="cursor-pointer">
                    <input
                        type="file"
                        accept=".pdf,.md,.txt"
                        className="hidden"
                        onChange={handleFileSelect}
                    />
                    <span className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors font-medium text-sm">
                        {uploading ? "Uploading..." : "+ Upload"}
                    </span>
                </label>
            </div>

            <div
                className={`border-2 border-dashed rounded-xl p-8 mb-8 text-center transition-colors ${
                    dragOver ? "border-blue-400 bg-blue-50" : "border-slate-200 hover:border-slate-300"
                }`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
            >
                <div className="text-slate-500">
                    <p className="text-base mb-1">Drag files here or click Upload</p>
                    <p className="text-sm">PDF, MD, TXT</p>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : documents.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
                    No documents found
                </div>
            ) : (
                <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="bg-slate-50 border-b border-slate-200">
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Name</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Type</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Status</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Chunks</th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Date</th>
                                <th className="text-right px-6 py-3 text-xs font-medium text-slate-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100">
                            {documents.map((doc) => {
                                const colors = statusColors[doc.status] || statusColors.pending;
                                return (
                                    <tr key={doc.id} className="hover:bg-slate-50">
                                        <td className="px-6 py-4">
                                            <span className="text-slate-900 font-medium">{doc.filename}</span>
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
                                                    Edit Chunks
                                                </button>
                                                {doc.status !== "indexed" && (
                                                    <button
                                                        onClick={() => handleProcess(doc.id)}
                                                        className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                                                    >
                                                        Process
                                                    </button>
                                                )}
                                                <button
                                                    onClick={() => handleDelete(doc.id)}
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