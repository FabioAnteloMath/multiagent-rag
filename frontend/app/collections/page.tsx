"use client";

import { useState, useEffect } from "react";
import { getCollections, type Collection } from "@/lib/api";

export default function CollectionsPage() {
    const [collections, setCollections] = useState<Collection[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadCollections();
    }, []);

    async function loadCollections() {
        try {
            const data = await getCollections();
            setCollections(data);
        } catch (error) {
            console.error("Failed to load:", error);
        } finally {
            setLoading(false);
        }
    }

    return (
        <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-2xl font-semibold text-slate-900">Collections</h1>
                    <p className="text-slate-500 mt-1">Organize documents by knowledge area</p>
                </div>
            </div>

            {loading ? (
                <div className="text-center py-12 text-slate-400">Loading...</div>
            ) : collections.length === 0 ? (
                <div className="text-center py-12 text-slate-500 bg-white rounded-xl border border-slate-200">
                    No collections found
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {collections.map((col) => (
                        <div
                            key={col.id}
                            className="bg-white border border-slate-200 rounded-xl p-6 hover:shadow-md transition-shadow"
                        >
                            <div className="flex items-center gap-3 mb-3">
                                <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-emerald-500 rounded-lg flex items-center justify-center">
                                    <span className="text-white text-sm font-bold">{col.name.charAt(0)}</span>
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-slate-900">{col.name}</h3>
                                    {col.is_default && (
                                        <span className="inline-block px-2 py-0.5 text-xs bg-amber-50 text-amber-600 rounded">Default</span>
                                    )}
                                </div>
                            </div>
                            {col.description && (
                                <p className="text-slate-500 text-sm mb-3">{col.description}</p>
                            )}
                            <div className="text-sm text-slate-500">
                                {col.document_count} document{col.document_count !== 1 ? "s" : ""}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}