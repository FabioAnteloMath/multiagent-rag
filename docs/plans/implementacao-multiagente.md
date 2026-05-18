# Plano de Implementacao - Multiagent RAG

## Analise do Estado Atual

### O que ja existe (OK)
- Backend FastAPI com `/health`, `/ingest`, `/ask`
- Pipeline RAG baseline funcional (FAISS como backend padrao)
- LLM via Ollama com `llama3.2:3b`
- Embeddings com `all-MiniLM-L6-v2`
- 8 documentos de suporte ja disponiveis em `data/docs/`
- 15 perguntas de baseline em `data/eval/perguntas-baseline.md`
- Estrutura de diretorios pronta para multiagente

### O que falta (Prioridade)

| Prioridade | Item | Descricao |
|------------|------|-----------|
| P1 | Multiagente LangGraph | Planner -> Retriever -> Answerer com StateGraph |
| P1 | Toggle baseline/multiagente | Endpoint para comparar modos |
| P1 | Logging estruturado | Métricas de latencia e etapas |
| P2 | UI minima | Interface web para chat |
| P2 | Reindexacao incremental | Detectar apenas docs novos/modificados |
| P2 | Testes unitarios | Cobertura para chunking e retrieval |

---

## Plano Detalhado de Implementacao

### FASE 1: Multiagente com LangGraph (2 dias)

#### 1.1 Criar `backend/app/services/multiagent_service.py`

```python
# Estrutura:
# - MultiAgentState ( TypedDict com question, top_k, plan, context, answer, sources, steps )
# - Node: planner_node() - classifica tipo de pergunta e define estrategia de busca
# - Node: retriever_node() - executa busca vetorial com query refinada
# - Node: answerer_node() - gera resposta com contexto
# - Edge condicional: short question = direct answer, complex = full pipeline
# - Compilar grafo com StateGraph
```

#### 1.2 Criar `backend/app/agents/__init__.py`
- exports dos agentes

#### 1.3 Criar `backend/app/agents/state.py`
- Definicoes de estado e tipos

---

### FASE 2: Toggle Baseline vs Multiagente (1 dia)

#### 2.1 Modificar `routes.py`
- Adicionar campo `mode` no `AskRequest` (`"baseline"` | `"multiagent"`)
- Routing para pipeline correto baseado no modo

#### 2.2 Modificar `multiagent_service.py`
- Adicionar metodo `ask_multiagent()` que executa o grafo

---

### FASE 3: Logging Estruturado (0.5 dia)

#### 3.1 Criar `backend/app/core/logging_config.py`
- Configuracao de logging com formato JSON
- Campos: timestamp, request_id, question, mode, latency_ms, sources_count

#### 3.2 Integrar no RagPipeline e MultiAgentService
- Log de inicio/fim de cada etapa
- Log de latencia total

---

### FASE 4: UI minima (1 dia)

#### 4.1 Criar `backend/app/ui/index.html`
- Pagina simples com chat
- Input de pergunta
- Toggle baseline/multiagente
- Exibicao de resposta + fontes + tempo

#### 4.2 Servir UI via FastAPI
- Endpoint GET `/` que serve o HTML
- Static files para CSS/JS inline

---

### FASE 5: Reindexacao Incremental (0.5 dia)

#### 5.1 Modificar `rag_pipeline.py`
- Adicionar metodo `get_document_fingerprints()` - hash dos arquivos
- Comparar fingerprints antes de reindexar
- Reindexar apenas docs novos ou modificados

---

### FASE 6: Testes Unitarios (1 dia)

#### 6.1 Criar `backend/tests/`
- `test_chunking.py` - validar tamanhos de chunk
- `test_retrieval.py` - validar recall
- `test_multiagent.py` - validar fluxo do grafo

---

## Arquivos a Criar ou Modificar

### Novos Arquivos
```
backend/app/services/multiagent_service.py  (150 linhas)
backend/app/agents/__init__.py
backend/app/agents/state.py
backend/app/core/logging_config.py
backend/app/ui/index.html
backend/tests/test_chunking.py
backend/tests/test_retrieval.py
backend/tests/test_multiagent.py
```

### Arquivos a Modificar
```
backend/app/api/routes.py       (+30 linhas - toggle mode)
backend/app/services/rag_pipeline.py  (+50 linhas - fingerprint + incremental)
backend/app/main.py             (+10 linhas - servir UI)
backend/requirements.txt        (adicionar pytest)
```

---

## Ordem de Implementacao Sugerida

1. **multiagent_service.py** - Core do multiagente
2. **routes.py** - Toggle entre baseline e multiagente
3. **logging_config.py** - Logging para métricas
4. **rag_pipeline.py** - Reindexacao incremental
5. **UI** - Interface web simples
6. **Testes** - Cobertura basica

---

## Tempo Total Estimado

- Fase 1: 4 horas
- Fase 2: 2 horas
- Fase 3: 1 hora
- Fase 4: 2 horas
- Fase 5: 1 hora
- Fase 6: 3 horas

**Total: ~13 horas de implementacao**

---

## Dependencias Externas

- Ollama rodando na porta 11434
- Modelo `llama3.2:3b` baixado
- Python 3.11 com virtualenv ativo
- Pacotes: ja instalados no requirements.txt

---

## Criterios de Validacao

Apos implementacao, o sistema deve:
1. Responder perguntas via `/api/ask` com `mode=multiagent`
2. Retornar campo `agent_used` indicando qual pipeline foi usado
3. Logar latencia e etapas em formato estruturado
4. UI web funcional em `http://127.0.0.1:8000/`
5. Reindexacao detectar apenas docs novos (sem reindexar tudo)