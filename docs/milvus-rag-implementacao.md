# Milvus RAG - Implementacao e Otimizacao

## Setup e Instalacao

### Milvus Lite (Desenvolvimento Local)

```bash
pip install pymilvus
```

```python
from pymilvus import Milvus

client = Milvus(
    uri="milvus_local.db",  # Arquivo local SQLite
    auto_id=True
)
```

### Milvus Standalone (Docker)

```yaml
# docker-compose.yml
version: '3.8'
services:
  etcd:
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
    volumes:
      - etcd_data:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    image: minio/minio:latest
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - minio_data:/minio
    command: minio server /minio

  milvus:
    image: milvusdb/milvus:v2.3.0
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - milvus_data:/var/lib/milvus
    depends_on:
      - etcd
      - minio

volumes:
  etcd_data:
  minio_data:
  milvus_data:
```

---

## Integracao com LangChain

### Instalacao

```bash
pip install langchain langchain-community pymilvus
```

### Document Loader e Chunking

```python
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus

# Carregar documentos
loader = PyPDFLoader("documento.pdf")
documents = loader.load()

# Chunking
splitter = RecursiveCharacterTextSplitter(
    chunk_size=600,
    chunk_overlap=80,
    length_function=len
)
chunks = splitter.split_documents(documents)

# Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"}
)

# Conectar ao Milvus
vectorstore = Milvus.from_documents(
    documents=chunks,
    embedding=embeddings,
    connection_args={"host": "localhost", "port": "19530"},
    collection_name="support_docs"
)
```

### Retrieval e Query

```python
# Retrieval simples
results = vectorstore.similarity_search(
    query="Como reiniciar o servico?",
    k=4
)

# Retrieval com scores
results_with_scores = vectorstore.similarity_search_with_score(
    query="Erro 401",
    k=4
)

# Retrieval por ID
result = vectorstore.get_by_id("chunk_id_123")
```

---

## Multi-Agent RAG com Milvus

### Arquitetura de Agentes

```
                    ┌─────────────┐
                    │  Router     │
                    │  (LLM)      │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  Suporte    │ │  Database   │ │   DevOps    │
    │   Agent     │ │   Agent     │ │   Agent     │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ Collection  │ │ Collection  │ │ Collection  │
    │  Suporte    │ │  Database   │ │  DevOps     │
    └─────────────┘ └─────────────┘ └─────────────┘
```

### Implementacao

```python
class AgentRouter:
    def __init__(self, vectorstore: Milvus):
        self.vectorstore = vectorstore
        self.agents = {
            "suporte": self._create_agent("suporte_docs", self.prompt_suporte),
            "database": self._create_agent("database_docs", self.prompt_database),
            "devops": self._create_agent("devops_docs", self.prompt_devops),
        }
        self.default_agent = self._create_agent("general_docs", self.prompt_general)

    def route(self, query: str) -> str:
        """Usa LLM para determinar qual agente deve responder"""
        prompt = f"Classifique a pergunta: {query}\nOpcoes: suporte, database, devops, general"
        # Chamada ao LLM para classificacao
        classification = llm.generate(prompt)
        return classification.strip().lower()

    def query(self, question: str) -> dict:
        agent_name = self.route(question)
        agent = self.agents.get(agent_name, self.default_agent)
        return agent.invoke(question)
```

---

## Otimizacao de Performance

### 1. Batch Insert

```python
# Insersao em lote para melhor performance
batch_size = 1000
for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    collection.insert(batch)
collection.flush()
```

### 2. Index After Bulk Load

```python
# Carregar dados primeiro, depois criar index
collection.insert(all_chunks)
collection.flush()
collection.build_index({"type": "IVF_FLAT", "params": {"nlist": 1024}})
```

### 3. Connection Pooling

```python
from pymilvus import connections

# Pool de conexoes para alta performance
connections.connect(
    alias="default",
    host="localhost",
    port="19530",
    pool_size=10,
    wait_timeout=30
)
```

### 4. Async Operations

```python
import asyncio
from pymilvus import AsyncMilvus

async def bulk_insert_async(collection, chunks):
    tasks = []
    for chunk in chunks:
        task = collection.insert_async(chunk)
        tasks.append(task)
    await asyncio.gather(*tasks)
    await collection.flush_async()
```

---

## Gestao de Collections

### Listar Collections

```python
from pymilvus import utility

collections = utility.list_collections()
# ['support_docs', 'database_docs', 'devops_docs']
```

### Drop Collection

```python
utility.drop_collection("temp_chunks")
```

### Estatisticas

```python
stats = collection.stats()
# {'row_count': 15000, 'indexes': [...]}
```

---

## Backup e Restore

### Export Collection Data

```python
import json

def export_collection(collection, output_file):
    data = collection.query(
        expr="id >= 0",
        output_fields=["id", "document_id", "chunk_text", "embedding"]
    )
    with open(output_file, 'w') as f:
        json.dump(data, f)
```

### Import Collection Data

```python
def import_collection(collection, input_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    collection.insert(data)
    collection.flush()
```

---

## Troubleshooting

### Problemas Comuns

| Problema | Causa | Solucao |
|----------|-------|---------|
| **Conexao recusada** | Servico nao esta rodando | `docker-compose up -d` |
| **Consulta lenta** | Index nao construido | `collection.build_index()` |
| **Memoria cheia** | Muitos vetores em memoria | Usar IVF_SQ8 com compressao |
| **Timeout** | Rede ou query complexa | Reduzir `nprobe` ou `limit` |

### Checagem de Saude

```python
from pymilvus import connections

def check_health():
    try:
        connections.connect("default", host="localhost", port="19530")
        print("Milvus esta online")
        return True
    except Exception as e:
        print(f"Erro: {e}")
        return False
```

---

## Production Checklist

- [ ] Milvus em modo cluster (nao standalone)
- [ ] Index construido apos carga de dados
- [ ] Connection pooling configurado
- [ ] Monitoring (Prometheus/Grafana)
- [ ] Backup regular de dados
- [ ] Alta disponibilidade (replicas)
- [ ] TTL policy para dados antigos
- [ ] Query timeout configurado

---

## Referencias

- [LangChain Milvus Integration](https://python.langchain.com/docs/integrations/vectorstores/milvus)
- [Milvus Performance Tuning](https://milvus.io/docs/tuning.md)
- [RAG with LangChain and Milvus](https://github.com/milvus-io/bootcamp)