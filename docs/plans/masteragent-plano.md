# Plano de Implementacao: MasterAgent com Agentes Especializados

## Visao Geral

Sistema RAG multiagente com MasterAgent que classifica perguntas e delega para agentes especializados, executando-os em paralelo e agregando as respostas.

## Decisoes Confirmadas

| Item | Decisao |
|------|---------|
| MasterAgent | Unico, apenas delega |
| Documents para collections | SuporteAPI, Database, DevOps |
| Modelo | llama3.2:3b (troca futura via config) |
| Frontend mostra agentes | Sim |

## Arquitetura

```
User Question
     │
     ▼
┌─────────────────────────┐
│      MasterAgent        │
│  1. Classify (LLM)      │
│  2. Identify agents     │
│  3. Delegate (parallel) │
│  4. Aggregate results   │
└───────────┬─────────────┘
            │
        ┌───┼───┐
        ▼   ▼   ▼
   ┌─────────┬─────────┬─────────┐
   │Agente   │Agente   │Agente   │
   │Suporte  │Database │DevOps   │
   │  API    │ Expert  │ Expert  │
   └────┬────┘────┬────┘────┬────┘
        │         │         │
        └─────────┼─────────┘
                  │ (parallel)
                  ▼
        ┌─────────────────────────┐
        │     MasterAgent        │
        │   (aggregate + format) │
        └─────────────────────────┘
                  │
                  ▼
            User Response
```

## Collections e Documents

| Collection | Documents |
|------------|-----------|
| SuporteAPI | faq-autenticacao.md, runbook-api-gateway.md, sla-escalonamento.md |
| Database | troubleshooting-postgres.txt, incidente-cache-2026-04-18.md |
| DevOps | procedimento-rollback.md, release-checklist.md, observabilidade-alertas.md |

## Estrutura de Arquivos

```
backend/app/agents/
├── __init__.py
├── base_agent.py          # Classe abstrata BaseAgent e AgentResult
├── master_agent.py       # Orquestrador MasterAgent
├── agente_suporte.py     # AgenteSuporte (SuporteAPI)
├── agente_database.py     # AgenteDatabase
├── agente_devops.py      # AgenteDevOps
├── agente_generalista.py  # Fallback
└── classifiers.py         # LLMClassifier e KeywordClassifier
```

## Classes Principais

### AgentResult
```python
@dataclass
class AgentResult:
    answer: str
    sources: list[str]
    confidence: float
    agent_name: str
    category: str
```

### BaseAgent
```python
class BaseAgent(ABC):
    def __init__(self, name: str, category: str, collection_name: str)
    @abstractmethod
    def execute(self, question: str) -> AgentResult
    def search(self, query: str) -> list[Document]
    def format_context(self, docs: list[Document]) -> str
```

### MasterAgent
```python
class MasterAgent:
    def __init__(self)
    def classify(self, question: str) -> list[str]
    def needs_clarifying(self, categories: list[str]) -> bool
    def delegate_parallel(self, question: str, categories: list[str]) -> dict
    def aggregate(self, results: dict) -> AskResponse
    def ask(self, question: str, force_agent: str = None) -> AskResponse
```

### LLMClassifier
```python
CLASSIFY_PROMPT = """
Analise a pergunta e identifique TODAS as areas relevantes.

Areas:
- suporte_api: erros HTTP, auth, gateway, runbooks
- database: postgres, redis, conexoes, queries
- devops: deploy, rollback, CI/CD, monitoramento

Regras:
- Pergunta pode ter multiplas areas
- Se ambigua, responda "clarifying"
- Se nenhuma relevante, responda "general"

Pergunta: {question}

Responda apenas a lista de categorias separadas por virgulas.
"""
```

## Fluxo de Classificacao

1. Recebe pergunta do usuario
2. Envia para LLM com prompt de classificacao
3. LLM retorna lista de categorias (ex: "suporte_api,database")
4. Se "clarifying" -> pede esclarecimento
5. Se vazio -> usa "general"
6. Filtra categorias validas
7. Delegua para agentes relevantes

## Fluxo de Resposta

1. Se `force_agent` definido -> usa apenas esse agente
2. Classifica a pergunta
3. Executa agentes em paralelo via ThreadPoolExecutor
4. Agrega respostas e fontes
5. Retorna com `agent_used` como lista de nomes

## API Modifications

### AskRequest
```python
class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    top_k: int = Field(default=4, ge=1, le=10)
    mode: str = Field(default="auto", pattern="^(baseline|multiagent|auto)$")
    force_agent: str = Field(default=None)  # suporte_api, database, devops
```

### AskResponse (atualizado)
```python
class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    agent_used: list[str]  # Agora lista
    steps: list[str]
    needs_clarifying: bool = False
```

## Frontend - Chat Page

### Mudancas
1. Toggle modes: "Baseline" | "Auto (MasterAgent)" | "Multiagent"
2. Dropdown "Forcar agente" - opcional
3. Mostrar badges dos agentes que responderam
4. Exibir "needs_clarifying" message

### UI Agent Badges
```typescript
{response.agent_used.map(agent => (
  <span className="px-2 py-1 rounded-full bg-purple-500/20 text-purple-400 text-xs">
    {agent}
  </span>
))}
```

## Implementacao por Fase

### FASE 1: Reorganizar Collections e Documents
- Criar 3 collections: SuporteAPI, Database, DevOps
- Mover documents existentes para collections corretas
- Atualizar CollectionResponse com document_count

### FASE 2: BaseAgent e AgentResult
- dataclass AgentResult
- Classe abstrata BaseAgent
- Metodo format_context()

### FASE 3: Classifiers
- LLMClassifier com prompt
- KeywordClassifier como fallback
- MasterAgent integration

### FASE 4: Agentes Especializados
- AgenteSuporte (SuporteAPI)
- AgenteDatabase
- AgenteDevOps
- AgenteGeneralista (fallback)

### FASE 5: MasterAgent
- classify()
- needs_clarifying()
- delegate_parallel()
- aggregate()
- ask()

### FASE 6: API Integration
- Modificar AskRequest com force_agent
- Modificar routes.py
- Integrar MasterAgent

### FASE 7: Frontend Updates
- Novos modes no toggle
- Dropdown forcar agente
- Agent badges
- Clarifying handling

## Performance

```
Sequencial: Classifier (2s) + Agent1 (10s) + Agent2 (10s) = ~22s
Paralelo:    Classifier (2s) + max(Agent1, Agent2) (10s) = ~12s
```

## Validacao

Testar com:
1. Pergunta simples (1 area): "Como resolver erro 401?"
2. Multi-area: "Deploy afetou o banco" -> SuporteAPI + Database
3. Forcar agente: Selecionar "Database" manual
4. Clarifying: Pergunta ambigua
5. General: Duvida fora das areas

## Tempo Total Estimado

| Fase | Tempo |
|------|-------|
| 1 | 30 min |
| 2 | 30 min |
| 3 | 30 min |
| 4 | 2 horas |
| 5 | 1 hora |
| 6 | 1 hora |
| 7 | 1 hora |
| **Total** | **~7 horas** |