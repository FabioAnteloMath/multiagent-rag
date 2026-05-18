# Plano de Implementacao - Melhorias Multiagent RAG

## Visao Geral do Projeto

Sistema RAG com gerenciador de documentos, collections, agentes especializados e frontend moderno.

---

## 1. Gerenciamento de Documentos

### 1.1 Funcionalidades

| Funcionalidade | Descricao |
|----------------|-----------|
| Upload | Arrastar/selecionar arquivos PDF, MD, TXT |
| Visualizacao | Ler conteudo de documentos indexados |
| Processamento | Chunking, embedding e indexacao |
| Edicao/Exclusao | Remover documentos ou chunks individuais |
| Status | Visualizar estado de processamento |

### 1.2 API Endpoints

```
GET    /api/documents              - Listar todos os documentos
GET    /api/documents/{id}          - Detalhes de um documento
POST   /api/documents/upload        - Upload de novo documento
DELETE /api/documents/{id}         - Excluir documento
GET    /api/documents/{id}/chunks   - Listar chunks de um documento
DELETE /api/documents/{id}/chunks/{chunk_id} - Excluir chunk
POST   /api/documents/{id}/reprocess - Reprocessar documento
GET    /api/documents/{id}/status   - Status de processamento
```

---

## 2. Collections

### 2.1 Conceito

Agrupamentos logicos de documentos para organizacao e busca segmentada.

### 2.2 API Endpoints

```
GET    /api/collections             - Listar collections
POST   /api/collections             - Criar collection
GET    /api/collections/{id}        - Detalhes
PUT    /api/collections/{id}        - Atualizar
DELETE /api/collections/{id}        - Excluir
POST   /api/collections/merge        - Merge de collections
GET    /api/collections/{id}/documents - Docs da collection
```

---

## 3. Multiagentes Especializados

### 3.1 Arquitetura

```
Base de Conhecimento
    |
    +-- Collection "Suporte API" --> Agente SuporteAPI
    +-- Collection "Database" --> Agente DatabaseExpert
    +-- Collection "DevOps" --> Agente DevOpsExpert
    +-- Collection "Geral" --> Agente Generalista
    |
    v
Router de Agentes --> Identifica area --> Encaminha para agente correto
```

### 3.2 Agentes

| Agente | Collection | Specialty |
|--------|------------|-----------|
| SuporteAPI | suporte-api | Erros 401/403/5xx, debugging |
| DatabaseExpert | database | Postgres, queries, troubleshooting |
| DevOpsExpert | devops | Deploy, CI/CD, rollback |
| Generalista | default | Suporte geral |

### 3.3 API Endpoints

```
GET    /api/agents                 - Listar agentes
POST   /api/agents                 - Criar agente
GET    /api/agents/{id}            - Detalhes
PUT    /api/agents/{id}            - Atualizar
DELETE /api/agents/{id}            - Remover
PUT    /api/agents/{id}/collection  - Associar collection
GET    /api/agents/{id}/stats      - Estatisticas
```

---

## 4. Base de Dados

### 4.1 Solucao: SQLite + ChromaDB

- **SQLite**: Metadados (documents, collections, agents, chunks)
- **ChromaDB**: Vetores para busca semantica

### 4.2 Schema SQLite

```sql
-- Documents
CREATE TABLE documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'pending',
    collection_id TEXT
);

-- Chunks
CREATE TABLE chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER,
    embedding_status TEXT DEFAULT 'pending'
);

-- Collections
CREATE TABLE collections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agents
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    specialty TEXT,
    system_prompt TEXT,
    collection_id TEXT,
    model_name TEXT
);

-- Processing Log
CREATE TABLE processing_log (
    id TEXT PRIMARY KEY,
    document_id TEXT,
    status TEXT,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 5. Frontend

### 5.1 Stack

| Tecnologia | Motivo |
|------------|--------|
| **Next.js 14+** | Framework moderno, React |
| **Tailwind CSS** | Design minimalista, responsivo |
| **shadcn/ui** | Componentes customizaveis |
| **Framer Motion** | Animacoes suaves |
| **Zustand** | Estado global simples |

### 5.2 Design System

**Dark Mode:**
- Background: #0f172a
- Surface: #1e293b
- Border: #334155
- Text Primary: #f1f5f9
- Accent: #3b82f6

### 5.3 Paginas

```
/                    - Dashboard
/documents           - Gerenciamento de documentos
/documents/[id]      - Detalhes do documento
/collections         - Listar collections
/collections/[id]    - Detalhes da collection
/agents              - Gerenciar agentes
/chat                - Chat com toggle de agentes
```

---

## 6. Estrutura de Pastas

```
multiagent-rag/
├── backend/
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── documents.py
│   │   │   ├── collections.py
│   │   │   ├── agents.py
│   │   │   └── routes.py
│   │   ├── core/
│   │   │   ├── database.py
│   │   │   └── config.py
│   │   ├── models/
│   │   │   ├── document.py
│   │   │   ├── collection.py
│   │   │   └── agent.py
│   │   ├── services/
│   │   │   ├── document_service.py
│   │   │   ├── vector_service.py
│   │   │   └── agent_router.py
│   │   └── main.py
│   └── requirements.txt
├── frontend/
│   ├── app/
│   ├── components/
│   └── package.json
└── data/
    ├── docs/
    ├── chroma/
    └── db/
```

---

## 7. Dependencias

```txt
# Backend
sqlalchemy>=2.0
chromaadb>=0.4.0
python-multipart>=0.0.6
aiofiles>=23.0.0

# Frontend
next>=14.0
react>=18.0
tailwindcss>=3.4
@shadcn/ui>=0.5
framer-motion>=10.0
zustand>=4.0
```

---

## 8. Ordem de Implementacao

1. **Fase 1**: Schema SQLite + Models + CRUD Documents
2. **Fase 2**: Collections CRUD + Upload
3. **Fase 3**: Agentes e Router
4. **Fase 4**: Frontend Next.js - Layout e Pages
5. **Fase 5**: Chat e integracao