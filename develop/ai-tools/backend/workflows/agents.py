
import json
import logging
import threading
import asyncio
from queue import Queue
import httpx
from typing import List, Dict, Optional, Any

import google.generativeai as genai
from utils import (
    sleep_backoff, allowed_url, expand_and_summarize_web, 
    web_context, rag_context, dedupe_by_link
)

from models import EvalRubric, QueryState, ClientRequest, ClientResponse

# Get logger
logger = logging.getLogger("LangGraphNodes")

# These will be initialized from app.py
gemini_model = None
gemini_json = None
GENAI_RAG_URL = None
GENAI_RAG_TOKEN = None
MCP_SEARCH_URL = None
GOOGLE_API_KEY = None
GOOGLE_CSE_ID = None
END_USER_ID = None
SUBQ_SEARCH_COUNT = None
MAX_SOURCES_FOR_CITATIONS = None
MAX_EVIDENCE_SNIPPETS = None
MIN_OVERALL = None
MAX_LOOPS = None

def configure_nodes(config):
    """Configure the node functions with global variables."""
    global gemini_model, gemini_json, GENAI_RAG_URL, GENAI_RAG_TOKEN
    global MCP_SEARCH_URL, GOOGLE_API_KEY, GOOGLE_CSE_ID, END_USER_ID, SUBQ_SEARCH_COUNT
    global MAX_SOURCES_FOR_CITATIONS, MAX_EVIDENCE_SNIPPETS
    global MIN_OVERALL, MAX_LOOPS
    
    gemini_model = config.get("gemini_model")
    gemini_json = config.get("gemini_json")
    GENAI_RAG_URL = config.get("GENAI_RAG_URL")
    GENAI_RAG_TOKEN = config.get("GENAI_RAG_TOKEN")
    MCP_SEARCH_URL = config.get("MCP_SEARCH_URL")
    GOOGLE_API_KEY = config.get("GOOGLE_API_KEY")
    GOOGLE_CSE_ID = config.get("GOOGLE_CSE_ID")
    END_USER_ID = config.get("END_USER_ID")
    SUBQ_SEARCH_COUNT = config.get("SUBQ_SEARCH_COUNT")
    MAX_SOURCES_FOR_CITATIONS = config.get("MAX_SOURCES_FOR_CITATIONS")
    MAX_EVIDENCE_SNIPPETS = config.get("MAX_EVIDENCE_SNIPPETS")
    MIN_OVERALL = config.get("MIN_OVERALL")
    MAX_LOOPS = config.get("MAX_LOOPS")

def search_with_google_cse(query: str, num_results: int = 5) -> List[Dict[str, Any]]:
    """
    Search using Google Custom Search Engine API.
    Results are automatically filtered to configured domains in CSE.
    
    Args:
        query: Search query
        num_results: Number of results to return
        
    Returns:
        List of search results with title, link, snippet
    """
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "q": query,
            "cx": GOOGLE_CSE_ID,
            "key": GOOGLE_API_KEY,
            "num": min(num_results, 10)  # Google CSE allows max 10 per request
        }
        
        response = httpx.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        
        results = []
        for item in data.get("items", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "url": item.get("link", ""),  # For compatibility
                "snippet": item.get("snippet", "")
            })
        
        logger.info(f"Google CSE search for '{query}' returned {len(results)} results")
        return results
        
    except Exception as e:
        logger.error(f"Google CSE search error for '{query}': {e}")
        return []


def structured_summarizer(state: QueryState) -> QueryState:
    prompt = f"""
Summarize this medical question clearly:
Question: {state.question}
Extract:
- Condition
- Symptoms
- Tests/Treatments
- Core Clinical Goal
Strict output format:
- Condition:
- Symptoms:
- Tests/Treatments:
- Core Clinical Goal:
"""
    for attempt in range(3):
        try:
            resp = gemini_model.generate_content(prompt)
            state.summary = (resp.text or "").strip()
            return state
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                logger.warning("Rate limit in structured_summarizer; retry 45s")
                sleep_backoff()
            else:
                logger.error(f"Gemini API error: {e}")
                state.summary = f"Error: {e}"; return state

def planner(state: QueryState) -> QueryState:
    avoid = list(set(state.previous_subqueries + state.bad_subqueries))
    web_ctx = web_context(state.web_results) if state.web_results else ""
    rag_ctx = rag_context(state)

    prompt = f"""
Generate 3-5 subquestions to answer the main query:
"{state.question}"

Use (if present):
- Structured Summary: {state.summary}
- Web Search Results: {web_ctx if web_ctx else "None"}
- RAG Results: {rag_ctx if rag_ctx else "None"}
- Feedback: "{state.feedback if state.feedback else 'None'}"

Avoid repeating:
{chr(10).join(['- ' + a for a in avoid]) if avoid else 'None'}

Output: Numbered list of distinct, feasible, medically valid subquestions.
"""
    for attempt in range(3):
        try:
            resp = gemini_model.generate_content(prompt)
            state.previous_subqueries = state.subqueries
            state.subqueries = [
                line.strip("0123456789. ").strip()
                for line in (resp.text or "").splitlines()
                if line.strip() and not line.lower().startswith("here are")
            ]
            return state
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                logger.warning("Rate limit in planner; retry 45s")
                sleep_backoff()
            else:
                logger.error(f"Gemini API error: {e}")
                state.subqueries = []
                return state

async def executor(state: QueryState) -> QueryState:
    logger.info(" Executor starting")
    aggregated: List[Dict[str, Any]] = []

    # ---- RAG on the parent question ----
    try:
        logger.info(f"Starting RAG request with URL: {GENAI_RAG_URL}")
        headers = {"Authorization": f"Bearer {GENAI_RAG_TOKEN}"} if GENAI_RAG_TOKEN else None
        rag_res = httpx.post(GENAI_RAG_URL, json={"query": state.question, "end_user_id": END_USER_ID},
                             headers=headers, timeout=35)
        logger.info(f"RAG response status: {rag_res.status_code}")
        rag_res.raise_for_status()
        rag_data = rag_res.json()
        logger.info(f"RAG response received, keys: {rag_data.keys()}")
        state.rag_answer  = rag_data.get("output_text", "No answer from RAG.")
        logger.info(f"RAG answer extracted, length: {len(state.rag_answer)}")
        # Get summary but don't wait forever - use short timeout
        try:
            logger.info("Starting summary generation...")
            state.rag_summary = await asyncio.wait_for(get_concise_summary(state.rag_answer), timeout=15)
            logger.info(f"Summary generated: {state.rag_summary[:100]}")
        except asyncio.TimeoutError:
            logger.warning("RAG summary generation timed out, using truncated answer")
            state.rag_summary = (state.rag_answer[:200] + "...") if state.rag_answer else "No summary available"
    except Exception as e:
        logger.error(f"RAG Error: {e}")
        state.rag_answer = f"RAG Error: {e}"
        state.rag_summary = "RAG summary failed."

    # ---- Per-subquestion search + page expansion (parallel) ----
    for subq in state.subqueries:
        q = Queue(); threads: List[threading.Thread] = []
        try:
            # Use Google CSE API (results already filtered by configured domains)
            links = search_with_google_cse(subq, SUBQ_SEARCH_COUNT)
            
            # No need to filter by allowed_url() anymore - Google CSE already filters
            # But we keep the call for backward compatibility (it now always returns True)
            links = [l for l in links if allowed_url(l.get("link","") or l.get("url",""))][:SUBQ_SEARCH_COUNT]
            
            for link in links:
                t = threading.Thread(target=expand_and_summarize_web, args=(link, subq, q))
                t.start(); threads.append(t)
        except Exception as e:
            logger.error(f"Websearch error ({subq}): {e}")
            aggregated.append({"title": subq, "link": "", "summary": f"Websearch error: {e}"})

        for t in threads: t.join()
        while not q.empty():
            aggregated.append(q.get())

    # Deduplicate and number sources for citation mapping
    state.web_results = dedupe_by_link(aggregated)
    for i, r in enumerate(state.web_results[:MAX_SOURCES_FOR_CITATIONS]):  # add n=1..k
        r["n"] = i + 1
    return state

def answer_subquestions(state: QueryState) -> QueryState:
    web_ctx = web_context(state.web_results)
    rag_ctx = rag_context(state)

    answers: Dict[str, str] = {}
    for subquery in state.subqueries:
        prompt = f"""
Answer concisely (max 4 sentences).
Use ONLY the Evidence below; add inline citations like [1] using the numbered list.

Parent Question: "{state.question}"
Subquestion: {subquery}

Evidence:
{web_ctx if web_ctx else "None"}
{("\nRAG: " + rag_ctx) if rag_ctx else ""}
"""
        for attempt in range(3):
            try:
                resp = gemini_model.generate_content(prompt)
                answers[subquery] = (resp.text or "").strip()
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    logger.warning(f"Rate limit answering subq '{subquery}'; retry 45s")
                    sleep_backoff()
                else:
                    logger.error(f"Gemini error for subq '{subquery}': {e}")
                    answers[subquery] = f"Gemini error: {e}"
                    break
    state.answers = answers
    return state

def synthesizer(state: QueryState) -> QueryState:
    # Build numbered source list and snippets
    sources = state.web_results[:MAX_SOURCES_FOR_CITATIONS]
    sources_list_text = "\n".join([f"[{s.get('n')}] {s.get('title','Source')} — {s.get('link') or s.get('url','')}" for s in sources])
    evidence_snips = "\n\n".join([f"[{s.get('n')}] Summary: {(s.get('summary','') or '')[:500]}" for s in sources[:MAX_EVIDENCE_SNIPPETS]])
    rag_ctx = f"RAG Summary: {state.rag_summary}" if state.rag_summary else ""

    prompt = f"""
You are writing a concise, evidence-grounded medical answer.

Question:
{state.question}

Evidence snippets (cite ONLY these numbers):
{evidence_snips}

Sources list (use these numbers for inline citations):
{sources_list_text}

Rules:
- Base claims ONLY on the evidence snippets above.
- Add inline citations like [1], [2] matching the numbered Sources list.
- If evidence is insufficient, state the gap explicitly.
- Max 3 sentences.
{rag_ctx}
"""
    for attempt in range(3):
        try:
            resp = gemini_model.generate_content(prompt)
            state.final_answer = (resp.text or "").strip()
            return state
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                logger.warning("Rate limit in synthesizer; retry 45s")
                sleep_backoff()
            else:
                logger.error(f"Gemini API error: {e}")
                state.final_answer = f"Error: {e}"; return state

def evaluator(state: QueryState) -> QueryState:
    state.loop_count += 1
    ev = [{
        "title": r.get("title", ""),
        "url":   r.get("link", "") or r.get("url",""),
        "summary": (r.get("summary", "") or "")[:600]
    } for r in state.web_results[:MAX_EVIDENCE_SNIPPETS]]

    prompt = f"""
Return STRICT JSON with keys:
coverage (0..1), grounding (0..1), coherence (0..1), overall (0..1), replan_needed (true/false), critique (string).

Question: {state.question}
Final Answer: {state.final_answer}
Evidence: {json.dumps(ev, ensure_ascii=False)}
"""
    for attempt in range(3):
        try:
            raw = (gemini_json.generate_content(prompt).text or "").strip()
            if not raw: raise ValueError("Empty eval response")
            try:
                data = json.loads(raw)
            except Exception:
                fixed = (gemini_json.generate_content(f"Return valid JSON only (no prose):\n{raw}").text or "").strip()
                data = json.loads(fixed)

            logger.info(f"Rubric JSON: {data}")  # <-- Added logging for rubric

            rubric = EvalRubric(
                coverage=float(data.get("coverage", 0.0)),
                grounding=float(data.get("grounding", 0.0)),
                coherence=float(data.get("coherence", 0.0)),
                overall=float(data.get("overall", 0.0)),
                replan_needed=bool(data.get("replan_needed", False)),
                critique=str(data.get("critique", "")),
            )
            state.scores = rubric

            if rubric.overall >= MIN_OVERALL:
                state.evaluation, state.feedback, state.bad_subqueries = "yes", "", []
            else:
                state.evaluation = "no"
                state.feedback = rubric.critique or "Needs improvement"
                state.bad_subqueries = state.subqueries.copy()
            return state

        except Exception as e:
            if "429" in str(e) and attempt < 2:
                logger.warning("Rate limit in evaluator; retry 45s")
                sleep_backoff()
            else:
                logger.error(f"Evaluator error: {e}")
                state.scores = EvalRubric(overall=0.0, replan_needed=True, critique=f"Evaluation failed: {e}")
                state.evaluation = "no"
                state.feedback = state.scores.critique
                state.bad_subqueries = state.subqueries.copy()
                return state

def should_replan(state: QueryState) -> str:
    if state.loop_count >= MAX_LOOPS:
        return "end"
    # Only replan if overall score is less than MIN_OVERALL
    if state.scores and state.scores.overall < MIN_OVERALL:
        return "replan"
    return "end"

# This function is missing from utils and needs to be here temporarily
async def get_concise_summary(text: str) -> str:
    for attempt in range(3):
        try:
            prompt = f"Provide a very concise summary (max 50 words) of the following text:\n\n{(text or '')[:2000]}"
            logger.info(f"get_concise_summary prompt: {prompt}")
            resp = await gemini_model.generate_content_async(prompt)
            logger.info(f"get_concise_summary response: {resp}")
            return (resp.text or "").strip()
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                logger.warning("Rate limit in get_concise_summary; retry in 45s")
                sleep_backoff()
            else:
                logger.error(f"Gemini concise summarization error: {e}")
                logger.error(f"get_concise_summary input text: {text}")
                return "Summary not available due to API error."
