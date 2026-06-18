const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8011/api';

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  upload_date: string;
  status: string;
  collection_id: string | null;
  chunks_count: number;
}

export interface Chunk {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  embedding_status: string;
}

export interface Collection {
  id: string;
  name: string;
  description: string;
  is_default: boolean;
  document_count: number;
  created_at: string;
}

export interface Agent {
  id: string;
  name: string;
  specialty: string;
  system_prompt: string;
  guidelines: string;
  personality: string;
  response_format: string;
  examples: string;
  collection_id: string | null;
  collection_name: string | null;
  provider: string;
  model_name: string;
  temperature: number;
  is_active: boolean;
  is_fallback: boolean;
  created_at: string;
}

export interface RoutingInfo {
  chosen: string[];
  via: "llm" | "keyword" | "llm_override_keyword" | "default" | "clarifying" | string;
  llm_category?: string | null;
  llm_confidence?: number | null;
  llm_raw?: string;
  keyword_matches: string[];
  fallback_used: boolean;
  reasoning: string;
}

export interface AskResponse {
  answer: string;
  sources: string[];
  agent_used: string[];
  steps: string[];
  needs_clarifying?: boolean;
  tokens_used?: number;
  thinking?: string;
  model_used?: string;
  total_time_ms?: number;
  confidence?: number;
  collection_searched?: string;
  routing?: RoutingInfo | null;
}

export async function updateDocument(id: string, collectionId?: string | null): Promise<Document> {
  // Backend expects `collection_id`. Pass null explicitly to detach from a collection,
  // or undefined to leave it untouched. The backend treats null as "remove".
  const body: Record<string, unknown> = {};
  if (collectionId !== undefined) {
    body.collection_id = collectionId;
  }
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error('Failed to update document');
  return res.json();
}

export async function getDocuments(): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/documents`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to fetch documents');
  return res.json();
}

export async function getDocument(id: string): Promise<Document> {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to fetch document');
  return res.json();
}

export async function uploadDocument(file: File, collectionId?: string | null): Promise<{ id: string; filename: string; status: string; message: string }> {
  const formData = new FormData();
  formData.append('file', file);
  // Send `collection_id` even when empty string so the backend can distinguish
  // "explicitly no collection" from "caller forgot". The backend ignores falsy.
  if (collectionId) formData.append('collection_id', collectionId);

  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) throw new Error('Failed to upload document');
  return res.json();
}

export async function deleteDocument(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/documents/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to delete document');
}

export async function processDocument(id: string): Promise<{ message: string }> {
  const res = await fetch(`${API_BASE}/documents/${id}/process`, {
    method: 'POST',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to process document');
  return res.json();
}

export async function getDocumentChunks(id: string): Promise<Chunk[]> {
  const res = await fetch(`${API_BASE}/documents/${id}/chunks`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to fetch chunks');
  return res.json();
}

export async function createChunk(documentId: string, content: string, chunkIndex?: number): Promise<Chunk> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/chunks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, chunk_index: chunkIndex }),
  });
  if (!res.ok) throw new Error('Failed to create chunk');
  return res.json();
}

export async function updateChunk(documentId: string, chunkId: string, content?: string, chunkIndex?: number): Promise<Chunk> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/chunks/${chunkId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content, chunk_index: chunkIndex }),
  });
  if (!res.ok) throw new Error('Failed to update chunk');
  return res.json();
}

export async function deleteChunk(documentId: string, chunkId: string): Promise<{ message: string; chunks_remaining: number }> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/chunks/${chunkId}`, {
    method: 'DELETE',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to delete chunk');
  return res.json();
}

export async function getCollections(): Promise<Collection[]> {
  const res = await fetch(`${API_BASE}/collections`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to fetch collections');
  return res.json();
}

export async function getCollectionDocuments(collectionId: string): Promise<Document[]> {
  const res = await fetch(`${API_BASE}/collections/${collectionId}/documents`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to fetch collection documents');
  return res.json();
}

export async function updateCollection(id: string, data: { name?: string; description?: string }): Promise<Collection> {
  const res = await fetch(`${API_BASE}/collections/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update collection');
  return res.json();
}

export async function createCollection(data: { name: string; description?: string; is_default?: boolean }): Promise<Collection> {
  const res = await fetch(`${API_BASE}/collections`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create collection');
  return res.json();
}

export async function deleteCollection(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/collections/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to delete collection');
}

export async function getAgents(): Promise<Agent[]> {
  const res = await fetch(`${API_BASE}/agents`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to fetch agents');
  return res.json();
}

export async function createAgent(data: {
  name: string;
  specialty?: string;
  collection_id?: string;
  provider?: string;
  model_name?: string;
  temperature?: number;
  system_prompt?: string;
  guidelines?: string;
  personality?: string;
  response_format?: string;
  examples?: string;
  is_fallback?: boolean | null;
}): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create agent');
  return res.json();
}

export async function deleteAgent(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/agents/${id}`, {
    method: 'DELETE',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to delete agent');
}

export async function updateAgent(id: string, data: {
  name?: string;
  specialty?: string;
  collection_id?: string;
  provider?: string;
  model_name?: string;
  temperature?: number;
  is_active?: boolean;
  is_fallback?: boolean;
  system_prompt?: string;
  guidelines?: string;
  personality?: string;
  response_format?: string;
  examples?: string;
}): Promise<Agent> {
  const res = await fetch(`${API_BASE}/agents/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update agent');
  return res.json();
}

export async function askQuestion(
  question: string,
  topK: number = 4,
  mode: "baseline" | "auto" | "single_rag" = "auto",
  forceAgent?: string
): Promise<AskResponse> {
  const res = await fetch(`${API_BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK, mode, force_agent: forceAgent }),
  });
  if (!res.ok) throw new Error("Failed to ask question");
  return res.json();
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`, {
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to check health');
  return res.json();
}

export async function rebuildDocumentIndex(documentId: string): Promise<{ success: boolean; collection?: string; chunks_indexed?: number; index_path?: string; error?: string }> {
  const res = await fetch(`${API_BASE}/documents/${documentId}/reindex`, {
    method: 'POST',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to rebuild index');
  return res.json();
}

export async function rebuildAllIndexes(): Promise<{ message: string; results: Record<string, unknown> }> {
  const res = await fetch(`${API_BASE}/documents/rebuild-all-indexes`, {
    method: 'POST',
    credentials: 'include',
  } as RequestInit);
  if (!res.ok) throw new Error('Failed to rebuild all indexes');
  return res.json();
}

// ---------------------------------------------------------------------------
// Provider / model catalog
// ---------------------------------------------------------------------------

export interface ProviderSpec {
  id: string;
  name: string;
  models: string[];
  free: boolean;
  notes: string;
}

export const PROVIDER_CATALOG: ProviderSpec[] = [
  {
    id: "ollama",
    name: "Ollama (Local)",
    free: true,
    notes: "Local, no cost. Models you have pulled with `ollama pull`.",
    models: [
      "llama3.2:3b",
      "llama3.2:1b",
      "llama3.1:8b",
      "mistral:7b",
      "qwen2.5:1.5b",
      "qwen2.5:7b",
      "phi3:mini",
      "gemma2:2b",
      "codellama:7b",
    ],
  },
  {
    id: "minimax",
    name: "MiniMax (Cloud)",
    free: false,
    notes: "Primary cloud model. Requires MINIMAX_API_KEY.",
    models: ["MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
  },
  {
    id: "groq",
    name: "Groq (Cloud, free tier)",
    free: true,
    notes: "Ultra-fast inference. Free tier ~30 req/min. Needs GROQ_API_KEY.",
    models: [
      "llama-3.1-8b-instant",
      "llama-3.3-70b-versatile",
      "mixtral-8x7b-32768",
      "gemma2-9b-it",
    ],
  },
  {
    id: "gemini",
    name: "Google Gemini (Cloud, free tier)",
    free: true,
    notes: "Free tier rate-limited. Needs GEMINI_API_KEY.",
    models: ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash-exp"],
  },
];

export function getProviderSpec(providerId: string): ProviderSpec | undefined {
  return PROVIDER_CATALOG.find((p) => p.id === providerId);
}