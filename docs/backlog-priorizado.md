# Backlog Priorizado - Copiloto de Suporte Tecnico

## P0 (obrigatorio para MVP)
1. Configurar ambiente Python + FastAPI basico.
2. Configurar Ollama e validar inferencia local.
3. Implementar ingestao de documentos (PDF/MD/TXT).
4. Implementar chunking e indexacao no Milvus Lite.
5. Implementar endpoint POST /ask com RAG baseline.
6. Retornar citacoes de fonte em toda resposta.
7. Criar UI minima para chat.
8. Criar conjunto de 20 perguntas de validacao.
9. Medir latencia e taxa de respostas com fonte.
10. Documentar setup e execucao no README.

## P1 (forte diferencial de portfolio)
1. Implementar fluxo multiagente (planner, retriever, answerer/critic).
2. Toggle baseline vs multiagente na UI.
3. Logging estruturado de pipeline (etapas e tempos).
4. Reindexacao incremental (somente novos docs).
5. Testes unitarios para chunking e retrieval.

## P2 (fase seguinte)
1. Avaliacao automatica com RAGAS.
2. OCR opcional para PDFs escaneados.
3. Cache de respostas para perguntas repetidas.
4. Deploy gratuito (Hugging Face Spaces/Render/Railway).
5. Dashboard simples de qualidade.

## Definicao de Pronto (DoD)
- Funcional: historia executa ponta a ponta sem ajuste manual.
- Tecnico: logs minimos e tratamento de erros principais.
- Qualidade: ao menos 1 teste de validacao por item critico.
- Documentacao: instrucoes objetivas para reproduzir localmente.

## Plano de Entregas por Bloco
- Bloco A (Dias 1-2): P0 itens 1-4.
- Bloco B (Dias 3-4): P0 itens 5-6.
- Bloco C (Dia 6): P0 item 7.
- Bloco D (Dia 7): P0 itens 8-10.
- Bloco E (extra): P1 itens 1-3.
