from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, ConfigDict
import os
from dotenv import load_dotenv
load_dotenv()

# Get environment variables
END_USER_ID = os.getenv("END_USER_ID")

class EvalRubric(BaseModel):
    coverage: float = 0.0
    grounding: float = 0.0
    coherence: float = 0.0
    overall: float = 0.0
    replan_needed: bool = False
    critique: str = ""

class QueryState(BaseModel):
    question: str
    summary: str = ""
    subqueries: List[str] = Field(default_factory=list)
    answers: Dict[str, str] = Field(default_factory=dict)
    final_answer: str = ""
    evaluation: str = ""                 # "yes"/"no"
    evaluation_reason: str = ""
    feedback: str = ""
    previous_subqueries: List[str] = Field(default_factory=list)
    bad_subqueries: List[str] = Field(default_factory=list)
    loop_count: int = 0
    web_results: List[Dict[str, Any]] = Field(default_factory=list)  # sources with n=1..k
    rag_answer: str = ""
    rag_summary: str = ""
    scores: Optional[EvalRubric] = None

# ---- Request model: ONLY these two fields appear in Swagger ----
class ClientRequest(BaseModel):
    query: str
    end_user_id: str = END_USER_ID

    # Pydantic v2 replacement for schema_extra
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "query": "string",
                "end_user_id": "test-user"
            }
        }
    )

# ---- Response model  ----
class ClientResponse(BaseModel):
    question: str
    summary: str
    rag_answer: str
    rag_summary: str
    web_results: List[Dict[str, Any]]
    subqueries: List[str]
    subquery_answers: Dict[str, str]
    final_answer: str
    evaluation: str
    feedback: str
    rubric: Optional[EvalRubric] = None
