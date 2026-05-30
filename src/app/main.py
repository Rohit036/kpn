from dataclasses import asdict
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.services.llm_service import run_llm_orchestration


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User question")
    top_k: int = Field(default=4, ge=1, le=10)
    max_tool_rounds: int = Field(default=2, ge=1, le=5)
    log_dir: str = Field(default="data/logs")
    disable_log: bool = Field(default=False)


class QueryResponse(BaseModel):
    run_id: str
    question: str
    selected_tools: List[str]
    answer: str
    citations: List[Dict[str, Any]]
    run_log_path: str


app = FastAPI(title="KPN Agent API", version="0.1.0")


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/query", response_model=QueryResponse)
def query(payload: QueryRequest) -> QueryResponse:
    try:
        result = run_llm_orchestration(
            query=payload.query,
            top_k=payload.top_k,
            max_tool_rounds=payload.max_tool_rounds,
            log_dir=payload.log_dir,
            disable_log=payload.disable_log,
        )
    except SystemExit as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"query failed: {exc}") from exc

    citations = [asdict(item) for item in result.get("citations", [])]
    return QueryResponse(
        run_id=result.get("run_id", ""),
        question=result.get("question", payload.query),
        selected_tools=result.get("selected_tools", []),
        answer=result.get("answer", ""),
        citations=citations,
        run_log_path=result.get("run_log_path", ""),
    )
