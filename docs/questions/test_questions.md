# RAG System Test Questions

These questions are designed to test different aspects of the RAG retrieval and generation pipeline.

## Test Questions

### 1. Spell Details (Factual Lookup)
**Question:** What are the effects of the Magic User spell "Prismatic Sphere"?

**Testing:** 
- Specific factual retrieval
- Spell description parsing
- Ability to find exact named entity

**Expected Challenge:** Spell might be in Player's Handbook or DM Guide; tests cross-document retrieval

---

### 2. Experience Points Table (Table Query)
**Question:** How many experience points does a fighter need to become 9th level?

**Testing:**
- Table data retrieval
- Numeric data extraction
- Class-specific information

**Expected Challenge:** Data is in a table format; tests how well naive chunking handles structured data

---

### 3. Class Abilities (Conceptual/Comparative)
**Question:** What can Thieves do that other character classes cannot do?

**Testing:**
- Cross-referencing multiple sections
- Comparative analysis
- Synthesis of information from different parts

**Expected Challenge:** Requires understanding of multiple character classes; tests if retrieval gets enough context

---

### 4. Combat Comparison (Reasoning/Multi-source)
**Question:** Who would win in a fight, an OwlBear or a Lizard Man (explain your answer)?

**Testing:**
- Monster Manual retrieval
- Comparative reasoning
- LLM's ability to synthesize stats into conclusions

**Expected Challenge:** Requires retrieving and comparing hit dice, armor class, attacks, damage - likely the hardest question

---

### 5. Rules Query (Detailed Policy)
**Question:** Under what circumstances can characters change their alignment?

**Testing:**
- Rules retrieval
- Multi-paragraph comprehension
- Policy understanding

**Expected Challenge:** Answer spans multiple paragraphs; tests if chunk size captures complete context

---

## Success Metrics

1. **Accuracy** - Is the answer factually correct according to the rulebooks?
2. **Relevance** - Did the system retrieve the right chunks?
3. **Speed** - Response time < 5 seconds (once we switch to Groq)

## Hypothesis: Naive Chunking Failure Predictions

### Will Likely PASS:
- Question 5 (alignment rules are narrative text, should chunk reasonably)

### Will Likely STRUGGLE:
- Question 2 (tables are hard to chunk and retrieve)
- Question 4 (requires multiple chunks from Monster Manual)

### Will Likely FAIL:
- Question 1 (if spell is split across chunks)
- Question 3 (requires comparing multiple class descriptions)

## Iteration Goals

After Phase 1 (Naive), we'll analyze:
- Which questions failed and why
- What chunk sizes would have helped
- Whether overlap improved retrieval
- Where metadata would have added value

Then we'll implement targeted fixes in Phase 2.
