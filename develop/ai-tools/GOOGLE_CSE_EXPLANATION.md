# How Google Custom Search Engine (CSE) Works in Your System

## Quick Answer
**Google CSE searches ALL configured websites at once** for your query. It's NOT searching individual websites separately. Instead, it's searching a custom index containing only those websites.

---

## Visual Explanation

### Without Google CSE (Old Approach)
```
Your Question: "UTI treatment in pregnancy"
                          |
                          v
    Check: Does this site allow this domain?
    ├── Mayo Clinic? ✓
    ├── WebMD? ✓
    ├── Random site? ✗
    └── If allowed, scrape it
    
    Result: Only scraped allowed sites manually
```

### With Google CSE (Current Approach)
```
Your Question: "UTI treatment in pregnancy"
                          |
                          v
    Google CSE API Call with:
    ├── Query: "UTI treatment in pregnancy"
    ├── Custom Search Engine ID (CSE_ID: 3743e9e99b7094950)
    └── API Key
                          |
                          v
    Google's Servers (Pre-indexed):
    ├── Mayo Clinic articles ✓
    ├── PubMed articles ✓
    ├── NIH articles ✓
    ├── WebMD articles ✓
    ├── PubMed Central (PMC) ✓
    └── [Other configured medical sites]
                          |
                          v
    Google searches ENTIRE custom index
    at once for matching results
                          |
                          v
    Returns Top 10 results from ANY
    of the configured websites that
    match your query
```

---

## How Your Google CSE is Configured

Your CSE ID: `3743e9e99b7094950`

This CSE instance is pre-configured in Google's system to search ONLY these websites:
- PubMed Central (pmc.ncbi.nlm.nih.gov)
- PubMed (pubmed.ncbi.nlm.nih.gov)
- NIH (nih.gov)
- Mayo Clinic (mayoclinic.org)
- WebMD (webmd.com)
- And other medical/health websites

---

## How Search Works Step-by-Step

### Example: Medical Question About UTI in Pregnancy

```
User asks: "What antibiotics are safe for UTI treatment during pregnancy?"

Step 1: Your backend calls Google CSE API
   URL: https://www.googleapis.com/customsearch/v1
   Parameters:
   {
     "q": "What antibiotics are safe for UTI treatment during pregnancy?",
     "cx": "3743e9e99b7094950",  # Your custom search engine
     "key": "YOUR_GOOGLE_API_KEY",
     "num": 10  # Get top 10 results
   }

Step 2: Google searches its index
   Google searches ALL configured sites simultaneously:
   - Did Mayo Clinic mention UTI antibiotics? → 3 results
   - Did PubMed mention it? → 5 results
   - Did NIH mention it? → 2 results
   - Did WebMD mention it? → 4 results
   
   (Total matching: 14 results, returning top 10)

Step 3: Google returns results
   {
     "items": [
       {
         "title": "UTI Treatment During Pregnancy",
         "link": "https://www.mayoclinic.org/...",
         "snippet": "Antibiotics that are safe during pregnancy..."
       },
       {
         "title": "Antibiotics in Pregnancy - PubMed",
         "link": "https://pubmed.ncbi.nlm.nih.gov/...",
         "snippet": "Safe antibiotic options include..."
       },
       // ... 8 more results from various sites
     ]
   }

Step 4: Your system processes results
   - Extracts content from each URL
   - Summarizes with Gemini
   - Returns combined evidence to user
```

---

## Key Differences

| Aspect | Old Hardcoded Approach | Google CSE |
|--------|----------------------|-----------|
| **Search Method** | Manual domain list check | Google indexes entire custom collection |
| **Speed** | Slower (checks each domain) | Faster (Google's pre-indexed) |
| **Accuracy** | Only exact URL matches | Ranked by relevance |
| **Flexibility** | Hard to add/remove sites | Easy (just reconfigure CSE) |
| **Coverage** | Limited to known domains | Covers all configured sites uniformly |
| **Scalability** | Breaks with many domains | Scales to unlimited sites |

---

## Important Clarifications

### 1. NOT Individual Website Search
**False:** "It searches each website one by one"
**True:** Google CSE searches all configured websites simultaneously in a single query

### 2. NOT Random Internet Search
**False:** "It can return results from any website"
**True:** Only results from pre-configured medical websites

### 3. NOT Sequential Fallback
**False:** "It tries Mayo Clinic, then WebMD, then PubMed..."
**True:** Single API call returns mixed results from all sites ranked by relevance

---

## How Relevance Ranking Works

When you ask "UTI antibiotics pregnancy", Google returns:
1. **Most relevant** - Results mentioning all keywords
2. **Very relevant** - Results mentioning most keywords
3. **Somewhat relevant** - Results mentioning some keywords

Examples:
```
Query: "Safe antibiotics for UTI in pregnancy"

Result 1 (Score: 10/10)
  URL: mayoclinic.org/...
  Content mentions: safe + antibiotics + UTI + pregnancy
  ✅ All keywords present

Result 2 (Score: 8/10)
  URL: pubmed.ncbi.nlm.nih.gov/...
  Content mentions: antibiotics + pregnancy + infection (not "UTI" explicitly)
  ✅ Most keywords present

Result 3 (Score: 5/10)
  URL: nih.gov/...
  Content mentions: antibiotics + pregnancy
  ⚠️ Missing UTI context
```

---

## Code Flow in Your System

```python
# File: backend/workflows/agents.py

def search_with_google_cse(query: str, num_results: int = 5):
    """
    ONE API call that searches ALL configured sites at once
    """
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,              # Your entire question
        "cx": GOOGLE_CSE_ID,     # Custom search engine ID
        "key": GOOGLE_API_KEY,   # Google API key
        "num": num_results       # How many results to return
    }
    
    # Single request to Google - returns results from all configured sites
    response = httpx.get(url, params=params, timeout=15)
    data = response.json()
    
    # Results include URLs from multiple configured websites
    return [
        {
            "title": item["title"],
            "link": item["link"],  # Could be from Mayo, PubMed, NIH, etc.
            "snippet": item["snippet"]
        }
        for item in data.get("items", [])
    ]
```

---

## Summary

✅ **Google CSE searches all configured websites in ONE request**
✅ **Results can come from any configured site**
✅ **Google ranks results by relevance automatically**
✅ **No manual checking of allowed domains needed**
✅ **Much faster and more reliable than scraping individual sites**

The beauty of Google CSE is that you don't need to tell it "search Mayo Clinic" or "search PubMed" separately. You just ask your question, and Google searches all configured sites and returns the most relevant results.
