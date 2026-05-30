from dataclasses import dataclass


@dataclass(frozen=True)
class CrawlConfig:
    seed_url: str = "https://www.overons.kpn/nieuws/en"
    allowed_domain: str = "overons.kpn"
    max_pages: int = 30
    max_depth: int = 2
    request_delay_sec: float = 1.0
    min_text_length: int = 200
    user_agent: str = "kpn-assignment-crawler/0.1 (educational project)"


@dataclass(frozen=True)
class ChunkConfig:
    chunk_size: int = 1200
    chunk_overlap: int = 200


@dataclass(frozen=True)
class StorageConfig:
    docs_output_file: str = "data/raw/kpn_news_raw.jsonl"
    chunks_output_file: str = "data/processed/kpn_news_chunks.jsonl"
    quarterly_docs_output_file: str = "data/raw/kpn_quarterly_raw.jsonl"
    quarterly_chunks_output_file: str = "data/processed/kpn_quarterly_chunks.jsonl"
    chroma_persist_dir: str = "data/vector_store/chroma_store"
    news_collection: str = "kpnnews"
    annual_collection: str = "kpnquarterlyreports"
