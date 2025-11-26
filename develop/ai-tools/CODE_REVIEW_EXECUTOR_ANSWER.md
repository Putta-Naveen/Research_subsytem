# Code Analysis: executor() and answer_subquestions()

## 🔴 CRITICAL ISSUE #1: Web Results Are Mixed Across All Subqueries

### The Problem in `executor()`

```python
# ---- Web search per subquestion via MCP ----
for subq in state.subqueries:
    q = Queue()
    threads: List[threading.Thread] = []
    try:
        search_result = await mcp_client.call_tool(...)
        search_text = _extract_text_content(search_result)
        links = _parse_websearch_text(search_text)
        
        for link in links:
            t = threading.Thread(target=expand_and_summarize_web, args=(link, subq, q))
            t.start()
            threads.append(t)
    
    for t in threads:
        t.join()
    while not q.empty():
        aggregated.append(q.get())  # ← Adds results to SHARED aggregated list

state.web_results = _dedupe_by_link(aggregated)  # ← ALL results mixed together
```

**What happens:**
1. Search for Subquery 1 → Get 3 results
2. Add to `aggregated` → `aggregated = [S1-R1, S1-R2, S1-R3]`
3. Search for Subquery 2 → Get 3 results
4. Add to `aggregated` → `aggregated = [S1-R1, S1-R2, S1-R3, S2-R1, S2-R2, S2-R3]`
5. Search for Subquery 3 → Get 3 results
6. Add to `aggregated` → `aggregated = [S1-R1, S1-R2, S1-R3, S2-R1, S2-R2, S2-R3, S3-R1, S3-R2, S3-R3]`

**Result:**
- `state.web_results` now has 9 mixed results from ALL subqueries
- **Lost context about which results came from which subquery!**

---

## 🔴 CRITICAL ISSUE #2: Evidence Context Is NOT Subquery-Specific

### The Problem in `answer_subquestions()`

```python
def answer_subquestions(state: QueryState) -> QueryState:
    web_ctx = _web_context(state.web_results)  # ← Built ONCE from ALL results
    rag_ctx = _rag_context(state)
    
    answers: Dict[str, str] = {}
    for subquery in state.subqueries:
        prompt = f"""
Answer concisely (max 4 sentences).

Subquestion: {subquery}

Evidence:
{web_ctx if web_ctx else "None"}   # ← SAME for ALL subqueries!
{("\nRAG: " + rag_ctx) if rag_ctx else ""}
"""
        resp = gemini_model.generate_content(prompt)
        answers[subquery] = (resp.text or "").strip()
```

**What happens:**
- `web_ctx` built from `state.web_results` (all 9 mixed results)
- ALL 3 subqueries see SAME evidence
- Gemini produces similar answers for all 3

**Example:**
```
All 3 prompts contain:
Evidence:
[1] DVT after femur fracture - ...
[2] PE progression - ...
[3] Vascular changes - ...
[4] Fibrous tissue formation - ...
[5] Surgical immobility - ...
... (all 9 results mixed)

So all subqueries get answered with the same chain of evidence!
```

---

## ✅ Solutions

### Solution A: Store Results Per Subquery (Recommended)

Modify `executor()` to track which results came from which subquery:

```python
async def executor(state: QueryState) -> QueryState:
    logger.info("Executor starting")
    
    # NEW: Map subqueries to their results
    subquery_results: Dict[str, List[Dict[str, Any]]] = {}
    aggregated: List[Dict[str, Any]] = []

    # ---- RAG via MCP ----
    try:
        rag_result = await mcp_client.call_tool(...)
        state.rag_answer = _parse_rag_text_for_answer(rag_text) or "No answer from RAG."
        state.rag_summary = await get_concise_summary(state.rag_answer)
    except Exception as e:
        logger.error(f"RAG MCP Error: {e}")
        state.rag_answer = f"RAG MCP Error: {e}"
        state.rag_summary = "RAG summary failed."

    # ---- Web search per subquestion via MCP ----
    for subq in state.subqueries:
        q = Queue()
        threads: List[threading.Thread] = []
        subquery_results[subq] = []  # NEW: Track per-subquery results
        
        try:
            logger.info(f"Calling Search MCP for: {subq}")
            search_result = await mcp_client.call_tool(
                MCP_SEARCH_SERVER_URL, "web_search", {"query": subq, "count": SUBQ_SEARCH_COUNT}
            )
            search_text = _extract_text_content(search_result)
            links = _parse_websearch_text(search_text)
            links = [l for l in links if _allowed(l.get("link", "") or l.get("url", ""))][:SUBQ_SEARCH_COUNT]
            
            for link in links:
                t = threading.Thread(target=expand_and_summarize_web, args=(link, subq, q))
                t.start()
                threads.append(t)
        except Exception as e:
            logger.error(f"Search MCP error ({subq}): {e}")
            aggregated.append({"title": subq, "link": "", "summary": f"Search MCP error: {e}"})

        for t in threads:
            t.join()
        
        # NEW: Store results per subquery AND in aggregated
        while not q.empty():
            result = q.get()
            subquery_results[subq].append(result)  # NEW: Track per subquery
            aggregated.append(result)

    # Store both mappings in state
    state.web_results = _dedupe_by_link(aggregated)
    state.subquery_results = subquery_results  # NEW: Add to state
    
    for i, r in enumerate(state.web_results[:MAX_SOURCES_FOR_CITATIONS]):
        r["n"] = i + 1
    
    logger.info(f"Executor completed: {len(state.web_results)} web results")
    return state
```

Then modify `answer_subquestions()`:

```python
def answer_subquestions(state: QueryState) -> QueryState:
    rag_ctx = _rag_context(state)
    answers: Dict[str, str] = {}
    
    for subquery in state.subqueries:
        # NEW: Get evidence SPECIFIC to this subquery
        subq_specific_results = state.subquery_results.get(subquery, [])
        
        # Build context from this subquery's results
        web_ctx = _web_context(subq_specific_results)
        
        prompt = f"""
Answer concisely (max 4 sentences).
Use ONLY the Evidence below; add inline citations like [1].

Parent Question: "{state.question}"
Subquestion: {subquery}

Evidence (from search for this subquestion):
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
                    _sleep_backoff()
                else:
                    answers[subquery] = f"Gemini error: {e}"
                    break
    
    state.answers = answers
    return state
```

---

### Solution B: Filter Evidence Per Subquery (Lightweight)

If you don't want to modify `executor()`, filter in `answer_subquestions()`:

```python
def is_relevant_to_subquery(evidence_item: Dict, subquery: str) -> bool:
    """Check if evidence is relevant to subquery via keyword overlap."""
    content = f"{evidence_item.get('title', '')} {evidence_item.get('summary', '')}"
    subq_words = set(w.lower() for w in subquery.split() if len(w) > 3)
    content_words = set(w.lower() for w in content.split())
    
    if not subq_words:
        return True
    
    overlap = len(subq_words & content_words)
    return overlap >= 2  # At least 2 keyword matches

def answer_subquestions(state: QueryState) -> QueryState:
    rag_ctx = _rag_context(state)
    answers: Dict[str, str] = {}
    
    for subquery in state.subqueries:
        # NEW: Filter results relevant to this subquery
        relevant_results = [
            r for r in state.web_results 
            if is_relevant_to_subquery(r, subquery)
        ]
        
        # If no relevant results, use all (fallback)
        if not relevant_results:
            relevant_results = state.web_results
        
        web_ctx = _web_context(relevant_results[:MAX_EVIDENCE_SNIPPETS])
        
        prompt = f"""
Answer concisely (max 4 sentences).

Subquestion: {subquery}

Evidence (filtered for this subquestion):
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
                    _sleep_backoff()
                else:
                    answers[subquery] = f"Gemini error: {e}"
                    break
    
    state.answers = answers
    return state
```

---

## Comparison

| Aspect | Solution A | Solution B |
|--------|-----------|-----------|
| **Accuracy** | Perfect - exact results | Good - keyword-based filtering |
| **Implementation** | Modify `executor()` + `answer_subquestions()` | Modify only `answer_subquestions()` |
| **Performance** | Same | Same |
| **Complexity** | Medium | Low |
| **Data Tracking** | Explicit per-subquery mapping | Implicit filtering |

---

## Recommendation

**Use Solution A** because:
1. ✅ Gives Gemini the EXACT results for each subquery
2. ✅ Cleaner data flow - no guessing which results are relevant
3. ✅ Better for citations - results are clearly tied to subqueries
4. ✅ Easier to debug - can see what evidence each subquery got

---

## Expected Results After Fix

**Before:**
```
Subquery 1: "Causes of fibrous tissue?"
→ Answer: DVT → PE → vascular changes → fibrous tissue

Subquery 2: "Effect of surgery?"
→ Answer: DVT → PE → vascular changes → intimal fibrosis

Subquery 3: "Sequelae of immobility?"
→ Answer: DVT → PE → vascular changes → pulmonary hypertension
```
(All similar)

**After:**
```
Subquery 1: "Causes of fibrous tissue?"
→ Answer: [Results specific to tissue formation pathophysiology]
→ Answer: Endothelial injury + inflammation + fibroblast proliferation...

Subquery 2: "Effect of surgery?"
→ Answer: [Results specific to post-surgical complications]
→ Answer: Surgical trauma + extended immobility + hypercoagulability...

Subquery 3: "Sequelae of immobility?"
→ Answer: [Results specific to immobility effects]
→ Answer: Venous stasis + muscle atrophy + metabolic dysfunction...
```
(All diverse and specific!)
