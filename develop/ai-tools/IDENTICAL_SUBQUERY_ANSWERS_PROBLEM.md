# Problem: Identical Subquery Answers

## Root Cause Identified

The issue is in the **`answer_subquestions()` function** (lines 224-254 in `backend/workflows/agents.py`).

### The Bug

```python
def answer_subquestions(state: QueryState) -> QueryState:
    web_ctx = web_context(state.web_results)  # ← Built ONCE
    rag_ctx = rag_context(state)              # ← Built ONCE
    
    answers: Dict[str, str] = {}
    for subquery in state.subqueries:
        prompt = f"""
Answer concisely (max 4 sentences).
Parent Question: "{state.question}"
Subquestion: {subquery}

Evidence:
{web_ctx if web_ctx else "None"}  # ← SAME for ALL subqueries
{("\nRAG: " + rag_ctx) if rag_ctx else ""}
"""
        # Call Gemini with identical evidence for each subquery
        resp = gemini_model.generate_content(prompt)
        answers[subquery] = (resp.text or "").strip()
```

### Why This Happens

1. **Evidence built once globally** (`web_ctx`, `rag_ctx`)
   - Contains ALL web results + RAG answer
   - NOT specific to each subquery

2. **Same evidence for all subqueries**
   - All 3 subqueries get same context
   - Gemini sees same information for each prompt
   - Results in similar/identical answers

3. **No query-specific search**
   - Even though each subquery is different
   - The evidence context doesn't change
   - So answers tend to converge

### Example

```
Subquery 1: "What are the potential causes of fibrous tissue formation?"
→ Evidence: [All 10 web results about DVT, PE, vascular changes]
→ Answer: "DVT → PE → vascular changes → fibrous tissue formation"

Subquery 2: "How might surgical intervention contribute?"
→ Evidence: [SAME 10 web results]
→ Answer: "DVT → PE → vascular changes → intimal fibrosis"

Subquery 3: "What are common sequelae of immobility?"
→ Evidence: [SAME 10 web results]
→ Answer: "DVT → PE → vascular changes → pulmonary hypertension"
```

All answers follow the same evidence chain!

---

## Solution: Make Evidence Subquery-Specific

### Option 1: Filter Evidence Per Subquery (Recommended)
```python
def answer_subquestions(state: QueryState) -> QueryState:
    answers: Dict[str, str] = {}
    
    for subquery in state.subqueries:
        # Build evidence SPECIFIC to this subquery
        # Filter web_results for relevance to THIS subquery
        relevant_results = [r for r in state.web_results 
                          if is_relevant_to_subquery(r, subquery)]
        
        web_ctx = web_context(relevant_results[:MAX_EVIDENCE_SNIPPETS])
        rag_ctx = rag_context(state)  # Keep RAG (general knowledge)
        
        prompt = f"""
Answer concisely.
Subquestion: {subquery}

Evidence (filtered for this subquery):
{web_ctx}
{("\nRAG: " + rag_ctx) if rag_ctx else ""}
"""
        resp = gemini_model.generate_content(prompt)
        answers[subquery] = (resp.text or "").strip()
    
    state.answers = answers
    return state

def is_relevant_to_subquery(result: Dict, subquery: str) -> bool:
    """Check if result is relevant to subquery."""
    content = f"{result.get('title','')} {result.get('summary','')}"
    # Simple keyword overlap
    subq_words = set(subquery.lower().split())
    content_words = set(content.lower().split())
    overlap = len(subq_words & content_words) / len(subq_words)
    return overlap > 0.3  # At least 30% keyword overlap
```

### Option 2: Re-Search Web Per Subquery
```python
def answer_subquestions(state: QueryState) -> QueryState:
    answers: Dict[str, str] = {}
    
    for subquery in state.subqueries:
        # Do a NEW search specific to this subquery
        subq_results = search_with_google_cse(subquery, num_results=5)
        
        # Expand and summarize these results
        for result in subq_results:
            expand_and_summarize_web(result, subquery, results_queue)
        
        web_ctx = web_context(results_for_subquery)
        rag_ctx = rag_context(state)
        
        prompt = f"""
Answer concisely.
Subquestion: {subquery}

Evidence:
{web_ctx}
{("\nRAG: " + rag_ctx) if rag_ctx else ""}
"""
        resp = gemini_model.generate_content(prompt)
        answers[subquery] = (resp.text or "").strip()
    
    state.answers = answers
    return state
```

### Option 3: Expand the Full Evidence Collection
(Keep current approach but ADD per-subquery searches during executor)

```python
# In executor() - for EACH subquery, search AND expand
async def executor(state: QueryState) -> QueryState:
    # ... existing RAG code ...
    
    # NEW: Build evidence map per subquery
    subquery_evidence = {}
    
    for subquery in state.subqueries:
        # Search for THIS subquery
        links = search_with_google_cse(subquery, SUBQ_SEARCH_COUNT)
        
        # Expand THIS subquery's results
        subq_results = []
        for link in links:
            result = expand_and_summarize_web(link, subquery, ...)
            subq_results.append(result)
        
        subquery_evidence[subquery] = subq_results
    
    state.subquery_evidence = subquery_evidence
    return state

# In answer_subquestions() - use subquery-specific evidence
def answer_subquestions(state: QueryState) -> QueryState:
    answers: Dict[str, str] = {}
    
    for subquery in state.subqueries:
        # Use evidence SPECIFIC to this subquery
        subq_results = state.subquery_evidence.get(subquery, [])
        web_ctx = web_context(subq_results)
        rag_ctx = rag_context(state)
        
        prompt = f"""
Answer: {subquery}
Evidence: {web_ctx}
"""
        resp = gemini_model.generate_content(prompt)
        answers[subquery] = (resp.text or "").strip()
    
    state.answers = answers
    return state
```

---

## Which Solution to Use?

| Option | Pros | Cons |
|--------|------|------|
| **Option 1** (Filter Evidence) | Fast, uses existing searches | Might miss relevant results |
| **Option 2** (Re-Search) | Most accurate per-subquery answers | 3x more API calls, slower |
| **Option 3** (Expand Storage) | Balanced, captures both global + local | Requires model change |

**Recommendation:** Start with **Option 1** (filter evidence), then upgrade to **Option 2** if quality isn't good enough.

---

## Implementation Steps for Option 1

1. Add helper function to `web_utils.py`:
```python
def is_relevant_to_query(text: str, query: str, threshold: float = 0.3) -> bool:
    """Check keyword overlap between text and query."""
    text_words = set(text.lower().split())
    query_words = set(query.lower().split())
    if not query_words:
        return True
    overlap = len(text_words & query_words) / len(query_words)
    return overlap >= threshold
```

2. Modify `answer_subquestions()` in `agents.py`:
```python
def answer_subquestions(state: QueryState) -> QueryState:
    answers: Dict[str, str] = {}
    rag_ctx = rag_context(state)
    
    for subquery in state.subqueries:
        # Filter results for THIS subquery
        relevant = [r for r in state.web_results 
                   if is_relevant_to_query(
                       r.get('title','') + ' ' + r.get('summary',''),
                       subquery
                   )]
        
        web_ctx = web_context(relevant[:MAX_EVIDENCE_SNIPPETS])
        
        prompt = f"""..."""
        resp = gemini_model.generate_content(prompt)
        answers[subquery] = (resp.text or "").strip()
    
    state.answers = answers
    return state
```

This ensures each subquery gets **relevant evidence**, not just **all evidence**.
