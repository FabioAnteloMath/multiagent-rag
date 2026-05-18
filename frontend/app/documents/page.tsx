"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { getDocuments, uploadDocument, deleteDocument, processDocument, type Document } from "@/lib/api";

const statusColors: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    processing: "bg-blue-500/20 text-blue-400 border-blue-500/30",
    indexed: "bg-green-500/20 text-green-400 border-green-500/30",
    error: "bg-red-500/20 text-red-400 border-red-500/30",
};

export default function DocumentsPage() {
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
            alert("Error uploading document");
        } finally {
            setUploading(false);
        }
    }

    async function handleDelete(id: string) {
        if (!confirm("Are you sure you want to delete?")) return;
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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-bold text-white">Documents</h1>
                    <p className="text-slate-400 mt-1">Manage your support documents</p>
                </div>
                <label className="cursor-pointer">
                    <input
                        type="file"
                        accept=".pdf,.md,.txt"
                        className="hidden"
                        onChange={handleFileSelect}
                    />
                    <span className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors">
                        {uploading ? "Uploading..." : "+ Upload Document"}
                    </span>
                </label>
            </div>

            <div
                className={`border-2 border-dashed rounded-xl p-8 mb-8 text-center transition-colors ${
                    dragOver ? "border-blue-500 bg-blue-500/10" : "border-slate-700 hover:border-slate-600"
                }`}
                onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
            >
                <div className="text-slate-400">
                    <p className="text-lg mb-2">Drag files here or click Upload</p>
                    <p className="text-sm">Formats: PDF, MD, TXT</p>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : documents.length === 0 ? (
                <div className="text-center py-12 text-slate-500">
                    No documents found. Upload a file to get started.
                </div>
            ) : (
                <div className="bg-slate-800/50 border border-slate-700 rounded-xl overflow-hidden">
                    <table className="w-full">
                        <thead className="bg-slate-800 border-b border-slate-700">
                            <tr>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Name
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Type
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Status
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Chunks
                                </th>
                                <th className="text-left px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Date
                                </th>
                                <th className="text-right px-6 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                                    Actions
                                </th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-700">
                            {documents.map((doc) => (
                                <tr key={doc.id} className="hover:bg-slate-700/30">
                                    <td className="px-6 py-4">
                                        <Link href={`/chunks/${doc.id}`} className="text-white font-medium hover:text-blue-400 transition-colors">
                                            {doc.filename}
                                        </Link>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className="text-slate-400 uppercase text-sm">{doc.file_type}</span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <span className={`inline-flex px-2 py-1 text-xs font-medium rounded-full border ${statusColors[doc.status] || statusColors.pending}`}>
                                            {doc.status}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 text-slate-400">{doc.chunks_count}</td>
                                    <td className="px-6 py-4 text-slate-400 text-sm">
                                        {new Date(doc.upload_date).toLocaleDateString("en-US")}
                                    </td>
                                    <td className="px-6 py-4">
                                        <div className="flex items-center justify-end gap-2">
                                            <Link
                                                href={`/chunks/${doc.id}`}
                                                className="text-purple-400 hover:text-purple-300 text-sm px-2 py-1"
                                            >
                                                Chunks
                                            </Link>
                                            {doc.status !== "indexed" && (
                                                <button
                                                    onClick={() => handleProcess(doc.id)}
                                                    className="text-blue-400 hover:text-blue-300 text-sm px-2 py-1"
                                                >
                                                    Process
                                                </button>
                                            )}
                                            <button
                                                onClick={() => handleDelete(doc.id)}
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
        </div>
    );
}