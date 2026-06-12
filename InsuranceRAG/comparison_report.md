# Insurance RAG — Comparison Report
**Generated:** 2026-06-11 22:08

Project 2 — Financial Document Intelligence. Compares two chunking strategies and measures the impact of an LLM reranking step, then runs the full pipeline end-to-end (generation via Nebius Token Factory).

---

## 1. Retrieval Quality — Chunking × Reranking

Metric: **recall@5** — fraction of answerable questions whose expected source document appears in the retrieved chunks. Strategies compared: paragraph, fixed.

| Chunking strategy | Rerank off | Rerank on | Δ (rerank impact) |
|---|---|---|---|
| paragraph | 100% | 100% | +0% |
| fixed | 100% | 100% | +0% |

**Chunking comparison:** without reranking, `paragraph` chunking gives the best recall (100%).

**Reranking impact:** the LLM reranker (Nebius) reorders a fused candidate pool of 10+ chunks down to the top 5. Best overall config is `paragraph` with rerank off (100%).

---

## 2. End-to-End Answers (config: paragraph + rerank)

- **Answer relevance (keyword match):** 15/15 (100%)
- **Retrieval recall (source match):** 15/15 (100%)
- **Refusal correctness (unanswerable → "I don't know"):** 3/3 (100%)

| # | Type | Question | Retrieval | Answer | Refused | Top score |
|---|---|---|---|---|---|---|
| 1 | ans | Is a property with knob-and-tube wiring eligible for HO... | ✅ | ✅ | — | 10.0 |
| 2 | ans | What roof age triggers a referral? | ✅ | ✅ | — | 10.0 |
| 3 | ans | What happens if a property has a severe wildfire risk s... | ✅ | ✅ | — | 10.0 |
| 4 | ans | What is required if a property is in a Special Flood Ha... | ✅ | ✅ | — | 9.0 |
| 5 | ans | How many water losses in 36 months trigger a referral? | ✅ | ✅ | — | 10.0 |
| 6 | ans | What wildfire evidence must be collected for a High wil... | ✅ | ✅ | — | 9.0 |
| 7 | ans | What endorsement should be recommended if a property ha... | ✅ | ✅ | — | 10.0 |
| 8 | ans | When is the Ordinance or Law endorsement (ORD-01) recom... | ✅ | ✅ | — | 10.0 |
| 9 | ans | What is the base premium calculation formula? | ✅ | ✅ | — | 10.0 |
| 10 | ans | What surcharge applies to a property with a High wildfi... | ✅ | ✅ | — | 10.0 |
| 11 | ans | What are the minimum required fields before making an u... | ✅ | ✅ | — | 10.0 |
| 12 | ans | Can a property used for short-term rental be accepted f... | ✅ | ✅ | — | 10.0 |
| 13 | ans | What deductible factor applies to a $2,500 deductible? | ✅ | ✅ | — | 10.0 |
| 14 | ans | What protection class requires a referral unless distan... | ✅ | ✅ | — | 10.0 |
| 15 | ans | What should happen if a property has aluminum branch wi... | ✅ | ✅ | — | 10.0 |
| 16 | unans | What is the cash surrender value of a whole life insura... | — | — | ✅ | 0.0 |
| 17 | unans | How do I file an auto insurance collision claim and wha... | — | — | ✅ | 0.0 |
| 18 | unans | What is the company's CEO email address and office phon... | — | — | ✅ | 0.0 |

---

## 3. Detailed Answers

### Q1: Is a property with knob-and-tube wiring eligible for HO3 coverage?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md
**Retrieved sources:** uw_guidelines_homeowners.md, hazards_guidance.md

**Answer:**

No, according to the uw_guidelines_homeowners.md, a property with knob-and-tube wiring **MUST BE DECLINED** if it is not remediated (Section 1.2).

---

### Q2: What roof age triggers a referral?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md
**Retrieved sources:** uw_guidelines_homeowners.md, hazards_guidance.md, rating_rules.md

**Answer:**

According to the uw_guidelines_homeowners.md, if the roof age is **> 20 years**, the risk **SHALL BE REFERRED** (Section 2.1).

---

### Q3: What happens if a property has a severe wildfire risk score?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md, hazards_guidance.md
**Retrieved sources:** uw_guidelines_homeowners.md, hazards_guidance.md, endorsements_manual.md, rating_rules.md

**Answer:**

According to uw_guidelines_homeowners.md (Section 4.1) and hazards_guidance.md (Section 2.1), if a property has a **Severe** wildfire risk score, the risk **MUST BE DECLINED** unless defensible space mitigation is documented and the underwriter approves.

---

### Q4: What is required if a property is in a Special Flood Hazard Area (SFHA)?

**Type:** answerable  |  **Top relevance:** 9.0

**Expected sources:** uw_guidelines_homeowners.md, endorsements_manual.md, hazards_guidance.md
**Retrieved sources:** endorsements_manual.md, hazards_guidance.md, uw_guidelines_homeowners.md, rating_rules.md

**Answer:**

According to the guidelines, if a property is in a Special Flood Hazard Area (SFHA), the following are required:
* The risk SHALL BE REFERRED (uw_guidelines_homeowners.md, §4.2)
* Flood coverage requirements MUST be evaluated (uw_guidelines_homeowners.md, §4.2)
* The submission SHALL refer (hazards_guidance.md, §3.1)
* The applicant MUST confirm flood insurance status (hazards_guidance.md, §3.1)
* The Flood Exclusion Acknowledgement (FLX-ACK) MUST be attached (endorsements_manual.md, §2.2)

---

### Q5: How many water losses in 36 months trigger a referral?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md
**Retrieved sources:** uw_guidelines_homeowners.md, endorsements_manual.md, hazards_guidance.md

**Answer:**

According to the uw_guidelines_homeowners.md, if the claims count is **≥ 2 water losses within 36 months**, the risk **SHALL BE REFERRED** (Section 3.1 Claims Thresholds).

---

### Q6: What wildfire evidence must be collected for a High wildfire risk score?

**Type:** answerable  |  **Top relevance:** 9.0

**Expected sources:** hazards_guidance.md
**Retrieved sources:** hazards_guidance.md, uw_guidelines_homeowners.md, endorsements_manual.md

**Answer:**

For a High wildfire risk score, the following evidence must be collected:
* Defensible space evidence (Source: uw_guidelines_homeowners.md, §4.3)
* Specifically, this includes:
  * Brush clearance ≥ 100 feet where feasible
  * No combustible materials within 5 feet of structures
Additionally, photo evidence of clearance and roof material type may also be required (Source: hazards_guidance.md, §2.2).

---

### Q7: What endorsement should be recommended if a property has a basement?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** endorsements_manual.md
**Retrieved sources:** endorsements_manual.md, uw_guidelines_homeowners.md

**Answer:**

According to the endorsements_manual.md, if a basement is present, the Water Backup Coverage (WBK-01) SHOULD be recommended (Section 2.1).

---

### Q8: When is the Ordinance or Law endorsement (ORD-01) recommended?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** endorsements_manual.md
**Retrieved sources:** endorsements_manual.md, rating_rules.md, uw_workflow_playbook.md

**Answer:**

The Ordinance or Law endorsement (ORD-01) SHOULD be recommended for homes built before 2000 (endorsements_manual.md).

---

### Q9: What is the base premium calculation formula?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** rating_rules.md
**Retrieved sources:** rating_rules.md

**Answer:**

The base premium calculation formula is: BaseRate = 0.0020 * DwellingLimit (Source: rating_rules.md, Section 1. Base Premium)

---

### Q10: What surcharge applies to a property with a High wildfire score?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** rating_rules.md
**Retrieved sources:** rating_rules.md, endorsements_manual.md, hazards_guidance.md, uw_guidelines_homeowners.md

**Answer:**

According to the rating_rules.md, a property with a High wildfire score has a surcharge of +12%. (Source: rating_rules.md, Section 4.1 Wildfire)

---

### Q11: What are the minimum required fields before making an underwriting decision?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_workflow_playbook.md
**Retrieved sources:** uw_workflow_playbook.md, uw_guidelines_homeowners.md

**Answer:**

The minimum required fields are:
* roof_age
* construction_year
* occupancy_type
* distance_to_hydrant OR protection_class
* claims_count_36mo
(Source: uw_workflow_playbook.md, Section 2.1)

---

### Q12: Can a property used for short-term rental be accepted for HO3 coverage?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md
**Retrieved sources:** uw_guidelines_homeowners.md, endorsements_manual.md

**Answer:**

According to the uw_guidelines_homeowners.md, if the property is used for short-term rental, the risk SHALL BE REFERRED (§1.4). Therefore, it cannot be directly accepted for HO3 coverage without referral. (Source: uw_guidelines_homeowners.md)

---

### Q13: What deductible factor applies to a $2,500 deductible?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** rating_rules.md
**Retrieved sources:** rating_rules.md, endorsements_manual.md, hazards_guidance.md

**Answer:**

The deductible factor for a $2,500 deductible is 0.92 (Source: rating_rules.md, Section 5. Deductible Factors).

---

### Q14: What protection class requires a referral unless distance conditions are met?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md
**Retrieved sources:** uw_guidelines_homeowners.md, rating_rules.md

**Answer:**

According to uw_guidelines_homeowners.md (Section 1.3), a protection class of **9 or 10** requires a referral unless:
* distance to fire station ≤ 10 miles 
* distance to hydrant ≤ 1,000 feet.

---

### Q15: What should happen if a property has aluminum branch wiring?

**Type:** answerable  |  **Top relevance:** 10.0

**Expected sources:** uw_guidelines_homeowners.md
**Retrieved sources:** uw_guidelines_homeowners.md, endorsements_manual.md

**Answer:**

According to the uw_guidelines_homeowners.md, aluminum branch wiring **SHALL BE REFERRED** (Section 2.2).

---

### Q16: What is the cash surrender value of a whole life insurance policy after 10 years?

**Type:** unanswerable  |  **Top relevance:** 0.0

**Expected sources:** none (unanswerable)
**Retrieved sources:** none

**Answer:**

I don't have enough information in the guidelines to answer this question.

---

### Q17: How do I file an auto insurance collision claim and what is the rental car reimbursement limit?

**Type:** unanswerable  |  **Top relevance:** 0.0

**Expected sources:** none (unanswerable)
**Retrieved sources:** none

**Answer:**

I don't have enough information in the guidelines to answer this question.

---

### Q18: What is the company's CEO email address and office phone number?

**Type:** unanswerable  |  **Top relevance:** 0.0

**Expected sources:** none (unanswerable)
**Retrieved sources:** none

**Answer:**

I don't have enough information in the guidelines to answer this question.

---
