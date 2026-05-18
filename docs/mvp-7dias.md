# MVP 7 Dias - Copiloto de Suporte Tecnico (RAG + Multiagente)

## Objetivo do MVP
Construir um assistente de suporte tecnico que responde perguntas com base em documentos (manuais, FAQs, runbooks) e sempre cita a fonte. O sistema deve rodar localmente e ter custo proximo de zero.

## Problema que o MVP resolve
Times de suporte perdem tempo procurando informacoes em bases dispersas. O copiloto acelera o troubleshooting com respostas contextualizadas e rastreaveis.

## Escopo Fechado
- Ingestao de documentos PDF/MD/TXT.
- Indexacao vetorial em Milvus Lite.
- Pipeline RAG com LangChain.
- LLM local via Ollama.
- API backend simples com FastAPI.
- UI web minima para pergunta/resposta.
- Citacao de fontes (arquivo e pagina/secao).
- Modo baseline (single-agent) e modo multiagente inicial.

## Fora do Escopo (nesta semana)
- Autenticacao complexa.
- Deploy em cloud pago.
- Fine-tuning de modelo.
- OCR avancado para PDFs escaneados ruins.

## Stack Tecnica (baixo custo)
- Backend: Python 3.11 + FastAPI
- Orquestracao IA: LangChain + LangGraph
- Vetor DB: Milvus Lite (arquivo local)
- Embeddings: sentence-transformers (all-MiniLM-L6-v2)
- LLM local: Ollama (llama3.2:3b ou mistral:7b)
- Frontend: React + Vite (ou Streamlit para versao ultrarapida)
- Avaliacao: RAGAS (fase 2)

## Estrutura Sugerida

```text
multiagent-rag/
  backend/
    app/
      api/
      core/
      services/
      agents/
      tests/
    requirements.txt
  frontend/
  data/
    docs/
    milvus/
    eval/
  docs/
    mvp-7dias.md
    backlog-priorizado.md
```

## Cronograma - 7 Dias

### Dia 1 - Fundacao do projeto
- Criar estrutura de pastas e ambiente Python.
- Subir FastAPI com endpoint healthcheck.
- Configurar Ollama local e testar modelo.
- Definir 20 perguntas de negocio para validacao.

Criterio de pronto:
- API rodando local.
- Modelo local respondendo prompt simples.

### Dia 2 - Ingestao e indexacao
- Implementar loaders (PDF/MD/TXT).
- Aplicar chunking com RecursiveCharacterTextSplitter.
- Gerar embeddings e persistir no Milvus Lite.
- Criar script de reindexacao.

Criterio de pronto:
- Documentos indexados e recuperacao por similaridade funcionando.

### Dia 3 - Pipeline RAG baseline
- Implementar fluxo retrieve -> generate.
- Exibir fontes no retorno (nome do arquivo e referencia).
- Ajustar top-k inicial e prompt base.

Criterio de pronto:
- 70%+ das respostas das 20 perguntas com contexto correto.

### Dia 4 - API de produto
- Endpoints:
  - POST /ingest
  - POST /ask
  - GET /metrics
- Tratar erros comuns (sem resultados, docs vazios, timeout).
- Adicionar logging de latencia.

Criterio de pronto:
- Fluxo completo por API, com resposta e citacao.

### Dia 5 - Multiagente v1
- Implementar 3 papeis no LangGraph:
  - Planner: classifica tipo de pergunta.
  - Retriever: busca contexto e faz rerank simples.
  - Answerer/Critic: responde e valida suporte em fonte.
- Fallback para baseline quando necessario.

Criterio de pronto:
- Multiagente funcionando em pelo menos 10 perguntas complexas.

### Dia 6 - Frontend e UX minima
- Criar tela de chat simples.
- Mostrar resposta + fontes + tempo de resposta.
- Alternar entre modo baseline e multiagente.

Criterio de pronto:
- Demo navegavel ponta a ponta.

### Dia 7 - Qualidade e divulgacao
- Rodar avaliacao manual com 20 perguntas.
- Registrar tabela comparativa baseline vs multiagente.
- Finalizar README com arquitetura, setup e resultados.
- Gravar video curto de demo (2-4 min).

Criterio de pronto:
- Projeto publicavel com evidencia de qualidade.

## Metricas Minimas do MVP
- Taxa de resposta com fonte: >= 90%
- Latencia media por pergunta: <= 8s local
- Precisao percebida (avaliacao manual): >= 75%

## Riscos e Mitigacoes
- Hardware limitado para LLM:
  - Mitigar usando modelo menor (3b) e contexto curto.
- Qualidade fraca da recuperacao:
  - Ajustar chunk_size/overlap/top-k e validar por amostra.
- Dados de suporte inconsistentes:
  - Normalizar documentos e remover duplicidade.
