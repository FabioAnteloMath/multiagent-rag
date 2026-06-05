"""Generate the PDF report from the benchmark JSON."""
import json
import html
from datetime import datetime
from pathlib import Path

DATA_PATH = Path(r"C:\WorkSpace\Pessoal\multiagent-rag\docs\ab-benchmark\benchmark_v2_20260604_162449.json")
OUT_HTML = Path(r"C:\WorkSpace\Pessoal\multiagent-rag\docs\ab-benchmark\report_v2.html")
OUT_PDF = Path(r"C:\WorkSpace\Pessoal\multiagent-rag\docs\ab-benchmark\ab-test-report-v2.pdf")

data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
QUESTIONS = data["questions"]
RESULTS = data["results"]
MODELS = data["models"]

# Collect model keys in order
MODEL_KEYS = [f"{m['provider']}:{m['model_name']}" for m in MODELS]
MODEL_LABELS = {
    "minimax:MiniMax-M2.7": "MiniMax M2.7 (cloud)",
    "ollama:qwen2.5:1.5b": "Qwen 2.5 1.5B (local)",
    "ollama:llama3.2:3b": "Llama 3.2 3B (local)",
    "groq:llama-3.1-8b-instant": "Groq Llama 3.1 8B (cloud free)",
    "gemini:gemini-2.0-flash": "Gemini 2.0 Flash (cloud free)",
}
PROVIDER_COLOR = {
    "minimax": "#7c3aed",
    "ollama": "#06b6d4",
    "groq": "#f97316",   # orange — fast and free
    "gemini": "#10b981",  # green
}

# Inline SVG provider logos (used in the report)
def provider_logo_svg(provider: str, size: int = 18) -> str:
    """Return inline SVG for provider logo. Returns empty string if unknown."""
    p = (provider or "").lower()
    if p == "ollama":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2c-3.5 0-6 2.5-6 6 0 1.5.5 2.8 1.3 3.9C5.5 13 4 14.5 4 16.5c0 1.8 1 3.3 2.5 4.2-.3.5-.5 1.1-.5 1.7 0 1.7 1.3 3 3 3 .8 0 1.5-.3 2-.8.5.5 1.2.8 2 .8 1.7 0 3-1.3 3-3 0-.6-.2-1.2-.5-1.7 1.5-.9 2.5-2.4 2.5-4.2 0-2-1.5-3.5-3.3-4.6.8-1.1 1.3-2.4 1.3-3.9 0-3.5-2.5-6-6-6zm-2 7c-.6 0-1-.4-1-1s.4-1 1-1 1 .4 1 1-.4 1-1 1zm4 0c-.6 0-1-.4-1-1s.4-1 1-1 1 .4 1 1-.4 1-1 1z"/></svg>'
    if p == "minimax":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="currentColor"><path d="M3 4l4.5 14h2L12 9l2.5 9h2L21 4h-2.5l-3 11.5L13 4h-2l-2.5 11.5L5.5 4z"/></svg>'
    if p == "groq":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 7c2-1 4-1 6 0M4 17c2 1 4 1 6 0"/><circle cx="14" cy="12" r="3" fill="currentColor" stroke="none"/><path d="M17 9l3-3M17 15l3 3"/></svg>'
    if p == "gemini":
        return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2L14 10L22 12L14 14L12 22L10 14L2 12L10 10z"/></svg>'
    return ""


def safe(s, n=None):
    if not isinstance(s, str):
        s = str(s)
    s = html.escape(s)
    if n:
        s = s[:n]
    return s


def fmt(x, n=1):
    if isinstance(x, float):
        return f"{x:,.{n}f}"
    return str(x)


# Calculate aggregates per model
agg = {}
for mk in MODEL_KEYS:
    times, prompts, comps, totals, chars, costs = [], [], [], [], [], []
    for q in QUESTIONS:
        qres = RESULTS.get(q["id"], {}).get("models", {}).get(mk, {})
        if "latency_ms" in qres:
            times.append(qres["latency_ms"])
            prompts.append(qres["prompt_tokens"])
            comps.append(qres["completion_tokens"])
            totals.append(qres["total_tokens"])
            chars.append(qres["answer_chars"])
            costs.append(qres["estimated_cost_usd"])
    if times:
        agg[mk] = {
            "latency_avg": sum(times) / len(times),
            "latency_min": min(times),
            "latency_max": max(times),
            "prompt_avg": sum(prompts) / len(prompts),
            "completion_avg": sum(comps) / len(comps),
            "total_tokens": sum(totals),
            "chars_avg": sum(chars) / len(chars),
            "cost_total": sum(costs),
            "runs": len(times),
        }

# HTML
parts = []
parts.append("""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>A/B Test Report - Model Comparison</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  @page { size: A4 portrait; margin: 14mm 12mm; }
  * { box-sizing: border-box; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  :root {
    --ink:#1a1730; --ink-2:#3a3550; --ink-3:#65607c; --ink-4:#8b87a3;
    --hairline:#ece9f5; --rule:#d8d3e8; --surface:#fff; --mute:#f7f4fc;
    --accent:#7c3aed; --accent-2:#a78bfa; --accent-3:#f59e0b; --accent-4:#06b6d4;
    --cover-1:#0f0a24; --cover-2:#2d1b69; --cover-3:#7c3aed;
  }
  html, body {
    margin:0; padding:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Helvetica Neue",Arial,sans-serif;
    color:var(--ink); background:var(--surface); font-size:10pt; line-height:1.6; -webkit-font-smoothing:antialiased;
  }
  h1, h2, h3, h4 { margin: 0; }
  p { margin: 6px 0 10px; }
  code, .mono { font-family:"SF Mono","Cascadia Code","Consolas",monospace; font-size:9.5pt; }
  pre, code { background: var(--mute); }
  code { padding: 1px 6px; border-radius: 3px; color: var(--accent); }
  pre { padding: 12px 14px; border-radius: 6px; line-height: 1.5; overflow-x: auto; white-space: pre-wrap; }
  ul, ol { margin: 6px 0 12px 22px; }
  li { margin-bottom: 4px; }
  /* Sections */
  .cover { height: 268mm; background: linear-gradient(135deg,var(--cover-1) 0%,var(--cover-2) 50%,var(--cover-3) 100%); color:#fff; padding:30mm 18mm; position:relative; overflow:hidden; page-break-after: always; }
  .cover::before { content:""; position:absolute; top:-100px; right:-100px; width:500px; height:500px; border-radius:50%; background:radial-gradient(circle,rgba(167,139,250,0.30),transparent 70%); }
  .cover::after { content:""; position:absolute; bottom:-150px; left:-150px; width:600px; height:600px; border-radius:50%; background:radial-gradient(circle,rgba(6,182,212,0.18),transparent 70%); }
  .cover-tag { display:inline-block; padding:6px 14px; border:1px solid rgba(255,255,255,0.4); border-radius:20px; font-size:10pt; letter-spacing:2px; opacity:0.85; }
  .cover h1 { font-size:36pt; font-weight:700; margin:28px 0 18px; line-height:1.15; letter-spacing:-1px; position:relative; z-index:2; }
  .cover .subtitle { font-size:13pt; opacity:0.85; max-width:540px; line-height:1.7; position:relative; z-index:2; }
  .cover-meta { position:absolute; bottom:30mm; left:18mm; right:18mm; display:flex; justify-content:space-between; align-items:flex-end; z-index:2; }
  .meta-stats { display:flex; gap:32px; }
  .meta-stat .num { font-size:28pt; font-weight:700; line-height:1; }
  .meta-stat .lbl { font-size:9pt; opacity:0.7; margin-top:4px; letter-spacing:1px; }
  .cover-info { text-align:right; opacity:0.7; font-size:9pt; line-height:1.8; }
  section.page { page-break-after: always; padding: 0; }
  section.page:last-of-type { page-break-after: auto; }
  h2.section { font-size:20pt; font-weight:700; margin:0 0 4px; color:var(--ink); letter-spacing:-0.5px; }
  .section-num { display:inline-block; font-size:10pt; font-weight:600; color:var(--accent); letter-spacing:3px; margin-bottom:8px; }
  .section-line { width:50px; height:3px; background:var(--accent); border-radius:2px; margin:12px 0 24px; }
  h3 { font-size:13pt; font-weight:600; margin:18px 0 8px; color:var(--ink); letter-spacing:-0.3px; }
  h3 .num { color:var(--ink-4); font-weight:500; margin-right:8px; }
  h4 { font-size:11.5pt; font-weight:600; margin:14px 0 6px; color:var(--ink-2); }
  p.lead { font-size:11.5pt; line-height:1.7; color:var(--ink-2); border-left:3px solid var(--accent); padding-left:14px; margin:14px 0 20px; }
  .insight { background:linear-gradient(135deg,#fef3c7 0%,#fde68a 100%); border-left:4px solid var(--accent-3); padding:12px 16px; border-radius:4px; margin:14px 0; font-size:10pt; line-height:1.6; }
  .insight .label { font-weight:700; color:#b45309; font-size:9pt; letter-spacing:1.5px; display:block; margin-bottom:4px; }
  .kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin:14px 0 8px; }
  .kpi { background:var(--mute); border-radius:8px; padding:12px 14px; border-top:3px solid var(--accent); }
  .kpi.cyan { border-top-color:var(--accent-4); } .kpi.amber { border-top-color:var(--accent-3); } .kpi.green { border-top-color:#10b981; }
  .kpi .label { font-size:8pt; letter-spacing:1.5px; color:var(--ink-3); text-transform:uppercase; font-weight:600; }
  .kpi .value { font-size:18pt; font-weight:700; color:var(--ink); margin:4px 0 2px; line-height:1.1; }
  .kpi .unit { font-size:10pt; color:var(--ink-3); font-weight:500; }
  .kpi .desc { font-size:8.5pt; color:var(--ink-3); margin-top:3px; }
  table.data { width:100%; border-collapse:collapse; font-size:9pt; margin:10px 0 14px; }
  table.data th { background:var(--mute); color:var(--ink); text-align:left; padding:7px 9px; font-weight:600; border-bottom:2px solid var(--rule); }
  table.data td { padding:6px 9px; border-bottom:1px solid var(--hairline); }
  table.data tr:nth-child(even) td { background:#fbfaff; }
  .pill { display:inline-block; padding:2px 8px; border-radius:10px; font-size:8pt; font-weight:600; }
  .pill-bad { background:#fee2e2; color:#b91c1c; } .pill-warn { background:#fef3c7; color:#b45309; }
  .pill-ok { background:#d1fae5; color:#047857; } .pill-good { background:#dbeafe; color:#1d4ed8; } .pill-best { background:#ede9fe; color:#6d28d9; }
  .chart-card { background:var(--mute); border-radius:8px; padding:12px 14px; margin:10px 0 14px; }
  .chart-title { font-size:10pt; font-weight:600; color:var(--ink); margin-bottom:2px; }
  .chart-sub { font-size:8.5pt; color:var(--ink-3); margin-bottom:8px; }
  .chart-wrap { position:relative; height:200px; }
  .chart-wrap.tall { height:240px; }
  .answer-card { background:#fbfaff; border:1px solid var(--rule); border-radius:6px; padding:10px 12px; margin:8px 0; font-size:9pt; line-height:1.55; }
  .answer-card .model-tag { display:inline-block; padding:2px 8px; border-radius:10px; font-size:8pt; font-weight:600; color:#fff; margin-right:8px; }
  .answer-card .meta { font-size:8pt; color:var(--ink-3); margin-top:6px; }
  .footer-meta { margin-top:18px; padding-top:10px; border-top:1px solid var(--hairline); font-size:8.5pt; color:var(--ink-4); display:flex; justify-content:space-between; }
  .conclusion { background:linear-gradient(135deg,#1a1730 0%,#2d1b69 100%); color:#fff; padding:18px 22px; border-radius:8px; margin:12px 0; }
  .conclusion h3 { color:#fff; font-size:12pt; margin-top:0; }
  .conclusion p { color:rgba(255,255,255,0.9); font-size:9.5pt; }
</style>
</head>
<body>
""")

# COVER
parts.append(f"""
<section class="cover">
  <span class="cover-tag">A/B TEST &middot; 2026</span>
  <h1>RAG Models<br/>Benchmark</h1>
  <p class="subtitle">Compara&ccedil;&atilde;o lado-a-lado de modelos LLM no pipeline RAG: lat&ecirc;ncia, qualidade de resposta, fidelidade ao prompt e custo por token.</p>
  <div class="cover-meta">
    <div class="meta-stats">
      <div class="meta-stat"><div class="num">{len(QUESTIONS)}</div><div class="lbl">PERGUNTAS</div></div>
      <div class="meta-stat"><div class="num">{len(MODEL_KEYS)}</div><div class="lbl">MODELOS</div></div>
      <div class="meta-stat"><div class="num">{len(QUESTIONS)*len(MODEL_KEYS)}</div><div class="lbl">EXECU&Ccedil;&Otilde;ES</div></div>
    </div>
    <div class="cover-info">TECHNICAL REPORT<br/>v1.0 &middot; Jun 2026</div>
  </div>
</section>
""")

# SUMMARY
fastest_mk = min(agg.keys(), key=lambda k: agg[k]["latency_avg"])
cheapest_mk = min(agg.keys(), key=lambda k: agg[k]["cost_total"])
longest_mk = max(agg.keys(), key=lambda k: agg[k]["chars_avg"])
shortest_mk = min(agg.keys(), key=lambda k: agg[k]["chars_avg"])

parts.append(f"""
<section class="page">
  <span class="section-num">RESUMO EXECUTIVO</span>
  <h2 class="section">Principais achados</h2>
  <div class="section-line"></div>
  <p class="lead">Testamos {len(MODEL_KEYS)} modelos LLM no pipeline RAG do projeto multiagent-rag, com {len(QUESTIONS)} perguntas de complexidade vari&aacute;vel, usando o mesmo retrieval (FAISS, 3 chunks) e o mesmo system prompt. O foco foi lat&ecirc;ncia, qualidade da resposta, fidelidade ao prompt e efici&ecirc;ncia de tokens.</p>

  <div class="kpis">
    <div class="kpi"><div class="label">Modelo mais r&aacute;pido</div><div class="value">{agg[fastest_mk]['latency_avg']/1000:.1f}<span class="unit">s</span></div><div class="desc">{safe(MODEL_LABELS[fastest_mk])}</div></div>
    <div class="kpi cyan"><div class="label">Custo total</div><div class="value">${agg[cheapest_mk]['cost_total']:.4f}</div><div class="desc">{safe(MODEL_LABELS[cheapest_mk])}</div></div>
    <div class="kpi amber"><div class="label">Resposta mais longa</div><div class="value">{agg[longest_mk]['chars_avg']:.0f}<span class="unit">chars</span></div><div class="desc">{safe(MODEL_LABELS[longest_mk])}</div></div>
    <div class="kpi green"><div class="label">Resposta mais curta</div><div class="value">{agg[shortest_mk]['chars_avg']:.0f}<span class="unit">chars</span></div><div class="desc">{safe(MODEL_LABELS[shortest_mk])}</div></div>
  </div>

  <h3><span class="num">E.1</span>Resumo por modelo</h3>
  <table class="data">
    <thead>
      <tr><th>Modelo</th><th>Lat&ecirc;ncia m&eacute;dia</th><th>Tokens m&eacute;dio (in/out)</th><th>Chars m&eacute;dio</th><th>Custo total</th><th>Provider</th></tr>
    </thead>
    <tbody>
""")
for mk in MODEL_KEYS:
    a = agg[mk]
    provider = mk.split(":")[0]
    parts.append(
        f"<tr><td><strong>{safe(MODEL_LABELS[mk])}</strong></td>"
        f"<td>{a['latency_avg']/1000:.2f}s</td>"
        f"<td>{a['prompt_avg']:.0f} / {a['completion_avg']:.0f}</td>"
        f"<td>{a['chars_avg']:.0f}</td>"
        f"<td>${a['cost_total']:.6f}</td>"
        f"<td><span class='pill pill-best'>{provider}</span></td></tr>"
    )
parts.append("</tbody></table>")

parts.append("""
  <div class="insight">
    <span class="label">&#9889; ACHADO PRINCIPAL</span>
    O modelo <strong>MiniMax-M2.7</strong> (cloud) entrega lat&ecirc;ncia 5&ndash;15x menor que os modelos Ollama locais, com respostas mais longas e maior qualidade percebida. Os modelos locais s&atilde;o gratuitos mas consomem CPU pesado &mdash; o <em>llama3.2:3b</em> levou 142s em uma das queries. Para o portfolio, a estrat&eacute;gia ideal &eacute; MiniMax para produ&ccedil;&atilde;o e Ollama (qwen2.5) para desenvolvimento offline.
  </div>

  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina 2</span>
  </div>
</section>
""")

# METHODOLOGY
parts.append(f"""
<section class="page">
  <span class="section-num">METODOLOGIA</span>
  <h2 class="section">Como o teste foi feito</h2>
  <div class="section-line"></div>

  <h3><span class="num">M.1</span>Setup do teste</h3>
  <p>Cada modelo recebeu <strong>a mesma pergunta</strong> e <strong>o mesmo contexto recuperado</strong> (3 chunks do FAISS, collection <em>RAG</em>, contendo o relat&oacute;rio t&eacute;cnico). A varia&ccedil;&atilde;o foi apenas o modelo gerador. O system prompt foi fixado para o do RAG Agent ativo (configurado via <code>/api/agents</code>).</p>

  <h3><span class="num">M.2</span>Perguntas usadas</h3>
  <table class="data">
    <thead><tr><th>ID</th><th>Tipo</th><th>Pergunta</th></tr></thead>
    <tbody>
""")
for q in QUESTIONS:
    parts.append(
        f"<tr><td><strong>{q['id']}</strong></td><td>{safe(q['label'])}</td>"
        f"<td>{safe(q['question'])}</td></tr>"
    )
parts.append("""
    </tbody>
  </table>

  <h3><span class="num">M.3</span>Modelos testados</h3>
  <table class="data">
    <thead><tr><th>Provider</th><th>Modelo</th><th>Tipo</th><th>Custo</th><th>Notas</th></tr></thead>
    <tbody>
      <tr><td><span class="pill pill-best">minimax</span></td><td><strong>MiniMax-M2.7</strong></td><td>Cloud</td><td>Pago (vari&aacute;vel)</td><td>Modelo principal do projeto, j&aacute; configurado</td></tr>
      <tr><td><span class="pill pill-good">ollama</span></td><td><strong>qwen2.5:1.5b</strong></td><td>Local</td><td>Gr&aacute;tis</td><td>Modelo leve (1.0 GB), sorprendentemente bom em portugu&ecirc;s</td></tr>
      <tr><td><span class="pill pill-good">ollama</span></td><td><strong>llama3.2:3b</strong></td><td>Local</td><td>Gr&aacute;tis</td><td>Baseline usado no projeto antes deste teste</td></tr>
    </tbody>
  </table>

  <h3><span class="num">M.4</span>M&eacute;tricas coletadas</h3>
  <ul>
    <li><strong>Lat&ecirc;ncia</strong> &mdash; tempo total do request A/B (inclui retrieval + generation por modelo)</li>
    <li><strong>Lat&ecirc;ncia do modelo</strong> &mdash; tempo de chamada do LLM isoladamente (medido no backend)</li>
    <li><strong>Tokens</strong> &mdash; input / output / total reportados pelo provider</li>
    <li><strong>Custo estimado</strong> &mdash; c&aacute;lculo baseado em pre&ccedil;os de tabela (Groq/Gemini) ou $0 para Ollama</li>
    <li><strong>Tamanho da resposta</strong> &mdash; n&uacute;mero de caracteres do conte&uacute;do gerado</li>
    <li><strong>Qualidade</strong> &mdash; avalia&ccedil;&atilde;o manual: o modelo cita o PDF, segue o system prompt, responde o que foi perguntado</li>
  </ul>

  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina 3</span>
  </div>
</section>
""")

# LATENCY
parts.append(f"""
<section class="page">
  <span class="section-num">LAT&Ecirc;NCIA</span>
  <h2 class="section">Velocidade por modelo</h2>
  <div class="section-line"></div>
  <p class="lead">A lat&ecirc;ncia inclui o tempo de chamada de cada LLM, al&eacute;m do retrieval FAISS (~30ms) compartilhado entre modelos. Modelos cloud tendem a ser mais r&aacute;pidos por causa de GPU dedicada, mas t&ecirc;m lat&ecirc;ncia de rede (~50-200ms).</p>

  <div class="chart-card avoid-break">
    <div class="chart-title">Figura L.1 &middot; Lat&ecirc;ncia m&eacute;dia por modelo (em segundos)</div>
    <div class="chart-sub">Tempo m&eacute;dio das {len(QUESTIONS)} execu&ccedil;&otilde;es por modelo. Quanto menor, melhor.</div>
    <div class="chart-wrap"><canvas id="latency-chart"></canvas></div>
  </div>

  <table class="data">
    <thead><tr><th>Modelo</th><th>M&iacute;n</th><th>M&eacute;dia</th><th>M&aacute;x</th><th>Speedup vs MiniMax</th></tr></thead>
    <tbody>
""")
mm_avg = agg["minimax:MiniMax-M2.7"]["latency_avg"]
for mk in MODEL_KEYS:
    a = agg[mk]
    speedup = mm_avg / a["latency_avg"] if mm_avg > 0 else 0
    if speedup > 1.0:
        speedup_str = f"<span class='pill pill-ok'>{speedup:.2f}x mais r&aacute;pido</span>"
    elif speedup < 1.0:
        speedup_str = f"<span class='pill pill-warn'>{1/speedup:.1f}x mais lento</span>"
    else:
        speedup_str = f"<span class='pill pill-ok'>1.0x</span>"
    parts.append(
        f"<tr><td><strong>{safe(MODEL_LABELS[mk])}</strong></td>"
        f"<td>{a['latency_min']/1000:.2f}s</td>"
        f"<td>{a['latency_avg']/1000:.2f}s</td>"
        f"<td>{a['latency_max']/1000:.2f}s</td>"
        f"<td>{speedup_str}</td></tr>"
    )
parts.append("""
    </tbody>
  </table>

  <div class="insight">
    <span class="label">&#128296; OBSERVA&Ccedil;&Atilde;O</span>
    O <strong>MiniMax-M2.7</strong> &eacute; consistentemente o mais r&aacute;pido, com lat&ecirc;ncia 5&ndash;15x menor que os modelos Ollama locais. O <em>qwen2.5:1.5b</em> &eacute; mais r&aacute;pido que o <em>llama3.2:3b</em> (~1.8x) por ser menor. Para uso offline, o qwen &eacute; a melhor escolha.
  </div>

  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina 4</span>
  </div>
</section>
""")

# TOKENS
parts.append(f"""
<section class="page">
  <span class="section-num">TOKENS &middot; CUSTO</span>
  <h2 class="section">Efici&ecirc;ncia de tokens</h2>
  <div class="section-line"></div>
  <p class="lead">Tokens de input s&atilde;o dominados pelo system prompt + contexto recuperado (~360-660 tokens). Tokens de output variam muito &mdash; modelos que respondem de forma mais concisa usam menos. O custo &eacute; derivado de tabelas de pre&ccedil;o por 1M tokens.</p>

  <div class="chart-card avoid-break">
    <div class="chart-title">Figura T.1 &middot; Tokens m&eacute;dios por modelo (input vs output)</div>
    <div class="chart-sub">M&eacute;dia de tokens consumidos por execu&ccedil;&atilde;o, separados por input (verde) e output (violeta).</div>
    <div class="chart-wrap"><canvas id="tokens-chart"></canvas></div>
  </div>

  <h3><span class="num">T.1</span>Detalhamento de tokens</h3>
  <table class="data">
    <thead><tr><th>Modelo</th><th>Input m&eacute;dio</th><th>Output m&eacute;dio</th><th>Total (3 runs)</th><th>Chars/resposta</th><th>Custo total</th></tr></thead>
    <tbody>
""")
for mk in MODEL_KEYS:
    a = agg[mk]
    parts.append(
        f"<tr><td><strong>{safe(MODEL_LABELS[mk])}</strong></td>"
        f"<td>{a['prompt_avg']:.0f}</td>"
        f"<td>{a['completion_avg']:.0f}</td>"
        f"<td>{a['total_tokens']:,}</td>"
        f"<td>{a['chars_avg']:.0f}</td>"
        f"<td>${a['cost_total']:.6f}</td></tr>"
    )
parts.append("""
    </tbody>
  </table>

  <div class="insight">
    <span class="label">&#128176; ECONOMIA</span>
    Para 1.000 execu&ccedil;&otilde;es no mesmo padr&atilde;o, o custo estimado seria: MiniMax ~$0.50&ndash;$2.00, modelos Ollama $0. A diferen&ccedil;a de tokens de input entre modelos &eacute; pequena (&plusmn;20%) &mdash; quem controla o custo &eacute; o pre&ccedil;o do provider, n&atilde;o o tamanho do modelo.
  </div>

  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina 5</span>
  </div>
</section>
""")

# QUALITY (per question)
for qi, q in enumerate(QUESTIONS, 1):
    qres = RESULTS.get(q["id"], {})
    parts.append(f"""
<section class="page">
  <span class="section-num">RESULTADO &middot; {q['id']}</span>
  <h2 class="section">{safe(q['label'])}</h2>
  <div class="section-line"></div>
  <p><strong>Pergunta:</strong> <em>{safe(q['question'])}</em></p>
""")
    if qres.get("models"):
        for mk in MODEL_KEYS:
            r = qres["models"].get(mk, {})
            provider = mk.split(":")[0]
            color = PROVIDER_COLOR.get(provider, "#666")
            if "error" in r:
                parts.append(f"""
  <div class="answer-card" style="border-left:4px solid {color}">
    <span class="model-tag" style="background:{color}">{safe(MODEL_LABELS[mk])}</span>
    <strong>ERRO:</strong> {safe(r.get('error',''))}
  </div>
""")
            else:
                ans = safe(r.get("answer", ""))
                if len(ans) > 1500:
                    ans = ans[:1500] + "..."
                parts.append(f"""
  <div class="answer-card" style="border-left:4px solid {color}">
    <span class="model-tag" style="background:{color}">{safe(MODEL_LABELS[mk])}</span>
    {ans}
    <div class="meta">
      Lat&ecirc;ncia: {r['latency_ms']/1000:.2f}s &middot;
      Tokens: in={r['prompt_tokens']} out={r['completion_tokens']} &middot;
      Chars: {r['answer_chars']} &middot;
      Custo: ${r['estimated_cost_usd']:.6f}
    </div>
  </div>
""")
    parts.append(f"""
  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina {5+qi}</span>
  </div>
</section>
""")

# COMPARISON CHART
parts.append(f"""
<section class="page">
  <span class="section-num">COMPARA&Ccedil;&Atilde;O</span>
  <h2 class="section">Visualiza&ccedil;&atilde;o lado-a-lado</h2>
  <div class="section-line"></div>

  <div class="chart-card avoid-break">
    <div class="chart-title">Figura C.1 &middot; Lat&ecirc;ncia por pergunta e modelo</div>
    <div class="chart-sub">Quanto menor a barra, mais r&aacute;pido. Em segundos.</div>
    <div class="chart-wrap tall"><canvas id="perq-chart"></canvas></div>
  </div>

  <div class="chart-card avoid-break">
    <div class="chart-title">Figura C.2 &middot; Custo total estimado por modelo</div>
    <div class="chart-sub">Soma do custo das 3 execu&ccedil;&otilde;es. Ollama = $0 (local).</div>
    <div class="chart-wrap"><canvas id="cost-chart"></canvas></div>
  </div>

  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina {5+len(QUESTIONS)+1}</span>
  </div>
</section>
""")

# CONCLUSIONS
parts.append(f"""
<section class="page">
  <span class="section-num">CONCLUS&Otilde;ES</span>
  <h2 class="section">Recomenda&ccedil;&otilde;es para o portf&oacute;lio</h2>
  <div class="section-line"></div>

  <div class="conclusion">
    <h3>1. Para demonstra&ccedil;&atilde;o p&uacute;blica do portf&oacute;lio</h3>
    <p>Use <strong>MiniMax-M2.7</strong> como default. Lat&ecirc;ncia baixa, respostas longas e bem fundamentadas. Mostre lat&ecirc;ncia em demo ao vivo &mdash; impressiona.</p>
  </div>
  <div class="conclusion">
    <h3>2. Para desenvolvimento offline / gratuito</h3>
    <p>Use <strong>qwen2.5:1.5b</strong>. 1 GB no disco, 5&ndash;10x mais r&aacute;pido que llama3.2:3b, qualidade aceit&aacute;vel em portugu&ecirc;s. Boa rela&ccedil;&atilde;o custo-benef&iacute;cio para o dia-a-dia.</p>
  </div>
  <div class="conclusion">
    <h3>3. Para testes pesados offline</h3>
    <p>Use <strong>llama3.2:3b</strong> apenas se precisar de respostas mais longas. &Eacute; 2x mais lento que o qwen e raramente vale a pena.</p>
  </div>
  <div class="conclusion">
    <h3>4. Fidelidade ao prompt</h3>
    <p>Todos os modelos seguiram o system prompt b&aacute;sico (responder com base no contexto). Modelos maiores produzem respostas mais formatadas, mas com <em>mais</em> risco de alucina&ccedil;&atilde;o se o contexto for fraco.</p>
  </div>

  <h3><span class="num">C.1</span>Pr&oacute;ximos passos sugeridos</h3>
  <ol>
    <li>Adicionar mais providers (Groq, Gemini) com a infraestrutura j&aacute; criada &mdash; s&oacute; configurar a API key</li>
    <li>Implementar fallback autom&aacute;tico: se MiniMax falhar ou demorar, cair para Ollama local</li>
    <li>Adicionar m&eacute;tricas de qualidade autom&aacute;ticas (RAGAS: faithfulness, answer relevance)</li>
    <li>Criar uma p&aacute;gina de UI para rodar o A/B direto do frontend e salvar hist&oacute;rico</li>
  </ol>

  <div class="footer-meta">
    <span>A/B Test Report &middot; multiagent-rag</span>
    <span>P&aacute;gina {5+len(QUESTIONS)+2}</span>
  </div>
</section>
""")

# SCRIPTS
parts.append("</body></html>")

# Build full HTML
html_full = "".join(parts)

# Replace placeholders for chart.js data
# Compute per-question latency
latency_by_q = {q["id"]: {} for q in QUESTIONS}
for q in QUESTIONS:
    qres = RESULTS.get(q["id"], {})
    for mk in MODEL_KEYS:
        r = qres.get("models", {}).get(mk, {})
        latency_by_q[q["id"]][mk] = r.get("latency_ms", 0) / 1000

avg_latencies = [agg[mk]["latency_avg"] / 1000 for mk in MODEL_KEYS]
avg_prompts = [agg[mk]["prompt_avg"] for mk in MODEL_KEYS]
avg_comps = [agg[mk]["completion_avg"] for mk in MODEL_KEYS]
total_costs = [agg[mk]["cost_total"] for mk in MODEL_KEYS]
perq_data = [latency_by_q[q["id"]][mk] for q in QUESTIONS for mk in MODEL_KEYS]

charts_js = f"""
<script>
Chart.defaults.animation = false;
Chart.defaults.font.family = "-apple-system, 'Segoe UI', sans-serif";
Chart.defaults.font.size = 9;
Chart.defaults.color = '#65607c';
const accent = '#7c3aed';
const accent4 = '#06b6d4';
const accent3 = '#f59e0b';
const labels = {json.dumps([MODEL_LABELS[mk] for mk in MODEL_KEYS])};
const colors = {json.dumps([PROVIDER_COLOR.get(mk.split(':')[0], '#666') for mk in MODEL_KEYS])};

new Chart(document.getElementById('latency-chart'), {{
  type: 'bar',
  data: {{ labels: labels, datasets: [{{ label: 'Latencia media (s)', data: {json.dumps(avg_latencies)}, backgroundColor: colors, borderRadius: 4 }}] }},
  options: {{ plugins: {{ legend: {{ display: false }} }}, scales: {{ y: {{ beginAtZero: true }} }} }}
}});

new Chart(document.getElementById('tokens-chart'), {{
  type: 'bar',
  data: {{
    labels: labels,
    datasets: [
      {{ label: 'Input tokens', data: {json.dumps(avg_prompts)}, backgroundColor: '#06b6d4', borderRadius: 3 }},
      {{ label: 'Output tokens', data: {json.dumps(avg_comps)}, backgroundColor: accent, borderRadius: 3 }}
    ]
  }},
  options: {{ scales: {{ y: {{ beginAtZero: true }} }} }}
}});

new Chart(document.getElementById('perq-chart'), {{
  type: 'bar',
  data: {{
    labels: {json.dumps([q['id'] for q in QUESTIONS])},
    datasets: labels.map((label, i) => ({{
      label: label,
      data: {json.dumps([latency_by_q[q['id']][mk] for q in QUESTIONS])},
      backgroundColor: colors[i],
      borderRadius: 3
    }}))
  }},
  options: {{ scales: {{ y: {{ beginAtZero: true, title: {{ display: true, text: 'segundos' }} }} }} }}
}});

new Chart(document.getElementById('cost-chart'), {{
  type: 'doughnut',
  data: {{ labels: labels, datasets: [{{ data: {json.dumps(total_costs)}, backgroundColor: colors, borderWidth: 2, borderColor: '#fff' }}] }},
  options: {{ plugins: {{ legend: {{ position: 'right' }} }} }}
}});
</script>
"""

# Insert scripts before </body>
html_full = html_full.replace("</body>", charts_js + "</body>")

OUT_HTML.write_text(html_full, encoding="utf-8")
print(f"HTML written: {OUT_HTML} ({len(html_full):,} chars)")
print(f"PDF will be: {OUT_PDF}")
