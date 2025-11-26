# Visual Comparison: Before vs After Fix

## 🔴 BEFORE (Current - Wrong)

```
executor():
  
  For Subquery 1: "Causes of fibrous tissue?"
  └─ Search Google CSE
  └─ Get: [DVT-article, PE-article, tissue-article]
  └─ aggregated = [DVT-article, PE-article, tissue-article]
  
  For Subquery 2: "Effect of surgery?"
  └─ Search Google CSE
  └─ Get: [surgery-article, immobility-article, vascular-article]
  └─ aggregated = [DVT-article, PE-article, tissue-article, 
                   surgery-article, immobility-article, vascular-article]
  
  For Subquery 3: "Sequelae of immobility?"
  └─ Search Google CSE
  └─ Get: [immobility-article, sequelae-article, complications-article]
  └─ aggregated = [DVT-article, PE-article, tissue-article,
                   surgery-article, immobility-article, vascular-article,
                   immobility-article, sequelae-article, complications-article]
  
  state.web_results = deduplicated(aggregated)
  └─ Result: 8-9 random articles mixed together
  └─ NO TRACKING of which came from which subquery!

answer_subquestions():
  
  web_ctx = _web_context(state.web_results)
           = [All 8-9 articles listed together]
  
  For Subquery 1: "Causes of fibrous tissue?"
    ├─ Evidence: [All 8-9 articles]
    ├─ Gemini sees: DVT → PE → vascular changes → fibrous tissue
    └─ Answer: "DVT leads to PE, which causes vascular changes..."
  
  For Subquery 2: "Effect of surgery?"
    ├─ Evidence: [SAME All 8-9 articles]
    ├─ Gemini sees: DVT → PE → vascular changes → fibrous tissue
    └─ Answer: "DVT leads to PE, which causes vascular changes..."
  
  For Subquery 3: "Sequelae of immobility?"
    ├─ Evidence: [SAME All 8-9 articles]
    ├─ Gemini sees: DVT → PE → vascular changes → fibrous tissue
    └─ Answer: "DVT leads to PE, which causes vascular changes..."

RESULT: All 3 answers nearly identical! ❌
```

---

## ✅ AFTER (Fixed - Correct)

```
executor():
  
  subquery_results = {}
  aggregated = []
  
  For Subquery 1: "Causes of fibrous tissue?"
  ├─ Search Google CSE
  ├─ Get: [DVT-article, PE-article, tissue-article]
  ├─ subquery_results["Causes of fibrous tissue?"] = [DVT, PE, tissue]
  └─ aggregated = [DVT, PE, tissue]
  
  For Subquery 2: "Effect of surgery?"
  ├─ Search Google CSE
  ├─ Get: [surgery-article, immobility-article, vascular-article]
  ├─ subquery_results["Effect of surgery?"] = [surgery, immobility, vascular]
  └─ aggregated = [DVT, PE, tissue, surgery, immobility, vascular]
  
  For Subquery 3: "Sequelae of immobility?"
  ├─ Search Google CSE
  ├─ Get: [immobility-article, sequelae-article, complications-article]
  ├─ subquery_results["Sequelae of immobility?"] = [immobility, sequelae, complications]
  └─ aggregated = [DVT, PE, tissue, surgery, immobility, vascular,
                   immobility, sequelae, complications]
  
  state.web_results = deduplicated(aggregated)
  state.subquery_results = subquery_results  ← TRACKING!

answer_subquestions():
  
  For Subquery 1: "Causes of fibrous tissue?"
  ├─ subq_specific_results = state.subquery_results["Causes of fibrous tissue?"]
  ├─ web_ctx = _web_context([DVT, PE, tissue])
  ├─ Evidence: [DVT-article, PE-article, tissue-article]
  ├─ Gemini sees: Specific pathophysiology of tissue formation
  └─ Answer: "Endothelial injury, inflammation, and fibroblast proliferation..."
  
  For Subquery 2: "Effect of surgery?"
  ├─ subq_specific_results = state.subquery_results["Effect of surgery?"]
  ├─ web_ctx = _web_context([surgery, immobility, vascular])
  ├─ Evidence: [surgery-article, immobility-article, vascular-article]
  ├─ Gemini sees: Surgical complications and immobility effects
  └─ Answer: "Surgical trauma increases hypercoagulability, prolonged immobility..."
  
  For Subquery 3: "Sequelae of immobility?"
  ├─ subq_specific_results = state.subquery_results["Sequelae of immobility?"]
  ├─ web_ctx = _web_context([immobility, sequelae, complications])
  ├─ Evidence: [immobility-article, sequelae-article, complications-article]
  ├─ Gemini sees: Long-term effects of immobility
  └─ Answer: "Prolonged immobility causes muscle atrophy, DVT risk, metabolic dysfunction..."

RESULT: All 3 answers are DIVERSE and SPECIFIC! ✅
```

---

## Data Flow Diagram

### BEFORE (Wrong)
```
┌─────────────────────────────────────────────────────────┐
│                     executor()                          │
│                                                         │
│  For SubQ1 → Search → Get 3 results ┐                 │
│  For SubQ2 → Search → Get 3 results ├─→ Aggregate    │
│  For SubQ3 → Search → Get 3 results ┘                 │
│                                                         │
│  state.web_results = [mix of all 9 results]           │
│  (NO per-subquery tracking)                            │
└─────────────────────────┬───────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              answer_subquestions()                      │
│                                                         │
│  web_ctx = ALL 9 results                              │
│                                                         │
│  For SubQ1: Answer using [all 9 results] → Answer A    │
│  For SubQ2: Answer using [all 9 results] → Answer B    │
│  For SubQ3: Answer using [all 9 results] → Answer C    │
│                                                         │
│  Result: A ≈ B ≈ C (similar/identical)                │
└─────────────────────────────────────────────────────────┘
```

### AFTER (Correct)
```
┌─────────────────────────────────────────────────────────┐
│                     executor()                          │
│                                                         │
│  For SubQ1 → Search → Get [3 results] ──→ Track SubQ1  │
│  For SubQ2 → Search → Get [3 results] ──→ Track SubQ2  │
│  For SubQ3 → Search → Get [3 results] ──→ Track SubQ3  │
│                                                         │
│  state.web_results = deduplicated([all 9])            │
│  state.subquery_results = {                           │
│    SubQ1: [3 results],                                │
│    SubQ2: [3 results],                                │
│    SubQ3: [3 results]                                 │
│  }                                                     │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              answer_subquestions()                      │
│                                                         │
│  For SubQ1:                                            │
│  ├─ web_ctx = subquery_results[SubQ1] = [3 specific]  │
│  └─ Answer using only [3 specific] → Answer A'        │
│                                                         │
│  For SubQ2:                                            │
│  ├─ web_ctx = subquery_results[SubQ2] = [3 specific]  │
│  └─ Answer using only [3 specific] → Answer B'        │
│                                                         │
│  For SubQ3:                                            │
│  ├─ web_ctx = subquery_results[SubQ3] = [3 specific]  │
│  └─ Answer using only [3 specific] → Answer C'        │
│                                                         │
│  Result: A' ≠ B' ≠ C' (diverse and specific!)         │
└─────────────────────────────────────────────────────────┘
```

---

## Code Changes Summary

### In `executor()`:
```python
# ADD this line at the start:
subquery_results: Dict[str, List[Dict[str, Any]]] = {}

# ADD this line in the subquery loop:
subquery_results[subq] = []

# CHANGE this:
while not q.empty():
    aggregated.append(q.get())

# TO this:
while not q.empty():
    result = q.get()
    subquery_results[subq].append(result)
    aggregated.append(result)

# ADD this at the end:
state.subquery_results = subquery_results
```

### In `answer_subquestions()`:
```python
# CHANGE this:
web_ctx = _web_context(state.web_results)

# TO this (inside the subquery loop):
subq_specific_results = state.subquery_results.get(subquery, state.web_results)
web_ctx = _web_context(subq_specific_results)
```

That's it! 2 small changes give you completely different results.
