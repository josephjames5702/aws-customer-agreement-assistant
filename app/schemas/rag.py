from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class AskRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="The user query to search the AWS Customer Agreement."
    )

    @field_validator('query', mode='before')
    @classmethod
    def trim_whitespace(cls, v: str) -> str:
        if isinstance(v, str):
            return v.strip()
        return v

class Source(BaseModel):
    chunk_id: str
    page: int
    text_snippet: str
    similarity_score: float

# Maintain SourceChunk as an alias for backwards compatibility
SourceChunk = Source

class AskResponse(BaseModel):
    query: str
    answer: str
    answer_found: bool
    sources: List[Source]
    response_time_ms: float
    model_used: str

class IngestRequest(BaseModel):
    force: bool = Field(default=False, description="Re-ingest even if index already exists.")

class IngestResponse(BaseModel):
    status: str
    chunks_created: int
    embedding_model: str
    message: str

class TopQuestion(BaseModel):
    query: str
    frequency: int

class UnansweredQuery(BaseModel):
    query: str
    created_at: datetime

class QueryVolumeHour(BaseModel):
    hour: str
    queries: int

class AnalyticsResponse(BaseModel):
    total_queries: int
    average_response_time_ms: float
    unanswered_queries: List[UnansweredQuery]
    top_5_questions: List[TopQuestion]
    
    # Extra compatibility fields matching the PRD
    answer_found_rate_pct: float
    min_latency_ms: float
    max_latency_ms: float
    top_queries: List[TopQuestion]
    unanswerable_queries: List[UnansweredQuery]
    query_volume_by_hour: List[QueryVolumeHour]


