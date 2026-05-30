# Implementation Notes

## Goal

Build a minimal, production-minded local baseline before adding more complexity.

## Completed milestones

1. Created first ingestion script for one source (KPN news).
2. Added metadata-rich ingestion records.
3. Added chunking and ChromaDB persistence.
4. Built second script for retrieval and source-grounded answers.
5. Refactored into modular package-based architecture.
6. Reorganized repository into `scripts`, `src`, `data`, and `docs`.

## Metadata captured during ingestion

- `doc_id`
- `url`
- `parent_url`
- `title`
- `source_type`
- `crawl_depth`
- `crawl_timestamp_utc`
- `crawl_timestamp_epoch`
- `status_code`
- `text_char_len`
- `content_hash`
- `chunk_index`
- `chunk_count`

## Query behavior

- LLM plans tool calls dynamically from available tool definitions.
- Retrieval is grounded in Chroma collections via tool calls.
- Output includes synthesized answer, selected tools, and citations.

## Design choices

- Kept orchestration simple and deterministic.
- Prioritized traceability via metadata and source output.
- Separated core logic from CLI wrappers to keep code testable.
- Preserved local-first approach for fast iteration.

## LLM-only architecture

- Runtime query handling is now LLM-based tool-calling only.
- The LLM planner decides which retrieval tool(s) to call (`kpn_news_tool`, `kpn_quarterlyreports_tool`).
- Tools remain retrieval-only and return grounded evidence chunks, scores, and source metadata.
- Final response is synthesized by the LLM from tool outputs with citations.
- End-to-end flow is logged locally under `data/logs` (run summary + per-run traces).

## Current limitations

- Retrieval quality still depends on chunking strategy and indexed source quality.
- LLM synthesis can vary phrasing between runs, even with grounded evidence.
- No full automated test suite yet.

## Immediate next step

Implement annual report ingestion with same schema and push to `annual_reports` collection so `--mode both` becomes fully useful.
