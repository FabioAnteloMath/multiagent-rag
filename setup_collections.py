import requests
import json

BASE_URL = "http://localhost:8010/api"

print("=== Setting up Collections and Documents ===\n")

# Create collections
collections = [
    {"name": "SuporteAPI", "description": "Documentos de suporte tecnico API, erros HTTP, autenticacao e runbooks"},
    {"name": "Database", "description": "Documentos de banco de dados, Postgres, Redis e troubleshooting"},
    {"name": "DevOps", "description": "Documentos de DevOps, deploy, rollback e monitoramento"},
]

print("Creating collections...")
for col in collections:
    resp = requests.post(f"{BASE_URL}/collections", json=col)
    if resp.status_code == 200:
        print(f"  Created: {col['name']}")
    else:
        print(f"  {col['name']}: {resp.text[:100]}")

# List collections
print("\nListing collections...")
resp = requests.get(f"{BASE_URL}/collections")
cols = resp.json()
print(f"Found {len(cols)} collections:")
for c in cols:
    print(f"  - {c['name']} (id: {c['id'][:20]}...)")

# Get documents
print("\nGetting documents...")
resp = requests.get(f"{BASE_URL}/documents")
docs = resp.json()
print(f"Found {len(docs)} documents")

# Document to collection mapping
doc_mapping = {
    "SuporteAPI": ["faq-autenticacao.md", "runbook-api-gateway.md", "sla-escalonamento.md"],
    "Database": ["troubleshooting-postgres.txt", "incidente-cache-2026-04-18.md"],
    "DevOps": ["procedimento-rollback.md", "release-checklist.md", "observabilidade-alertas.md"],
}

# Assign documents to collections
print("\nAssigning documents to collections...")
for col_name, filenames in doc_mapping.items():
    col_id = next((c["id"] for c in cols if c["name"] == col_name), None)
    if not col_id:
        print(f"  Collection {col_name} not found")
        continue

    for doc in docs:
        if doc["filename"] in filenames:
            doc_id = doc["id"]
            update_resp = requests.put(f"{BASE_URL}/documents/{doc_id}", json={"collection_id": col_id})
            if update_resp.status_code == 200:
                print(f"  Assigned {doc['filename']} -> {col_name}")
            else:
                print(f"  Failed {doc['filename']}: {update_resp.text}")

print("\n=== Setup Complete ===")

# Verify
resp = requests.get(f"{BASE_URL}/collections")
cols = resp.json()
for c in cols:
    print(f"  {c['name']}: {c['document_count']} documents, is_default: {c['is_default']}")