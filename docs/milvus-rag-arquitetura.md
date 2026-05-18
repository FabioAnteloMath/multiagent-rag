# Milvus RAG - Fundamentos e Arquitetura

## O que e Milvus?

Milvus e um banco de dados vetorial de codigo aberto projetado para aplicacoes de busca por similaridade e ML/AI. Ele permite armazenar, indexar e buscar em grandes volumes de embeddings vetoriais de forma eficiente.

### Caracteristicas Principais

| Caracteristica | Descricao |
|----------------|-----------|
| Banco de dados vetorial | Otimizado para buscas por similaridade em espaco n-dimensional |
| Escalabilidade | Suporta bilhoes de vetores |
| Indexacao avancada | IVF, HNSW, ANNs para busca eficiente |
| Multi-modal | Suporta dados de texto, imagens, audio |
| Kubernetes | Pronto para implantacao em nuvem |

---

## Arquitetura Milvus

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                      Milvus Cluster                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │
│  │ Proxy   │  │ Coord   │  │  Data   │  │ Query   │         │
│  │ (gRPC)  │  │(Meta)   │  │ Node    │  │ Node    │         │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘         │
│       │            │            │            │               │
│       └────────────┴────────────┴────────────┘               │
│                          │                                   │
│              ┌───────────┴───────────┐                       │
│              │    Object Storage     │                       │
│              │   (MinIO/S3/Azure)    │                       │
│              └───────────────────────┘                       │
└─────────────────────────────────────────────────────────────┘
```

### Modos de Implantacao

| Modo | Uso | Recursos |
|------|-----|----------|
| **Milvus Lite** | Desenvolvimento local, prototipos | SQLite local, zero configuracao |
| **Milvus Standalone** | Homologacao, pequenas producoes | Todos os componentes em um servidor |
| **Milvus Cluster** | Producao em larga escala | K8s, shards, replicas |

---

## Integracao RAG com Milvus

### Pipeline RAG com Milvus

```
┌──────────┐    ┌───────────┐    ┌─────────┐    ┌────────┐    ┌────────┐
│ Document │ -> │ Chunking  │ -> │ Embed   │ -> │ Store  │ -> │  RAG   │
│          │    │          │    │dings    │    │ Milvus │    │ Query  │
└──────────┘    └───────────┘    └─────────┘    └────────┘    └────────┘
                                                             │
                                                             v
                                                         ┌────────┐
                                                         │  LLM   │
                                                         │ Response│
                                                         └────────┘
```

### Por que Milvus para RAG?

1. **Performance**: Indices vetoriais permitem busca em milhoes de documentos em milissegundos
2. **Escalabilidade**: Cresce horizontalmente conforme base de conhecimento aumenta
3. **Flexibilidade**: Suporta multiplos tipos de embeddings e metricas de similaridade
4. **Custo-beneficio**: Versao open source com opcoes gerenciadas (Zilliz Cloud)

---

## Tipos de Index no Milvus

### IVF (Inverted File)

```
┌──────────────────────────────────────────┐
│           Base Embeddings                │
│  [0.1, 0.2, ...] [0.3, 0.4, ...] ...    │
└──────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────┐
│          IVF Index (Centroids)           │
│     [C1]    [C2]    [C3]    [C4]        │
│      │       │       │       │          │
│    [p1,p2] [p3]    [p4]    [p5,p6]      │
└──────────────────────────────────────────┘
```

- **IVF_FLAT**: Busca exaustiva nos clusteres - melhor precisao
- **IVF_SQ8**: Compressao quantizada - menor memoria
- **IVF_PQ**: Quantizacao produto - maior velocidade

### HNSW (Hierarchical Navigable Small World)

```
Nivel 2:    [A]────────[B]─────────────────[C]
                │         │                   │
Nivel 1:    [A]───[D]───[B]───[E]─────────[C]
                │         │         │           │
Nivel 0:    [A]─[D]─[F]─[B]─[E]─[G]─────[C]
```

- Grafos hierarquicos para busca aproximada
- Maior velocidade com boa precisao
- Maior consumo de memoria

### Metric Types

| Metrica | Uso |
|---------|-----|
| **L2** | Distancia euclidiana - comum para imagens |
| **IP** | Produto interno - melhor para vetores normalizados |
| **COSINE** | Similaridade cosseno - texto |

---

## Schema e Collections no Milvus

### Definicao de Schema

```python
from pymilvus import connections, Collection, CollectionSchema, FieldSchema

# Definicao de campos
fields = [
    FieldSchema(name="id", dtype=DataType.INT64, is_primary=True),
    FieldSchema(name="document_id", dtype=DataType.VARCHAR, max_length=256),
    FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
    FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=384),
    FieldSchema(name="page", dtype=DataType.INT32),
]

schema = CollectionSchema(
    fields=fields,
    description="RAG document chunks",
    enable_dynamic_fields=True
)
```

### Parametros de Index

```python
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_FLAT",
    "params": {"nlist": 128}
}
```

---

## Operacoes CRUD no Milvus

### Inserir Dados

```python
from pymilvus import connections, Collection

connections.connect("default", host="localhost", port="19530")

collection = Collection("support_docs")
collection.insert([
    [1, 2, 3],  # ids
    ["doc1", "doc2", "doc3"],  # document_ids
    ["texto chunk 1", "texto chunk 2", "texto chunk 3"],  # chunk_text
    [[0.1]*384, [0.2]*384, [0.3]*384],  # embeddings
    [1, 1, 2]  # page
])

collection.flush()
```

### Buscar por Similaridade

```python
search_params = {
    "metric_type": "L2",
    "params": {"nprobe": 10}
}

results = collection.search(
    data=[query_embedding],
    anns_field="embedding",
    param=search_params,
    limit=top_k,
    expr=None,
    output_fields=["chunk_text", "document_id", "page"]
)
```

---

## Boas Praticas para RAG com Milvus

### 1. Chunking Otimo

| Tipo de Dado | Tamanho Recomendado | Overlap |
|--------------|---------------------|---------|
| Documentos tecnicos | 500-1000 tokens | 10-20% |
| Codigo fonte | 200-500 tokens | 5-10% |
| Artigos longos | 800-1500 tokens | 15-20% |

### 2. Choice de Embedding

| Modelo | Dimensão | Uso Recomendado |
|--------|----------|----------------|
| **all-MiniLM-L6-v2** | 384 | Geral, baixo custo |
| **BGE-large** | 1024 | Maior precisao |
| **e5-large-v2** | 1024 | Busca semantica |

### 3. Configuracao de Index

```python
# Para colecoes pequenas (<100k chunks)
index_params = {
    "metric_type": "L2",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200}
}

# Para colecoes grandes (>100k chunks)
index_params = {
    "metric_type": "L2",
    "index_type": "IVF_SQ8",
    "params": {"nlist": 1024}
}
```

---

## Comparacao: Milvus vs Alternatives

| Aspecto | Milvus | ChromaDB | FAISS | Pinecone |
|---------|--------|----------|-------|----------|
| **Tipo** | Produtivo | Embedding-only | Library | Cloud |
| **Escalabilidade** | Muito alta | Media | Alta | Muito alta |
| **Instalacao** | Complexa | Simples | Library | SaaS |
| **Custo** | Open source | Grátis | Grátis | Pago |
| **Consistencia** | Transacional | Eventual | Eventual | Eventual |
| **Use case** | Enterprise | Prototipo | Batch search | Cloud-native |

---

## RAG Evaluation Metrics

### Recall@K

```
Recall@K = (Documentos relevantes nos top K) / (Total de documentos relevantes)
```

### Mean Reciprocal Rank (MRR)

```
MRR = (1/N) * sum(1/rank_i)
```

### Normalized Discounted Cumulative Gain (NDCG)

Considera posicao e relevancia dos resultados.

---

## Referencias

- [Milvus Documentation](https://milvus.io/docs)
- [RAG with Milvus](https://github.com/milvus-io/bootcamp/blob/master/docs/en/tutorials)
- [Vector Search Best Practices](https://milvus.io/docs/tips.md)