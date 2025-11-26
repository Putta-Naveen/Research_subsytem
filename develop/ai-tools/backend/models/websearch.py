from typing import Dict, List, Optional
from pydantic import BaseModel

# Data models for WebSearch API
class StatusResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    services: Dict[str, str]

class SearchRequest(BaseModel):
    query: str
    count: Optional[int] = None
    cse_id: Optional[str] = None

class SearchResult(BaseModel):
    title: str
    snippet: str
    link: str

class SearchResponse(BaseModel):
    results: list[SearchResult]
