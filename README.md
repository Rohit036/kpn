# KPN Agentic RAG (Local Baseline)

This repository contains a simple, modular local baseline for a KPN-focused agentic RAG system.

## What is implemented

- Ingestion pipeline for KPN news pages.
- Text extraction and chunking.
- Metadata-enriched records (timestamps, depth, hashes, source URL, status).
- Local ChromaDB persistence.
- LLM-based tool-calling orchestrator for routing, retrieval, and grounded answer synthesis.
- Modular package layout under `src/`.

## Repository structure

- `src/kpn_agent/common`: Shared helpers (hashing, text, jsonl).
- `src/kpn_agent/config.py`: Runtime defaults and path config.
- `src/kpn_agent/ingestion`: Crawler and chunk builder.
- `src/kpn_agent/storage`: ChromaDB client and operations.
- `src/kpn_agent/pipelines`: End-to-end ingestion pipelines.
- `src/app`: FastAPI app and LLM orchestration service.
- `scripts/kpnnews_script.py`: CLI wrapper for ingestion.
- `scripts/run_api.py`: FastAPI launcher.
- `data/raw`: Raw crawled JSONL outputs.
- `data/processed`: Chunked JSONL outputs.
- `data/vector_store`: Local vector DB persistence.
- `data/logs`: LLM orchestration run logs and traces.
- `docs`: Design and implementation notes.

## Setup

Install packages in your environment:

```bash
pip install -r requirements.txt
```

## Usage

### 1) Ingest news data

```bash
python scripts/kpnnews_script.py
```

Useful options:

```bash
python scripts/kpnnews_script.py --max-pages 50 --max-depth 2 --skip-chroma
python scripts/kpnnews_script.py --collection kpn_news --persist-dir data/vector_store/chroma_store
```

### 2) Build indexes for API queries

The API query path uses these retrieval tools:

- `kpn_news_tool`: retrieval-only tool over the `kpnnews` index.
- `kpn_quarterlyreports_tool`: retrieval-only tool over the `kpnquarterlyreports` index.

Before querying KPN news, build or refresh the news index:

```bash
python scripts/test_kpnnews_ingest.py --seed-url "https://www.overons.kpn/nieuws/en" --allowed-domain overons.kpn
```

Before querying quarterly reports, build the quarterly index once:

```bash
python scripts/test_quarterly_ingest.py
```

### 3) Run API (FastAPI)

Start locally:

```bash
python scripts/run_api.py --host 127.0.0.1 --port 8000
```

Endpoints:

- `GET /health`
- `POST /query`

Example request:

```bash
curl -X POST http://127.0.0.1:8000/query \
	-H "Content-Type: application/json" \
	-d '{"query":"What are the latest KPN announcements?","top_k":4,"max_tool_rounds":2}'
```

### 4) Dockerize And Run API

Build image:

```bash
docker build -t kpn-agent-api .
```

Run container (mount `data` to persist Chroma store and logs):

```bash
docker run --rm -p 8000:8000 \
	--env-file .env \
	-v ./data:/app/data \
	kpn-agent-api
```

Test:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/query \
	-H "Content-Type: application/json" \
	-d '{"query":"What are the latest KPN announcements?"}'
```

What this validates:

- LLM-based tool routing.
- One-tool and two-tool orchestration paths.
- Evidence merging and citation formatting.
- Final answer synthesis contract.
- Local observability trace logging.

Index names used by the real tools:

- `kpnnews`
- `kpnquarterlyreports`

Quarterly flow is now separated:

- `scripts/test_quarterly_ingest.py` builds or updates the `kpnquarterlyreports` index.
- `kpn_quarterlyreports_tool` only queries the index at request time.

KPN news flow is now separated:

- `scripts/test_kpnnews_ingest.py` builds or updates the `kpnnews` index by crawling KPN news pages with BeautifulSoup.
- `kpn_news_tool` only queries the index at request time.

### 5) Tiny sequence diagram (LLM tool-calling flow)

```mermaid
sequenceDiagram
	participant U as User
	participant L as LLM Planner
	participant A as AnnualReportTool
	participant N as KpnNewsTool

	U->>L: Ask question
	L->>A: tool_call(query, top_k)
	L->>N: tool_call(query, top_k)
	A-->>L: Evidence
	N-->>L: Evidence
	L->>L: Synthesize grounded answer
	L-->>U: Final answer + citations
```

### 6) Test KPN news index build/update (incremental crawl)

This script demonstrates the separated ingestion strategy for KPN news:

- Crawl latest pages from the configured news URL.
- Compare current page content hashes against already indexed content hashes.
- Keep unchanged pages untouched.
- Replace chunks only for new or changed pages in `kpnnews`.

Run ingestion/update:

```bash
python scripts/test_kpnnews_ingest.py --seed-url "https://www.overons.kpn/nieuws/en" --allowed-domain overons.kpn --max-pages 30 --max-depth 2
```

For hourly change tracking, run the same command from your scheduler every hour.

## Output artifacts

- Raw docs: `data/raw/kpn_news_raw.jsonl`
- Chunks: `data/processed/kpn_news_chunks.jsonl`
- Vector store: `data/vector_store/chroma_store`

## Retrieval and answer generation details

This section explains exactly how answers are produced in the current LLM baseline.

### 1) Which embedding model is used

- The system uses ChromaDB local persistence via `PersistentClient`.
- Collections are created with `get_or_create_collection` and no custom embedding function is passed.
- This means Chroma uses its default embedding behavior for your installed Chroma version.

In other words:

- Embedding model selection is currently delegated to Chroma defaults.
- The project does not yet pin a custom embedding model in code.

Why this is acceptable for the baseline:

- It minimizes setup complexity.
- It allows quick local iteration for ingestion and retrieval pipeline design.

Why this should be improved for production:

- Production systems should explicitly pin the embedding model/version for reproducibility.
- Model pinning makes retrieval quality easier to benchmark and compare over time.

### 2) How data is transformed before retrieval

News ingestion flow:

1. Crawl from a seed URL with bounded depth and page limit.
2. Keep same-domain, relevant links (news/article-like URLs).
3. Extract text from main/article/body after removing noisy HTML tags.
4. Normalize whitespace.
5. Create metadata-rich page records.
6. Chunk each page into overlapping text chunks.
7. Upsert chunks + metadata into Chroma collection.

Important metadata currently stored:

- `doc_id`, `url`, `title`, `source_type`
- `crawl_depth`, `crawl_timestamp_utc`, `crawl_timestamp_epoch`
- `status_code`, `text_char_len`, `content_hash`
- `chunk_index`, `chunk_count`

### 3) How query routing works

- The LLM planner decides tool calls at runtime from tool definitions.
- Available tools are currently quarterly reports and KPN news retrieval.
- Tool arguments typically include a narrowed query plus `top_k`.

### 4) How retrieval scoring works

For each selected collection:

1. Run Chroma similarity query with `n_results = top_k_per_index`.
2. Read returned `documents`, `metadatas`, and `distances`.
3. Convert distance to a simple score for display:
	- `score = 1 / (1 + distance)`
4. Merge hits from all queried collections.
5. Sort by score descending.

Notes:

- This score is a display-friendly transformation, not a calibrated confidence model.
- Cross-collection score comparability is approximate in this baseline.

### 5) How final answer text is generated

- The LLM synthesizes the final answer after receiving tool outputs.
- The synthesis step is instructed to use only retrieved evidence and avoid hallucinations.
- Citations are included from the merged, ranked evidence set.
- Full planner/tool/synthesis traces are logged under `data/logs`.

### 6) How sources are produced

Source list generation:

1. Deduplicate by `(url, title, collection)`.
2. Include collection name, title, URL, crawl timestamp.
3. Include score and short snippet for traceability.
4. Limit to configurable `max_sources`.

### 7) Current limitations (transparent)

- Embedding model is not explicitly pinned yet.
- Answer generation is heuristic extractive synthesis, not LLM-grounded summarization.
- No reranking stage yet.
- No evaluation harness yet (precision/recall/citation quality tests).

### 8) Recommended next upgrade path

1. Pin explicit embedding model in code/config.
2. Add annual report ingestion pipeline to populate `annual_reports` collection consistently.
3. Add optional LLM synthesis step that uses retrieved chunks and preserves citations.
4. Add retrieval evaluation set with expected source checks.

## Next planned additions

- Annual report ingestion script with same metadata schema.
- Unified CLI with subcommands (`ingest-news`, `ingest-annual`, `query`).
- Basic tests for crawler, chunking, and query pipeline.
