# Google CSE Integration - Quick Reference Guide

## 🎯 One-Sentence Summary
**Your backend now uses Google Custom Search Engine API to automatically get search results filtered by your configured domains - no hardcoded lists, no code changes needed.**

---

## 📊 Architecture

```
┌─────────────────────────────────────┐
│  Google CSE Control Panel           │
│  (Add/Remove domains here)          │
│  - diabetes.org                     │
│  - healthline.com                   │
│  - mayoclinic.org                   │
└─────────────────────────────────────┘
            ↓ (instantly)
┌─────────────────────────────────────┐
│  Your Backend                       │
│  - Calls Google CSE API             │
│  - Uses: API_KEY + CSE_ID           │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  Google Returns                     │
│  - Pre-filtered results             │
│  - Only approved domains            │
└─────────────────────────────────────┘
            ↓
┌─────────────────────────────────────┐
│  User Gets Answer                   │
│  - From trusted sources             │
│  - With citations                   │
└─────────────────────────────────────┘
```

---

## 🔧 What You Need to Know

### **To Add a Domain**
1. Go to Google CSE Control Panel
2. Click "Add Site"
3. Enter: `yourdomain.org`
4. Done! ✅ (takes effect immediately)

### **To Remove a Domain**
1. Go to Google CSE Control Panel
2. Find the domain
3. Click "Remove"
4. Done! ✅ (takes effect immediately)

### **No Code Changes Needed** ✅
- No editing config files
- No editing code
- No rebuilding
- No redeploying
- **Changes take effect instantly**

---

## 📁 Files Changed

| File | What Changed | Impact |
|------|-------------|--------|
| `config.py` | Removed hardcoded domains | No more DEFAULT_ALLOWED set |
| `agents.py` | Added `search_with_google_cse()` | Direct Google CSE API calls |
| `web_utils.py` | Simplified `allowed_url()` | Always returns True (Google filters) |

---

## 🔐 Environment Variables

**Already in your `.env`:**
```env
GOOGLE_API_KEY=AIzaSyAsvfh78DeGl-enTwy_R9VOSN13pWTHdyE
GOOGLE_CSE_ID=3743e9e99b7094950
```

**No changes needed!** ✅

---

## 🚀 How It Works

### **Step-by-Step Flow**

1. User asks: *"What is diabetes?"*

2. Backend calls Google CSE API:
   ```
   https://www.googleapis.com/customsearch/v1?
   q=What%20is%20diabetes&
   cx=3743e9e99b7094950&
   key=AIzaSyAsvfh78DeGl-enTwy_R9VOSN13pWTHdyE
   ```

3. Google CSE checks its configured domains:
   - ✅ Include: diabetes.org
   - ✅ Include: healthline.com
   - ✅ Include: mayoclinic.org
   - ❌ Exclude: unrelated.com (not configured)

4. Google returns **only** results from approved domains

5. Backend processes results and sends to Gemini

6. Gemini generates answer with citations

---

## 💡 Key Advantages

| Before | After |
|--------|-------|
| Hardcoded list in code | Managed in Google CSE UI |
| Need to edit code | No code edits needed |
| Need to redeploy | Changes instant |
| Manual sync needed | Automatic (Google CSE) |
| Duplicate config | Single source of truth |

---

## ❓ FAQ

**Q: How do I add a new trusted source?**
A: Go to Google CSE Control Panel → Add Site → Done (instant)

**Q: Do I need to restart the app?**
A: No! Changes take effect immediately.

**Q: Do I need to edit code?**
A: No! Everything is managed in Google CSE.

**Q: What if Google CSE goes down?**
A: Search will fail gracefully with error message. No domains are hardcoded.

**Q: Can I revert to the old hardcoded way?**
A: Yes, but why would you? This is better! 😊

---

## 🧪 How to Test

**Check if it's working:**
```bash
# Look at logs for this message:
# "Google CSE search for 'query' returned X results"

# If you see this, it's working! ✅
```

**Try a query:**
```
POST /api/search
{
  "question": "What causes diabetes?"
}
```

**Check response:**
- Should have results from trusted medical sources only
- Should have citations [1], [2], etc.

---

## 🎓 What This Solves

### **Problem**
- Hardcoded domains in code
- Changes require code edits and redeploy
- Maintaining multiple lists (CSE + code)

### **Solution**
- Google CSE is single source of truth
- Changes take effect instantly
- No code changes needed
- Automatic filtering by Google

---

## 📞 Support

If you need to debug:

1. **Check `.env` has correct keys:**
   - `GOOGLE_API_KEY` ✅
   - `GOOGLE_CSE_ID` ✅

2. **Check Google CSE has domains:**
   - Go to Control Panel
   - Verify domains are configured

3. **Check logs:**
   - Look for "Google CSE search" messages
   - Check for errors

4. **Test directly:**
   ```python
   from workflows.agents import search_with_google_cse
   results = search_with_google_cse("test query", 5)
   ```

---

## 🎉 You're All Set!

Your system now automatically filters medical questions through Google's verified domain list. No more manual configuration!

Enjoy! ✨
