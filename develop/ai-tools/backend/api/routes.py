"""
API routes for the AI Tools backend.
"""

import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request
from langgraph.graph import StateGraph

from models import QueryState, ClientRequest, ClientResponse

# Initialize logger
logger = logging.getLogger("API")

def create_app(compiled_graph, config=None):
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(title="Medical Agentic AI Research Subsystem", version="1.5")
    
    # Use the configuration
    MAX_LOOPS = config.get("MAX_LOOPS", 3) if config else 3
    MIN_OVERALL = config.get("MIN_OVERALL", 0.7) if config else 0.7
    
    @app.post("/mcp/runLanggraph", response_model=ClientResponse, tags=["LangGraph"])
    async def run_pipeline(request_body: ClientRequest, request: Request):
        try:
            initial = QueryState(question=request_body.query)
            final: Optional[QueryState] = None

            async for step in compiled_graph.astream(initial, config={"recursion_limit": MAX_LOOPS * 8}):
                node, raw = list(step.items())[0]
                final = QueryState(**raw)
                logger.info(f"Node: {node} | Loop: {final.loop_count} | Eval: {final.evaluation} | Overall: {final.scores.overall if final.scores else 'NA'}")
                if final.scores and final.scores.overall >= MIN_OVERALL and not final.scores.replan_needed:
                    break
                if final.evaluation == "yes":
                    break

            if not final:
                raise RuntimeError("Pipeline produced no final state")

            return ClientResponse(
                question=final.question,
                summary=final.summary,
                rag_answer=final.rag_answer,
                rag_summary=final.rag_summary,
                web_results=final.web_results,        # includes n=1..k so [1],[2] map by position
                subqueries=final.subqueries,
                subquery_answers=final.answers,
                final_answer=final.final_answer,
                evaluation=final.evaluation,
                feedback=final.feedback,
                rubric=final.scores
            )
        except Exception as e:
            logger.error(f"LangGraph failed: {e}")
            raise HTTPException(status_code=500, detail=f"LangGraph failed: {e}")
    
    return app
