# Milvus RAG - Avaliacao e Melhores Praticas

## Metricas de Avaliacao RAG

### 1. Retrieval Metrics

#### Precision@K

Proporcao de documentos relevantes nos K primeiros resultados.

```
Precision@K = (Relevantes nos top K) / K
```

#### Recall@K

Proporcao de documentos relevantes recuperados.

```
Recall@K = (Relevantes nos top K) / (Total de Relevantes)
```

#### MRR (Mean Reciprocal Rank)

Media do inverso do rank da primeira resposta relevante.

```python
def calculate_mrr(ranks: list[int]) -> float:
    return sum(1/rank for rank in ranks) / len(ranks)
```

#### NDCG (Normalized Discounted Cumulative Gain)

Avalia ranking considerando relevancia em multiplos niveis.

---

### 2. Generation Metrics

#### Faithfulness

Grau em que a resposta generada e suportada pelo contexto recuperado.

```python
def faithfulness_score(response: str, contexts: list[str]) -> float:
    # Verificar quantas afirmacoes da resposta estao no contexto
    claims = extract_claims(response)
    supported = sum(1 for c in claims if any(c in ctx for ctx in contexts))
    return supported / len(claims) if claims else 1.0
```

#### Answer Relevancy

Quao relevante e a resposta para a pergunta feita.

```python
def answer_relevancy(response: str, question: str) -> float:
    # Embed question and response, calculate similarity
    q_emb = embed(question)
    r_emb = embed(response)
    return cosine_similarity(q_emb, r_emb)
```

---

## Framework RAGAS

### Instalacao e Uso

```bash
pip install ragas
```

### Avaliacao Completa

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)

# Preparar dataset
eval_dataset = [
    {
        "question": "Como reiniciar o servico?",
        "answer": "Vá em admin > serviços > reiniciar.",
        "contexts": ["docs/admin.md", "docs/servicos.md"],
        "ground_truth": "Acesse o painel admin, va para serviços e clique em reiniciar."
    }
]

# Avaliar
result = evaluate(
    eval_dataset,
    metrics=[
        faithfulness,
        answer_relevancy,
        context_precision,
        context_recall
    ]
)

print(result)
```

---

## Avaliacao Manual

### Checklist de Qualidade

| Criterio | Pergunta | Score (1-5) |
|----------|----------|-------------|
| Acuracia | A resposta esta correta? | |
| Completeza | A resposta cobre toda a pergunta? | |
| Fonte | A resposta cita as fontes corretas? | |
| Clareza | A resposta e compreensivel? | |
| Concisao | A resposta nao tem informacao desnecessaria? | |

### Planilha de Avaliacao

```markdown
| Pergunta | Resposta | Acuracia | Fontes | Feedback |
|----------|----------|----------|--------|----------|
| Como fazer X? | ... | 4/5 | OK | ... |
| O que e Y? | ... | 3/5 | Parcial | ... |
```

---

## Testes de Regressao

### Dataset de Validação

Manter um dataset de pelo menos 20 perguntas criticas que devem funcionar corretamente.

```python
regression_tests = [
    {
        "id": 1,
        "question": "Como reiniciar o API Gateway?",
        "expected_sources": ["runbook-api-gateway.md"],
        "expected_keywords": ["reiniciar", "servico"]
    },
    {
        "id": 2,
        "question": "Qual o SLA para SEV1?",
        "expected_sources": ["sla-escalonamento.md"],
        "expected_keywords": ["15 minutos", "SLA"]
    },
    # ... mais testes
]
```

### Automacao de Testes

```python
def run_regression_tests(vectorstore, llm, tests):
    results = []
    for test in tests:
        docs = vectorstore.similarity_search(test["question"], k=3)
        response = llm.generate(f"Pergunta: {test['question']}\nContexto: {docs}")

        passed = (
            any(src in test["expected_sources"] for src in get_sources(docs)) and
            any(kw in response.lower() for kw in test["expected_keywords"])
        )

        results.append({
            "id": test["id"],
            "passed": passed,
            "question": test["question"]
        })

    return results
```

---

## A/B Testing de Configuracoes

### Variaveis para Testar

| Variavel | Opcoes | Impacto |
|----------|--------|---------|
| Chunk size | 300, 600, 1000 | Recall vs Latencia |
| Overlap | 0, 50, 100, 200 | Continuidade vs Ruido |
| Embedding model | MiniLM, BGE, E5 | Precisao vs Velocidade |
| Top-K retrieval | 3, 5, 10, 20 | Precisao vs Contexto |
| Index type | IVF, HNSW, ANNOY | Velocidade vs Precisao |

### Script de A/B Test

```python
def ab_test(base_config, variants):
    results = {}
    for name, config in variants.items():
        # Setup com config
        vs = setup_vectorstore(config)
        # Run test queries
        metrics = evaluate_queries(vs, test_queries)
        results[name] = metrics

    # Comparar
    for name, metrics in results.items():
        print(f"{name}: Recall={metrics['recall']:.3f}, Latency={metrics['latency']:.2f}s")

    return results
```

---

## Monitoramento Continuo

### Dashboard de Metrics

```python
class RAGMetrics:
    def __init__(self):
        self.queries = 0
        self.total_latency = 0
        self.source_citations = 0

    def record(self, latency: float, sources_found: int):
        self.queries += 1
        self.total_latency += latency
        if sources_found > 0:
            self.source_citations += 1

    def report(self):
        return {
            "total_queries": self.queries,
            "avg_latency": self.total_latency / self.queries,
            "citation_rate": self.source_citations / self.queries
        }
```

### Alertas

| Condicao | Alerta |
|----------|--------|
| Latencia > 30s | Timeout de query |
| Citation rate < 80% | Retrieval falhando |
| Error rate > 5% | Sistema indisponivel |

---

## Otimizacao de Embeddings

### Fine-tuning de Embeddings

```python
from sentence_transformers import SentenceTransformer, InputExample, losses

# Treinar com dados do dominio
train_examples = [
    InputExample(texts=["query领域的例子", "领域的文档"], label=1.0),
    InputExample(texts=["unrelated query", "other topic"], label=0.0),
]

model = SentenceTransformer('all-MiniLM-L6-v2')
train_loss = losses.CosineSimilarityLoss(model)

model.fit(train_examples, epochs=10)
model.save("custom-embeddings")
```

### Avaliacao de Embeddings

```python
def evaluate_embeddings(test_cases: list[dict]) -> dict:
    """Avalia qualidade dos embeddings para o dominio"""
    correct = 0
    for case in test_cases:
        query_emb = embed(case["query"])
        doc_emb = embed(case["document"])
        similarity = cosine_similarity(query_emb, doc_emb)

        if similarity >= case["threshold"]:
            correct += 1

    return {"accuracy": correct / len(test_cases)}
```

---

## Casos de Uso Comuns

### 1. Suporte Tecnico

- Documentos: FAQs, runbooks, procedimentos
- Chunk size: 600-1000 tokens
- Embedding: all-MiniLM-L6-v2
- Top-K: 4-6

### 2. Documentacao de Codigo

- Documentos: READMEs, comentarios, especificacoes
- Chunk size: 300-500 tokens
- Overlap: 10%
- Embedding: codebert ou codellama embeddings

### 3. Base de Conhecimento Juridica

- Documentos: leis, jurisprudencias, contratos
- Chunk size: 1500-2000 tokens
- Embedding: BGE-large (1024 dim)
- Top-K: 3

---

## Checklist de Qualidade

### Pre-Deploy

- [ ] Dataset de validacao criado (20+ perguntas)
- [ ] Acuracia > 85% no dataset de validacao
- [ ] Latencia media < 10s
- [ ] Citation rate > 90%
- [ ] Testes de regressao passando

### Monitoramento

- [ ] Dashboard de metrics configurado
- [ ] Alertas de latencia/erro ativos
- [ ] Logs de queries fallhadas
- [ ] A/B testing de configs

### Melhoria Continua

- [ ]收集 feedback dos usuarios
- [ ] Atualizar dataset de validacao mensalmente
- [ ] Fine-tune embeddings trimestralmente
- [ ] Revisar chunking strategy semestralmente

---

## Referencias

- [RAGAS Documentation](https://docs.ragas.io/)
- [BEIR Benchmark](https://github.com/beir-cellar/beir)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [LangChain Evaluation](https://python.langchain.com/docs/guides/evaluation)