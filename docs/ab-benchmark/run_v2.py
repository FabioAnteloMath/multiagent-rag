"""Run full A/B with 4 models (MiniMax, qwen, llama, Groq). Gemini skipped (rate limit)."""
import json
import time
import urllib.request
from datetime import datetime
from pathlib import Path

API = "http://127.0.0.1:8011/api"
OUT = Path(r"C:\WorkSpace\Pessoal\multiagent-rag\docs\ab-benchmark")
OUT.mkdir(parents=True, exist_ok=True)
TS = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
JSON_PATH = OUT / f"benchmark_v2_{TS}.json"
LOG_PATH = OUT / f"benchmark_v2_{TS}.log"


def log(msg):
    line = f"[{datetime.utcnow().strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def save(b):
    JSON_PATH.write_text(json.dumps(b, indent=2, ensure_ascii=False), encoding="utf-8")


def post_ab(payload, timeout=300):
    req = urllib.request.Request(
        f"{API}/ask/ab",
        method="POST",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


QUESTIONS = [
    {"id": "Q1", "label": "Factual (HyDE)", "question": "O que e HyDE e qual problema ele resolve em RAG?"},
    {"id": "Q2", "label": "Comparative (RAG tiers)", "question": "Compare Naive RAG, Advanced RAG e Modular RAG em uma frase cada."},
    {"id": "Q3", "label": "Recommendation (production stack)", "question": "Para um RAG em producao com time de 2 devs, qual stack voce recomenda?"},
]

MODELS = [
    {"provider": "ollama", "model_name": "qwen2.5:1.5b", "temperature": 0.3, "max_tokens": 500},
    {"provider": "groq", "model_name": "llama-3.1-8b-instant", "temperature": 0.3, "max_tokens": 500},
    {"provider": "minimax", "model_name": "MiniMax-M2.7", "temperature": 0.3, "max_tokens": 500},
    {"provider": "ollama", "model_name": "llama3.2:3b", "temperature": 0.3, "max_tokens": 500},
]


def run():
    benchmark = {
        "started_at": datetime.utcnow().isoformat(),
        "questions": QUESTIONS,
        "models": MODELS,
        "results": {},
    }
    save(benchmark)
    log(f"Starting v2 benchmark with {len(MODELS)} models")

    for spec in MODELS:
        model_key = f"{spec['provider']}:{spec['model_name']}"
        log(f"\n--- Model: {model_key} ---")
        for q in QUESTIONS:
            qkey = q["id"]
            if qkey not in benchmark["results"]:
                benchmark["results"][qkey] = {
                    "question": q["question"],
                    "label": q["label"],
                    "models": {},
                }
            log(f"  Q: {q['question']}")
            t0 = time.time()
            try:
                r = post_ab({
                    "question": q["question"],
                    "top_k": 3,
                    "agent_category": "rag",
                    "models": [spec],
                }, timeout=300)
                elapsed = time.time() - t0
                res = r["results"][0]
                log(f"    ok in {elapsed:.1f}s | {res['latency_ms']:.0f}ms | in={res['prompt_tokens']} out={res['completion_tokens']} | {len(res['answer'])} chars")
                benchmark["results"][qkey]["models"][model_key] = {
                    "provider": spec["provider"],
                    "model_name": spec["model_name"],
                    "temperature": spec["temperature"],
                    "max_tokens": spec["max_tokens"],
                    "answer": res["answer"],
                    "answer_chars": len(res["answer"]),
                    "latency_ms": res["latency_ms"],
                    "prompt_tokens": res["prompt_tokens"],
                    "completion_tokens": res["completion_tokens"],
                    "total_tokens": res["total_tokens"],
                    "estimated_cost_usd": res["estimated_cost_usd"],
                    "sources": res["sources"],
                    "wall_clock_seconds": elapsed,
                }
            except Exception as e:
                elapsed = time.time() - t0
                log(f"    ERROR in {elapsed:.1f}s: {e}")
                benchmark["results"][qkey]["models"][model_key] = {
                    "provider": spec["provider"],
                    "model_name": spec["model_name"],
                    "error": str(e),
                    "wall_clock_seconds": elapsed,
                }
            save(benchmark)

    benchmark["finished_at"] = datetime.utcnow().isoformat()
    save(benchmark)
    log(f"\nDone. Saved to {JSON_PATH.name}")


if __name__ == "__main__":
    run()
