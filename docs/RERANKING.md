# PyTorch Reranking Experiment

## Objective

Evaluate whether a pretrained cross-encoder improves document retrieval compared with ContextIQ's existing hybrid retrieval system.

## Implementation

- Model: `cross-encoder/ms-marco-MiniLM-L6-v2`
- Framework: PyTorch / Sentence Transformers
- Inference device: CPU
- Retrieval candidates: 12
- Evaluation questions: 15
- Metrics: Recall@K, Precision@K, MRR, and median latency

## Results

| Metric         |   Hybrid | Hybrid + Reranking |
| -------------- | -------: | -----------------: |
| Recall@1       |     1.00 |               1.00 |
| MRR@1          |     1.00 |               1.00 |
| Median latency | 70.00 ms |          126.74 ms |

## Findings

The cross-encoder did not improve ranking quality on the existing evaluation dataset. However, it increased median latency by approximately 81%.

The current benchmark has limited difficulty because hybrid retrieval already places the labeled relevant passage first for every question.

## Engineering Decision

Keep hybrid retrieval as the default. Retain cross-encoder reranking as an experimental feature for future evaluation with harder, more ambiguous questions.

Fine-tuning is deferred because the current results do not establish a model weakness that training would address.
