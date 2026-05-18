import requests

BASE_URL = "http://localhost:8011/api"

agents = [
    {
        "name": "Agente Suporte API",
        "specialty": "suporte_api",
        "collection_id": None,  # Will use SuporteAPI collection by name
        "model_name": "llama3.2:3b"
    },
    {
        "name": "Agente Database",
        "specialty": "database",
        "collection_id": None,
        "model_name": "llama3.2:3b"
    },
    {
        "name": "Agente DevOps",
        "specialty": "devops",
        "collection_id": None,
        "model_name": "llama3.2:3b"
    },
    {
        "name": "Agente Generalista",
        "specialty": "general",
        "collection_id": None,
        "model_name": "llama3.2:3b"
    }
]

print("Creating agents...")

# Get collections to map
resp = requests.get(f"{BASE_URL}/collections")
collections = {c["name"]: c["id"] for c in resp.json()}
print(f"Collections: {list(collections.keys())}")

for agent in agents:
    # Map specialty to collection
    collection_map = {
        "suporte_api": "SuporteAPI",
        "database": "Database",
        "devops": "DevOps",
        "general": None
    }

    col_name = collection_map.get(agent["specialty"])
    if col_name and col_name in collections:
        agent["collection_id"] = collections[col_name]

    print(f"\nCreating {agent['name']}...")
    resp = requests.post(f"{BASE_URL}/agents", json=agent)
    if resp.status_code == 200:
        print(f"  Created: {resp.json()['name']} (ID: {resp.json()['id'][:20]}...)")
    else:
        print(f"  Error: {resp.status_code} - {resp.text[:200]}")

print("\nDone!")

# Verify
resp = requests.get(f"{BASE_URL}/agents")
agents = resp.json()
print(f"\nTotal agents: {len(agents)}")
for a in agents:
    print(f"  - {a['name']} | collection: {a.get('collection_name')}")