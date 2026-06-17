# 🎬 Demo Skit — Home Insurance Agent Assistant (3 min)

**Format:** Screen recording of the Streamlit UI (`streamlit run app.py`).
**Cast:** **Maya** — a homeowners underwriter (the voice/presenter). **The Assistant** — your RAG app.
**Goal:** Show natural, human-friendly questions, grounded cited answers, the chunking/rerank controls, and the honest "I don't know" refusal.

> 💡 **Before you hit record:** have the app open at `http://localhost:8501`, sidebar set to **paragraph + reranking ON**, and the chat cleared. Copy-paste each **Query** verbatim so timing stays tight.

---

## ⏱️ 0:00 – 0:20 — Cold open / intro

**🎙️ Maya (to camera):**
> "Hi! I'm an underwriter, and every day I get questions I'm *supposed* to answer straight from our HO3/HO5 guidelines. Flipping through five manuals is slow — so I built an assistant that answers from those exact documents and *cites* them. Let me show you."

**[SCREEN]** Show the app title **🏠 Home Insurance Agent Assistant** and the sidebar (chunking strategy + reranking toggle). Briefly hover the sidebar.

---

## ⏱️ 0:20 – 0:45 — Query 1: Eligibility (shows a hard decline + citation)

**🎙️ Maya:**
> "First one's a classic. I've got an older home with the original wiring."

**⌨️ Query:**
> Hey, I've got a home with old knob-and-tube wiring that was never updated — can we write an HO3 on it?

**[SCREEN]** Answer appears. Expected:
> ❌ **No** — a property with knob-and-tube wiring **MUST BE DECLINED** if it is not remediated *(uw_guidelines_homeowners.md, §1.2)*.

**🎙️ Maya:** "Clear decline — and notice it points me to the exact section. Let me expand the sources."
**[SCREEN]** Click **🔍 Retrieved context** → show the chunks with their **relevance scores** (10.0).

---

## ⏱️ 0:45 – 1:10 — Query 2: Natural phrasing (referral threshold)

**🎙️ Maya:**
> "Now something phrased the way I'd actually say it — not keyword-perfect."

**⌨️ Query:**
> A client's roof is about 25 years old. Does that have to go to referral?

**[SCREEN]** Expected:
> A roof **older than 20 years** **SHALL BE REFERRED** *(uw_guidelines_homeowners.md, §2.1)*.

**🎙️ Maya:** "I said 'about 25 years' — it understood that maps to the over-20 rule. That's the hybrid retrieval: semantic search gets the intent, keyword search nails the exact terms."

---

## ⏱️ 1:10 – 1:35 — Query 3: Recommendation (endorsement)

**🎙️ Maya:**
> "It's not just yes/no — it recommends coverage too."

**⌨️ Query:**
> This home has a basement. What coverage endorsement should I add?

**[SCREEN]** Expected:
> Recommend **WBK-01 (Water Backup Coverage)** for properties with a basement *(endorsements_manual.md, §2.1)*.

**🎙️ Maya:** "Water backup endorsement — exactly what I'd want flagged before binding."

---

## ⏱️ 1:35 – 1:55 — Query 4: Numeric lookup (rating)

**🎙️ Maya:**
> "Rating questions need to be precise — no rounding, no guessing."

**⌨️ Query:**
> Quick one — what's the deductible factor for a $2,500 deductible?

**[SCREEN]** Expected:
> The deductible factor for a **$2,500** deductible is **0.92** *(rating_rules.md, §5)*.

**🎙️ Maya:** "Exact figure, straight from the rating table."

---

## ⏱️ 1:55 – 2:25 — Query 5: The honesty test (refusal) ⭐

**🎙️ Maya:**
> "Here's the one that matters most. What happens when I ask something that *isn't* in our homeowners guidelines? A chatbot would make something up. Watch."

**⌨️ Query:**
> What's the cash surrender value of a whole life insurance policy after 10 years?

**[SCREEN]** Expected — a **yellow warning banner**:
> ⚠️ "I don't have enough information in the guidelines to answer this question."

**🎙️ Maya:** "It refused — because whole-life isn't in our corpus. Under the hood, the reranker scored every passage near zero, so instead of hallucinating, it declined. *That's* what makes it safe to use."

---

## ⏱️ 2:25 – 2:45 — The controls (chunking + reranking)

**🎙️ Maya:**
> "Two switches in the sidebar let me see how it works."

**[SCREEN]**
- Flip **chunking strategy**: `paragraph → fixed`, re-ask the basement question → same correct answer.
- Toggle **reranking OFF**, re-ask the whole-life question → note it no longer refuses as cleanly.

**🎙️ Maya:** "I compared both chunking strategies and the reranker in my evaluation — reranking is what powers that refusal."

---

## ⏱️ 2:45 – 3:00 — Outro / results

**🎙️ Maya (to camera):**
> "Quick numbers: across 15 graded questions it hit **100% source recall** and **100% answer relevance**, and it correctly refused **all 3** out-of-corpus questions. Generation and reranking both run on **Nebius Token Factory**, embeddings on OpenAI, vectors in Pinecone. Grounded, cited, and honest when it doesn't know. Thanks for watching!"

**[SCREEN]** Briefly show `comparison_report.md` (the 100% tables) then fade out.

---

## 📋 Copy-paste query list (in order)

1. `Hey, I've got a home with old knob-and-tube wiring that was never updated — can we write an HO3 on it?`
2. `A client's roof is about 25 years old. Does that have to go to referral?`
3. `This home has a basement. What coverage endorsement should I add?`
4. `Quick one — what's the deductible factor for a $2,500 deductible?`
5. `What's the cash surrender value of a whole life insurance policy after 10 years?`

**Backup / bonus queries** (if you have extra time or want variety):
- `Property came back with a severe wildfire score — what's my move?` → decline unless defensible-space mitigation *(hazards_guidance.md / uw_guidelines_homeowners.md)*
- `How many water claims in the last 3 years before I have to refer it?` → ≥ 2 in 36 months → referral
- `Is a place that's used as a short-term rental OK for HO3?` → must be referred
- `What surcharge hits a home with a high wildfire score?` → +12%

---

## 🎚️ Recording tips
- **~3:00 total** — if you run long, drop Query 4 (numeric) and keep the refusal (Query 5); the refusal is the highlight.
- Speak the **🎙️** lines; let each answer finish rendering before talking over it.
- Keep the **Retrieved context** panel expansion for Query 1 only — showing it every time eats time.
- The first question per (strategy + rerank) combo is slower (cold cache). Do one **throwaway warm-up query before recording** so live responses feel snappy.
