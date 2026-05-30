import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import AzureOpenAI

from kpn_agent.common.log_utils import append_jsonl, now_utc_iso, write_json
from kpn_agent.common.text_utils import preview_text
from kpn_agent.config import StorageConfig
from kpn_agent.orchestration.schemas import EvidenceItem
from kpn_agent.storage.chroma_store import create_client, query_collection


@dataclass
class ToolTrace:
    tool_name: str
    collection_name: str
    status: str
    latency_ms: int
    requested_top_k: int
    returned_rows: int
    query: str
    error: str = ""
    rows: List[Dict[str, Any]] = field(default_factory=list)


def _rows_to_evidence(tool_name: str, rows: List[Dict[str, Any]]) -> List[EvidenceItem]:
    evidence: List[EvidenceItem] = []
    for row in rows:
        md = row.get("metadata", {}) or {}
        evidence.append(
            EvidenceItem(
                tool_name=tool_name,
                source_type=str(md.get("source_type", row.get("collection", "unknown"))),
                title=str(md.get("source_title", md.get("source_url", "unknown source"))),
                url=str(md.get("source_url", "")),
                snippet=preview_text(str(row.get("document", ""))),
                score=float(row.get("score") or 0.0),
            )
        )
    return evidence


def _tool_call_query_collection(
    user_query: str,
    top_k: int,
    collection_name: str,
    tool_name: str,
    persist_dir: str,
) -> tuple[List[EvidenceItem], ToolTrace]:
    start = time.perf_counter()
    client = create_client(persist_dir)
    try:
        rows = query_collection(client, collection_name, user_query, top_k)
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        trace_rows: List[Dict[str, Any]] = []
        for row in rows:
            md = row.get("metadata", {}) or {}
            trace_rows.append(
                {
                    "id": row.get("id", ""),
                    "collection": row.get("collection", ""),
                    "distance": row.get("distance"),
                    "score": row.get("score"),
                    "source_type": md.get("source_type", ""),
                    "source_title": md.get("source_title", ""),
                    "source_url": md.get("source_url", ""),
                    "chunk_index": md.get("chunk_index"),
                    "chunk_count": md.get("chunk_count"),
                    "content_hash": md.get("content_hash", ""),
                    "document_preview": preview_text(str(row.get("document", "")), 320),
                }
            )
        trace = ToolTrace(
            tool_name=tool_name,
            collection_name=collection_name,
            status="ok" if rows else "empty",
            latency_ms=elapsed_ms,
            requested_top_k=top_k,
            returned_rows=len(rows),
            query=user_query,
            rows=trace_rows,
        )
        return _rows_to_evidence(tool_name, rows), trace
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        trace = ToolTrace(
            tool_name=tool_name,
            collection_name=collection_name,
            status="error",
            latency_ms=elapsed_ms,
            requested_top_k=top_k,
            returned_rows=0,
            query=user_query,
            error=str(exc),
            rows=[],
        )
        return [], trace


def run_llm_orchestration(
    query: str,
    top_k: int,
    max_tool_rounds: int,
    log_dir: str,
    disable_log: bool,
) -> Dict[str, Any]:
    load_dotenv()
    run_id = uuid.uuid4().hex
    started_at_utc = now_utc_iso()

    endpoint = (os.getenv("endpoint") or "").rstrip("/")
    api_key = os.getenv("api_key")
    api_version = os.getenv("api_version", "2024-12-01-preview")
    deployment = os.getenv("gpt_deployment")
    if not endpoint or not api_key or not deployment:
        raise SystemExit("Missing endpoint/api_key/gpt_deployment in .env")

    client = AzureOpenAI(
        api_key=api_key,
        azure_endpoint=endpoint,
        api_version=api_version,
    )

    storage = StorageConfig()
    tool_config = {
        "search_quarterly": {
            "collection": storage.annual_collection,
            "tool_name": "kpn_quarterlyreports_tool",
            "description": "Retrieve evidence from KPN quarterly report collection.",
        },
        "search_news": {
            "collection": storage.news_collection,
            "tool_name": "kpn_news_tool",
            "description": "Retrieve evidence from KPN news collection.",
        },
    }

    llm_tools = []
    for fn_name, cfg in tool_config.items():
        llm_tools.append(
            {
                "type": "function",
                "function": {
                    "name": fn_name,
                    "description": cfg["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "User question or narrowed sub-query."},
                            "top_k": {"type": "integer", "minimum": 1, "maximum": 10},
                        },
                        "required": ["query"],
                    },
                },
            }
        )

    messages = [
        {
            "role": "system",
            "content": (
                "You are an orchestration planner for grounded QA. "
                "Decide which retrieval tools to call. "
                "For final answer, use only tool outputs and do not hallucinate."
            ),
        },
        {"role": "user", "content": query},
    ]

    traces: List[ToolTrace] = []
    selected_tools: List[str] = []
    all_evidence: List[EvidenceItem] = []
    planner_steps: List[Dict[str, Any]] = []

    for _ in range(max_tool_rounds):
        resp = client.chat.completions.create(
            model=deployment,
            messages=messages,
            tools=llm_tools,
            tool_choice="auto",
            temperature=0.0,
        )
        msg = resp.choices[0].message
        messages.append(msg)
        planner_steps.append(
            {
                "phase": "planner",
                "timestamp_utc": now_utc_iso(),
                "tool_calls": [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                    for tc in (msg.tool_calls or [])
                ],
            }
        )

        if not msg.tool_calls:
            break

        for tc in msg.tool_calls:
            fn_name = tc.function.name
            if fn_name not in tool_config:
                continue

            args = json.loads(tc.function.arguments or "{}")
            tool_query = str(args.get("query", query)).strip() or query
            tool_top_k = int(args.get("top_k", top_k))

            cfg = tool_config[fn_name]
            selected_tools.append(cfg["tool_name"])

            evidence, trace = _tool_call_query_collection(
                user_query=tool_query,
                top_k=tool_top_k,
                collection_name=cfg["collection"],
                tool_name=cfg["tool_name"],
                persist_dir=storage.chroma_persist_dir,
            )
            traces.append(trace)
            all_evidence.extend(evidence)

            tool_payload = {
                "tool_name": cfg["tool_name"],
                "status": trace.status,
                "collection": cfg["collection"],
                "returned_rows": trace.returned_rows,
                "evidence": [asdict(e) for e in evidence],
                "error": trace.error,
            }

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": fn_name,
                    "content": json.dumps(tool_payload),
                }
            )
            planner_steps.append(
                {
                    "phase": "tool_response",
                    "timestamp_utc": now_utc_iso(),
                    "tool_name": cfg["tool_name"],
                    "collection": cfg["collection"],
                    "status": trace.status,
                    "returned_rows": trace.returned_rows,
                }
            )

    ranked = sorted(all_evidence, key=lambda x: x.score, reverse=True)
    deduped: List[EvidenceItem] = []
    seen = set()
    for item in ranked:
        key = (item.url, item.title)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    citations = deduped[:6]

    final_prompt = [
        {
            "role": "system",
            "content": (
                "Write a concise grounded answer using ONLY the evidence from tool outputs. "
                "If evidence is insufficient, say that clearly. "
                "Do not invent facts."
            ),
        },
        {"role": "user", "content": query},
        {
            "role": "user",
            "content": json.dumps([asdict(c) for c in citations]),
        },
    ]

    final_resp = client.chat.completions.create(
        model=deployment,
        messages=final_prompt,
        temperature=0.2,
    )
    answer = final_resp.choices[0].message.content or ""

    finished_at_utc = now_utc_iso()
    run_log = {
        "run_id": run_id,
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "query": query,
        "top_k": top_k,
        "max_tool_rounds": max_tool_rounds,
        "selected_tools": list(dict.fromkeys(selected_tools)),
        "citations": [asdict(c) for c in citations],
        "tool_traces": [asdict(t) for t in traces],
        "planner_steps": planner_steps,
        "synthesis_input_citations": [asdict(c) for c in citations],
        "answer": answer,
    }

    if not disable_log:
        summary_jsonl = os.path.join(log_dir, "orchestrator_llm_runs.jsonl")
        append_jsonl(
            summary_jsonl,
            {
                "run_id": run_id,
                "timestamp_utc": finished_at_utc,
                "query": query,
                "selected_tools": list(dict.fromkeys(selected_tools)),
                "tool_calls": len(traces),
                "citations": len(citations),
            },
        )
        run_json = os.path.join(log_dir, "orchestrator_llm", f"{run_id}.json")
        write_json(run_json, run_log)

    return {
        "run_id": run_id,
        "question": query,
        "selected_tools": list(dict.fromkeys(selected_tools)),
        "answer": answer,
        "citations": citations,
        "traces": traces,
        "log_dir": log_dir,
        "logging_enabled": not disable_log,
        "summary_log_path": os.path.join(log_dir, "orchestrator_llm_runs.jsonl"),
        "run_log_path": os.path.join(log_dir, "orchestrator_llm", f"{run_id}.json"),
    }