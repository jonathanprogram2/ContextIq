# ContextIQ Retrieval Evaluation

The evaluation file `datasets/evaluation/questions.json` starts empty intentionally. DO NOT publish fabricated benchmark scores.

After indexing a small public or synthetic PDF, get stable chunk IDs:

```powershell
docker compose exec postgres psql -U contextiq -d contextiq -c "SELECT c.id, d.filename, c.page_number, left(c.text_content, 110) AS excerpt FROM document_chunks c JOIN documents d ON c.document_id=d.id ORDER BY c.id;"
```

Manually verify the relevant chunk ID(s) for each question by reading the original PDF and the chunk text. Format:

```json
[
  {
    "question": "What exercise does the guide recommend for warmup?",
    "relevant_chunk_ids": [123]
  }
]
```

The ID `123` is only an illustrative placeholder. Replace it with a verified ID from YOUR database. Add at least five labeled cases, including paraphrases and exact-keyword questions.

From project root in PowerShell:

```powershell
$env:PYTHONPATH = (Resolve-Path .\backend).Path
.\backend\.venv\Scripts\python.exe .\scripts\evaluate_retrieval.py --dataset .\datasets\evaluation\questions.json --k 4
```

Metrics: recall@k = fraction of relevant chunks retrieved, precision@k = relevant chunks among k result slots, reciprocal rank = 1/rank of first relevant chunk, MRR = mean reciprocal rank across queries. Retrieval latency includes local embedding and DB access; it does not include generation or model-grade latency. All numbers are actual measured values; compare both retrieval configurations on the same cases and hardware.

**Limitations:** No Ragas metrics are enabled yet. Model-based evidence grading in the new agentic path is provisional and can make mistakes. A separate Ragas evaluation run with explicitly local models should be added after curated test cases exist, with model versions and failure cases documented. Do not call these scores answer faithfulness.
