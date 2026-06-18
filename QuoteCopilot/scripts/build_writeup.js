// Generates docs/QuoteCopilot_Project_Writeup.docx
// Formatting aligned to the Week 2 "Home Insurance Agent Assistant" house style.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, LevelFormat, HeadingLevel, BorderStyle,
  WidthType, ShadingType, PageNumber, PageBreak,
  ExternalHyperlink, TabStopType, TabStopPosition,
} = require("docx");

// Week 2 palette (matched exactly)
const NAVY = "1F4E79";    // Heading 1 + table header fill
const BLUE = "2E5496";    // Heading 2
const SLATE = "333333";   // Heading 3
const ACCENT = "2E74B5";  // accent text / rules
const ROWFILL = "EAF1F8"; // table zebra
const CODEFILL = "F4F4F4";

const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 80, bottom: 80, left: 120, right: 120 };

// ---- helpers ---------------------------------------------------------------
function h1(text) { return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(text)] }); }
function h2(text) { return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(text)] }); }
function h3(text) { return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun(text)] }); }
function p(text, opts = {}) {
  return new Paragraph({ spacing: { after: 120, line: 276 }, children: [new TextRun({ text, ...opts })] });
}
function runs(children) { return new Paragraph({ spacing: { after: 120, line: 276 }, children }); }
function bullet(text, level = 0) {
  return new Paragraph({ numbering: { reference: "bullets", level }, spacing: { after: 60, line: 276 },
    children: typeof text === "string" ? [new TextRun(text)] : text });
}
function numbered(text, ref = "nums") {
  return new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60, line: 276 },
    children: typeof text === "string" ? [new TextRun(text)] : text });
}
function tocLine(num, title) {
  return new Paragraph({ spacing: { after: 50, line: 276 }, indent: { left: 360 },
    tabStops: [{ type: TabStopType.LEFT, position: 900 }],
    children: [new TextRun({ text: num + ".", bold: true, color: ACCENT }), new TextRun({ text: "\t" + title })] });
}
function codeBlock(text) {
  return new Paragraph({ shading: { fill: CODEFILL, type: ShadingType.CLEAR }, spacing: { before: 40, after: 40 },
    border: { left: { style: BorderStyle.SINGLE, size: 12, color: "BBBBBB", space: 6 } },
    children: [new TextRun({ font: "Courier New", size: 18, text })] });
}
function cell(text, { width, head = false, fill, bold = false, align } = {}) {
  return new TableCell({ borders, width: { size: width, type: WidthType.DXA }, margins: cellMargins,
    shading: { fill: head ? NAVY : (fill || "FFFFFF"), type: ShadingType.CLEAR },
    children: [new Paragraph({ alignment: align,
      children: [new TextRun({ text, bold: head || bold, color: head ? "FFFFFF" : "000000", size: 20 })] })] });
}
function dataTable(widths, header, body) {
  const rows = [new TableRow({ tableHeader: true, children: header.map((t, i) => cell(t, { width: widths[i], head: true })) })];
  body.forEach((r, ri) => {
    rows.push(new TableRow({ cantSplit: true,
      children: r.map((t, i) => cell(t, { width: widths[i], fill: ri % 2 ? ROWFILL : "FFFFFF", bold: i === 0 })) }));
  });
  return new Table({ width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths, rows });
}
function rule() {
  return new Paragraph({ spacing: { after: 120 },
    border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: ACCENT, space: 1 } }, children: [new TextRun({ text: "" })] });
}

// ---- document --------------------------------------------------------------
const doc = new Document({
  creator: "Lak Tuttagunta",
  title: "QuoteCopilot — Week 3 Project Writeup",
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal", next: "Normal",
        run: { size: 56, bold: true, color: "000000", font: "Arial" }, paragraph: { spacing: { after: 80 } } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: NAVY, font: "Arial" },
        paragraph: { spacing: { before: 280, after: 140 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: BLUE, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: SLATE, font: "Arial" },
        paragraph: { spacing: { before: 140, after: 80 }, outlineLevel: 2 } },
    ],
  },
  numbering: {
    config: [
      { reference: "bullets", levels: [
        { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } } } },
        { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 1080, hanging: 280 } } } },
      ] },
      { reference: "nums", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
      { reference: "learnings", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 280 } } } }] },
    ],
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } },
    headers: { default: new Header({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
      children: [new TextRun({ text: "QuoteCopilot", bold: true, color: NAVY, size: 18 }),
        new TextRun({ text: "\tThe Gen Academy — Week 3", color: "777777", size: 18 })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({
      tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
      children: [new TextRun({ text: "Multi-Agent HO3 Underwriting Review", color: "999999", size: 16 }),
        new TextRun({ text: "\tPage ", color: "999999", size: 16 }),
        new TextRun({ children: [PageNumber.CURRENT], color: "999999", size: 16 }),
        new TextRun({ text: " of ", color: "999999", size: 16 }),
        new TextRun({ children: [PageNumber.TOTAL_PAGES], color: "999999", size: 16 })] })] }) },
    children: [
      // ---- Title block ----
      new Paragraph({ style: "Title", children: [new TextRun("QuoteCopilot")] }),
      new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "A Multi-Agent Insurance Underwriting Review System for HO3 Homeowner Submissions", bold: true, color: BLUE, size: 26 })] }),
      new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: "Week 3 Project — Mastering Agentic AI Bootcamp · Project 3B (Multi-Agent Deal Review Pipeline, insurance variant)", size: 20, color: "555555" })] }),
      runs([
        new TextRun({ text: "Author: ", bold: true }), new TextRun("Lak Tuttagunta   "),
        new TextRun({ text: "Track: ", bold: true }), new TextRun("Code-heavy (LangChain + LangGraph)   "),
        new TextRun({ text: "Date: ", bold: true }), new TextRun("18 June 2026"),
      ]),
      runs([
        new TextRun({ text: "Repository: ", bold: true }),
        new ExternalHyperlink({ link: "https://github.com/laknarayana9/GenAcademy", children: [new TextRun({ text: "github.com/laknarayana9/GenAcademy", style: "Hyperlink" })] }),
        new TextRun({ text: "  (QuoteCopilot/)", color: "777777" }),
      ]),
      new Paragraph({ shading: { fill: ROWFILL, type: ShadingType.CLEAR }, spacing: { before: 120, after: 120, line: 276 }, border: { left: { style: BorderStyle.SINGLE, size: 18, color: ACCENT, space: 8 } }, children: [
        new TextRun({ text: "Synthetic data notice. ", bold: true }),
        new TextRun("All underwriting guidelines, applicant data, hazard signals, and labeled evaluation cases in this project are synthetic and authored for the bootcamp. No real carrier guidelines, customer PII, credit, claims, or third-party hazard data are used. QuoteCopilot never binds coverage, issues a policy, or denies coverage without a human review path."),
      ] }),
      rule(),

      // ---- Contents ----
      h1("Contents"),
      tocLine(1, "One-Liner"),
      tocLine(2, "Project Overview"),
      tocLine(3, "System Architecture"),
      tocLine(4, "Setup & Running"),
      tocLine(5, "Datasets Used"),
      tocLine(6, "Prompts Used During AI-Assisted Coding"),
      tocLine(7, "Iterations We Tried"),
      tocLine(8, "Evaluation & Results"),
      tocLine(9, "Human-in-the-Loop & Failure Handling"),
      tocLine(10, "Limitations & Future Work"),
      tocLine(11, "Learnings & Observations"),
      new Paragraph({ children: [new PageBreak()] }),

      // ---- 1 One-liner ----
      h1("1. One-Liner"),
      new Paragraph({ spacing: { after: 120, line: 288 }, children: [new TextRun({ italics: true, size: 24, text:
        "QuoteCopilot helps insurance underwriters review HO3 homeowner quote submissions in a web app — replacing manual guideline lookup, missing-information follow-up, risk triage, rating checks, and referral-packet preparation. It runs intake, retrieval, enrichment, underwriting, verification, rating, and packaging tools on its own, hands off to a human when information is missing or the risk requires referral or decline, and it works when an underwriter can get a cited decision packet in under three minutes with reliable reason codes and a full audit trail." })] }),

      // ---- 2 Project overview ----
      h1("2. Project Overview"),
      p("QuoteCopilot turns a raw or legacy homeowner quote application into a cited ACCEPT, REFER, or DECLINE decision packet. The problem it targets is real: homeowner underwriting requires checking multiple guideline documents, interpreting eligibility rules, chasing missing facts, assessing hazards, computing a premium indication, and documenting a recommendation. The manual workflow is slow, inconsistent, and hard to audit."),
      p("The system is deliberately built as an agentic pipeline rather than a single LLM call. A LangGraph orchestrator composes four subgraphs, each owning a phase of the workflow, with eight specialized agents and three deterministic tools. The governing design principle is that deterministic rules — not LLM text — are the source of truth for any eligibility or referral decision. The LLM is used only where language, not judgment, is required: phrasing follow-up questions, rationale, and next steps. Every such call has a deterministic fallback, so the system remains fully runnable and reproducible offline."),
      h2("2.1 Agent Framework"),
      p("The project was formalized against the bootcamp agent framework before any code was written:"),
      dataTable([2600, 6760],
        ["Field", "This Project"],
        [
          ["Agent goal", "Convert a homeowner quote submission into a cited underwriting recommendation and review packet."],
          ["Where people use it", "Streamlit demo backed by FastAPI endpoints."],
          ["Steps it takes", "Normalize intake → route → pause if missing info → enrich risk → retrieve guidelines → assess rules → verify output → rate → package decision → route to human review when needed."],
          ["What it can do", "Read quote payloads, retrieve guideline chunks, enrich risk profiles, evaluate rules, compute a premium indication, create review tasks, persist audit events."],
          ["What it remembers", "Run ID, quote ID, raw + canonical submission, missing questions, supplied answers, node outputs, retrieved citations, decision packet, review status, audit trail."],
          ["What it should never do", "Bind coverage, issue a policy, deny coverage without a review path, invent citations, use real PII, or override deterministic rules with LLM text."],
          ["Human-in-the-loop", "Required for missing info, referrals, declines, verification failures, and any action that changes review status."],
          ["When something breaks", "Retry safe retrieval/model calls, fall back to deterministic wording, log the failure, and route to review if confidence or grounding is insufficient."],
          ["How to know it worked", "A demo user can complete accept, missing-info resume, refer, and decline scenarios with cited packets and passing eval metrics."],
        ]),
      h2("2.2 Autonomy Boundary"),
      dataTable([3120, 6240],
        ["Boundary", "Behavior"],
        [
          ["Autonomous (read / analyze)", "Normalize intake, route, enrich hazard/territory signals, retrieve guideline evidence, evaluate deterministic rules, verify grounding, compute a premium indication, assemble the packet."],
          ["Human-in-the-loop (required)", "Missing or uncertain intake facts; wildfire mitigation evidence; any REFER or DECLINE; verification block/downgrade; no retrievable evidence; invalid LLM output after retry."],
          ["Never (hard limits)", "Bind coverage, issue a policy, deny coverage without review, invent citations, use real PII, or override deterministic rules with LLM text."],
        ]),

      // ---- 3 Architecture ----
      h1("3. System Architecture"),
      p("The pipeline is a parent LangGraph StateGraph that composes four nested subgraphs over a single shared RunState. Graph wiring and agent logic are kept in separate modules so agents are unit-testable without a graph runner, and llm/factory.py is the single place model selection happens."),
      h2("3.1 Flow"),
      bullet("Intake subgraph — Normalizer canonicalizes the raw/legacy payload into an HO3 submission and detects missing required fields; Router classifies the route (waiting_for_info / standard / hard_refer / hard_decline_candidate). Pauses with follow-up questions when facts are missing."),
      bullet("Enrichment subgraph — Enrichment agent adds deterministic hazard/territory signals (wildfire band, flood indicator, territory, confidence map) and a retrieval plan; Retrieval agent runs hybrid RAG over the guideline corpus. Can pause for contextual gaps (e.g., wildfire mitigation evidence)."),
      bullet("Assessment subgraph — Assessor applies the governed deterministic rule engine to produce a preliminary decision, reason codes, facts used, and confidence; Verifier checks the decision is allowed and grounded in retrieved evidence; Rating tool computes a premium indication."),
      bullet("Packaging subgraph — Packager assembles the final cited decision packet (recommendation, confidence, reason codes, citations, facts used, next steps, review status, trace ref); an optional Critic reviews rationale faithfulness; review routing creates a human review task for any REFER/DECLINE/verification failure."),
      h2("3.2 Key Architectural Decisions"),
      dataTable([2600, 2600, 4160],
        ["Concern", "Choice", "Rationale"],
        [
          ["Orchestration", "LangGraph hierarchical subgraphs", "Graph composition, nested state, multi-level pause/resume."],
          ["Model assignment", "Switchable via llm/factory.py", "Cheap models for routing/enrichment; stronger for assessment/packaging."],
          ["Retrieval", "Hybrid BM25 + semantic + RRF + cross-encoder re-rank", "Exact rule-term matching plus paraphrase coverage; fully local."],
          ["Persistence", "SqliteSaver checkpoints + separate business SQLite", "Clean split between LangGraph internals and domain schema."],
          ["Demo surface", "Streamlit → FastAPI over HTTP", "API is independently testable; UI is a pure rendering layer."],
        ]),
      h2("3.3 Project Structure"),
      dataTable([2600, 6760],
        ["Path", "Purpose"],
        [
          ["app/api/", "FastAPI app factory + routes: quotes, runs, answers, reviews."],
          ["app/graph/", "Parent orchestrator, shared RunState, four subgraphs, run/resume runner."],
          ["app/agents/", "Eight agents: normalizer, router, enrichment, retrieval, assessor, verifier, packager, critic."],
          ["app/tools/", "Deterministic rules engine, rating calculator, hybrid RAG retriever."],
          ["app/models/", "Pydantic schemas: submission, decision (packet/reason code/citation), review."],
          ["app/db/", "SQLite connection + schema: runs, audit_events, decision_packets, review_tasks."],
          ["app/llm/", "Provider factory — the single model-selection point (anthropic / openai / nebius)."],
          ["corpus/", "Five synthetic HO3 guideline Markdown documents."],
          ["evals/", "Labeled dataset + scoring harness (run_evals.py)."],
          ["tests/", "Unit (rules, rating, state) + integration (full graph, API)."],
          ["streamlit_app.py", "Streamlit UI calling the API via httpx."],
        ]),
      h2("3.4 Technology Stack"),
      runs([new TextRun({ text: "Backend: ", bold: true }), new TextRun("FastAPI 0.115 · LangGraph 0.2.62 · langgraph-checkpoint-sqlite · Pydantic 2.10 / pydantic-settings.  ")]),
      runs([new TextRun({ text: "LLM: ", bold: true }), new TextRun("langchain-anthropic & langchain-openai; providers anthropic | openai | nebius (Nebius Token Factory via the OpenAI-compatible endpoint).  ")]),
      runs([new TextRun({ text: "Retrieval: ", bold: true }), new TextRun("ChromaDB 0.5 (semantic) · rank-bm25 (lexical) · sentence-transformers all-MiniLM-L6-v2 (embeddings) · ms-marco-MiniLM-L-6-v2 (cross-encoder re-rank).  ")]),
      runs([new TextRun({ text: "Frontend: ", bold: true }), new TextRun("Streamlit 1.41 calling the API via httpx.  ")]),
      runs([new TextRun({ text: "State: ", bold: true }), new TextRun("Two SQLite stores — checkpoints.db (LangGraph) and quotecopilot.db (runs, audit_events, decision_packets, review_tasks).")]),

      // ---- 4 Setup & Running ----
      h1("4. Setup & Running"),
      h2("4.1 Installation"),
      bullet("Python 3.13."),
      bullet("One provider key: ANTHROPIC_API_KEY (default) or NEBIUS_API_KEY (Nebius Token Factory — https://studio.nebius.com)."),
      codeBlock("python -m venv .venv && source .venv/bin/activate"),
      codeBlock("pip install -r requirements.txt"),
      codeBlock("cp .env.example .env   # set LLM_PROVIDER and the matching API key"),
      h2("4.2 Run Order"),
      dataTable([900, 3900, 4560],
        ["Step", "Command", "What it does"],
        [
          ["1", "python scripts/ingest_corpus.py", "Build BM25 + Chroma retrieval indexes from corpus/."],
          ["2", "uvicorn app.api.main:app --reload", "Start the FastAPI backend (quote intake, runs, answers, reviews)."],
          ["3", "streamlit run streamlit_app.py", "Launch the interactive demo UI."],
          ["4", "pytest", "Run the unit + integration suite (28 tests)."],
          ["5", "python evals/run_evals.py --report", "Run the labeled eval set and write results JSON."],
        ]),
      p("Switching providers is a one-line .env change (LLM_PROVIDER=nebius); no code edits are required. With LLM_PROVIDER=nebius and the Anthropic model names left in place, the factory automatically substitutes Nebius-hosted models."),

      // ---- 5 Datasets ----
      h1("5. Datasets Used"),
      p("Two synthetic datasets, both authored for this project. There is no real or proprietary data anywhere in the system."),
      h2("5.1 Guideline Corpus (retrieval source)"),
      p("Five Markdown documents under corpus/, chunked and indexed into the hybrid retriever. They are the only citable evidence — agents may cite a chunk only if it was actually retrieved."),
      dataTable([4680, 4680],
        ["File", "Contents"],
        [
          ["01_eligibility.md", "Core HO3 eligibility knockouts and acceptance bands."],
          ["02_occupancy.md", "Owner-occupied / rental / vacant occupancy rules."],
          ["03_roof_property.md", "Roof age/type and property condition guidelines."],
          ["04_hazard_wildfire_flood.md", "Wildfire band, mitigation evidence, and flood-zone rules."],
          ["05_rating_endorsements.md", "Rating factors and endorsement guidance."],
        ]),
      h2("5.2 Labeled Evaluation Set"),
      p("evals/dataset.json — 10 labeled synthetic HO3 cases spanning the full decision space, each with expected recommendation, reason codes, missing-info, and review-required flags."),
      dataTable([3120, 2080, 4160],
        ["Case", "Expected", "Tests"],
        [
          ["accept_001", "ACCEPT", "Clean low-risk straight-through."],
          ["refer_roof_age", "REFER", "Roof-age referral band."],
          ["decline_roof_age", "DECLINE", "Roof age past knockout."],
          ["decline_vacant", "DECLINE", "Prohibited vacant occupancy."],
          ["refer_rental", "REFER", "Rental occupancy referral."],
          ["refer_wildfire", "REFER", "High wildfire signal / mitigation."],
          ["refer_flood", "REFER", "Flood-zone referral."],
          ["refer_claims", "REFER", "Adverse claims history."],
          ["missing_roof_age", "ACCEPT", "Pause for roof age, resume, accept."],
          ["missing_occupancy", "ACCEPT", "Pause for occupancy, resume, accept."],
        ]),

      // ---- 6 Prompts ----
      h1("6. Prompts Used During AI-Assisted Coding"),
      p("The project was built with Claude Code (Opus) as the pair-programmer, working from an approved architecture spec. Two kinds of prompts mattered: build prompts that drove the AI coding tool, and the runtime agent prompts inside the system. Both are shown below."),
      h2("6.1 Representative Build Prompts (to the AI coding tool)"),
      numbered("“Formalize QuoteCopilot using the agent framework: write the one-liner, the eight-agent responsibility table, the state model, and the human-in-the-loop rules, then produce an approved architecture design doc.”"),
      numbered("“Scaffold the repo: FastAPI app factory + routes, a LangGraph parent graph composing four subgraphs over a shared RunState TypedDict, agents/ separate from graph/, deterministic rules and rating tools, and a hybrid RAG retriever. Keep llm/factory.py as the single model-selection point.”"),
      numbered("“Make every LLM call optional with a deterministic fallback so the whole system runs and tests offline. Decisions must come from the rule engine, never from LLM text.”"),
      numbered("“Implement same-run pause/resume: when required fields are missing, pause the run as waiting_for_info, store state, and resume the identical run_id after answers are supplied.”"),
      numbered("“Add a labeled eval harness scoring decision accuracy, reason-code match, missing-info detection, review-required match, and citation faithfulness; write results JSON with --report.”"),
      numbered("“Add a Nebius Token Factory provider via the OpenAI-compatible endpoint so at least one model call can run on Nebius, and let a single .env switch providers.”"),
      numbered("“Debugging pass: 17 integration tests error on settings load — find the root cause and fix it; then confirm a live Nebius call actually succeeds end-to-end and run the eval on Nebius.”"),
      h2("6.2 Runtime Agent System Prompts (verbatim)"),
      p("Agents call a single guardrailed helper, complete_text(role, system, user, fallback), which returns the deterministic fallback whenever the LLM is unavailable or errors. The three language-bearing roles use these exact system prompts:"),
      runs([new TextRun({ text: "Normalizer — ", bold: true }), new TextRun("phrases follow-up questions:")]),
      codeBlock("You are an insurance intake assistant. Rewrite each underwriting follow-up question to be clear and polite. Keep one line per question."),
      runs([new TextRun({ text: "Packager — ", bold: true }), new TextRun("phrases next steps, never invents evidence:")]),
      codeBlock("You are an underwriting assistant. Given a recommendation and reason codes, list concise next steps, one per line. Do not invent facts."),
      runs([new TextRun({ text: "Critic — ", bold: true }), new TextRun("optional faithfulness review, structured output:")]),
      codeBlock("You are a critical underwriting reviewer. Given a decision packet, respond with strict JSON {\"passed\": bool, \"issues\": [str]}. Flag only genuine completeness or faithfulness problems."),
      p("Citations are selected only from the retrieved evidence set in code (not by the model), so faithfulness is structurally enforced rather than prompted."),

      // ---- 7 Iterations ----
      h1("7. Iterations We Tried"),
      dataTable([2400, 3480, 3480],
        ["Iteration", "What we tried", "Outcome"],
        [
          ["Single graph → subgraphs", "Started toward one flat graph; moved to four hierarchical subgraphs over a shared RunState.", "Cleaner pause/resume at multiple levels; agents stay independently testable."],
          ["LLM decisions → deterministic rules", "Considered letting the model decide eligibility.", "Rejected. Rules engine is the source of truth; LLM only phrases language. Made faithfulness 100% and decisions reproducible."],
          ["Semantic-only → hybrid retrieval", "Began with semantic ChromaDB search.", "Added BM25 + RRF + cross-encoder re-rank so exact rule terms (reason codes, occupancy terms) match reliably."],
          ["Provider lock-in → switchable factory", "Anthropic-only at first.", "Refactored to a provider factory (anthropic/openai/nebius) selected by a single .env; added Nebius Token Factory for the cohort comparison requirement."],
          ["Settings crash on empty map", "AGENT_MODEL_MAP= (empty) crashed pydantic-settings JSON decode — 17 integration tests errored.", "Fixed config parsing / supplied valid JSON; full suite back to 28/28 passing."],
          ["Stale Nebius model IDs", "Default Nebius model names 404’d on the live endpoint.", "Updated to currently-hosted IDs (Qwen3-30B, Llama-3.3-70B) and extended the claude→Nebius swap to AGENT_MODEL_MAP overrides; live calls and a 100% Nebius eval confirmed."],
        ]),

      // ---- 8 Evaluation ----
      h1("8. Evaluation & Results"),
      p("The eval harness runs every labeled case through the full graph and scores five metrics. The run below was executed end-to-end with LLM_PROVIDER=nebius (the Nebius Token Factory requirement), 10/10 cases, results saved to evals/results/2026-06-18.json."),
      h2("8.1 Metrics"),
      dataTable([4360, 2500, 2500],
        ["Metric", "Target", "Result"],
        [
          ["Decision accuracy", "≥ 95%", "100%"],
          ["Reason-code exact match", "≥ 90%", "100%"],
          ["Missing-info detection", "≥ 95%", "100%"],
          ["Review-required match", "100%", "100%"],
          ["Citation faithfulness", "100%", "100%"],
        ]),
      h2("8.2 Per-Case Results (10/10)"),
      dataTable([3120, 1248, 1248, 1248, 1248, 1248],
        ["Case", "Decision", "Reason", "Missing", "Review", "Cite"],
        [
          ["accept_001", "✓", "✓", "✓", "✓", "✓"],
          ["refer_roof_age", "✓", "✓", "✓", "✓", "✓"],
          ["decline_roof_age", "✓", "✓", "✓", "✓", "✓"],
          ["decline_vacant", "✓", "✓", "✓", "✓", "✓"],
          ["refer_rental", "✓", "✓", "✓", "✓", "✓"],
          ["refer_wildfire", "✓", "✓", "✓", "✓", "✓"],
          ["refer_flood", "✓", "✓", "✓", "✓", "✓"],
          ["refer_claims", "✓", "✓", "✓", "✓", "✓"],
          ["missing_roof_age", "✓", "✓", "✓", "✓", "✓"],
          ["missing_occupancy", "✓", "✓", "✓", "✓", "✓"],
        ]),
      h2("8.3 Key Findings"),
      bullet([new TextRun({ text: "Decisions are deterministic by design. ", bold: true }), new TextRun("Because the rule engine — not the LLM — produces every recommendation and reason code, decision accuracy and reason-code match are reproducible across providers (Anthropic and Nebius give identical decisions).")]),
      bullet([new TextRun({ text: "Citation faithfulness is structural, not prompted. ", bold: true }), new TextRun("Citations are drawn in code only from the retrieved evidence set, so the 100% faithfulness figure is enforced by construction rather than by trusting the model.")]),
      bullet([new TextRun({ text: "Product tests back the eval. ", bold: true }), new TextRun("28 tests pass — unit (rules engine, rating tool, state schema) and integration (full graph runs and API for accept, missing-info resume, decline→review, and review actions).")]),
      bullet([new TextRun({ text: "The corpus is small and well-structured, ", bold: true }), new TextRun("so retrieval reliably surfaces the right guideline; a larger, noisier corpus would put more pressure on the hybrid retriever and re-ranker.")]),

      // ---- 9 HITL ----
      h1("9. Human-in-the-Loop & Failure Handling"),
      p("The agent is deliberately conservative about write actions. Reads and analysis are autonomous; anything that changes review status routes to a human. Failure handling is explicit rather than best-effort:"),
      bullet("Missing required fields → pause run, generate targeted questions, preserve state, resume same run_id."),
      bullet("Invalid payload → field-level validation error (Pydantic), no run created."),
      bullet("Retrieval returns no chunks → continue only if deterministic rules support the decision; otherwise route to review."),
      bullet("LLM structured/text output fails → retry, then deterministic fallback wording; decision unaffected."),
      bullet("Verifier blocks or downgrades, or any REFER/DECLINE → create a human review task with decision, reason codes, questions, citations, and priority."),

      // ---- 10 Limitations ----
      h1("10. Limitations & Future Work"),
      bullet("Synthetic guidelines and data only — not real carrier rules; no binding, issuance, or payments."),
      bullet("Hazard/territory enrichment is deterministic and local; real wildfire/flood/credit/claims APIs would sit behind the same tool boundary."),
      bullet("The Critic agent is implemented but disabled by default (CRITIC_ENABLED=false) to keep latency and cost predictable for the demo."),
      bullet("Evaluation set is 10 curated cases; broadening coverage and adding adversarial/invalid-payload cases would strengthen the recall and faithfulness signals."),
      bullet("On Nebius, the assessor/packager use Llama-3.3-70B in place of the Claude models named in AGENT_MODEL_MAP; quality is comparable for wording but not identical."),

      // ---- 11 Learnings ----
      h1("11. Learnings & Observations"),
      p("Selected takeaways from building an agentic system with an AI pair-programmer:"),
      numbered("The hard parts were not the prompts — they were control flow, state, and the autonomy boundary. Deciding what pauses, what persists, and what needs a human shaped the architecture far more than any single prompt.", "learnings"),
      numbered("Put the model where language lives, not where judgment lives. Making deterministic rules the source of truth and the LLM a wording layer gave reproducible decisions and structurally-enforced citation faithfulness.", "learnings"),
      numbered("Design for offline first. A deterministic fallback on every LLM call meant the full system, tests, and evals run with no API key — which made debugging fast and CI trivial, and meant a provider outage degrades gracefully instead of failing.", "learnings"),
      numbered("A provider factory pays off immediately. Isolating model selection in one module let us add Nebius and switch providers from a single .env, and surfaced the two real integration bugs (empty-map settings crash, stale model IDs) in one place.", "learnings"),
      numbered("Evidence before “done.” The handout’s warning — happy path is not a finished agent — held true: the bugs that mattered only appeared when we forced a live Nebius call and ran the full suite, not in the offline path that always passed.", "learnings"),
      numbered("The framework-first exercise was worth it. Writing the one-liner, state model, and HITL rules before any code meant the implementation had a spec to verify against rather than being discovered ad hoc.", "learnings"),

      rule(),
      new Paragraph({ spacing: { before: 120 }, children: [
        new TextRun({ text: "Submission artifacts: ", bold: true }),
        new TextRun("source on GitHub (QuoteCopilot/), this writeup, the labeled eval results (evals/results/2026-06-18.json), the architecture design doc (docs/superpowers/specs/), and a demo video — separate deliverable."),
      ] }),
    ],
  }],
});

const outPath = path.join(__dirname, "..", "docs", "QuoteCopilot_Project_Writeup.docx");
Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(outPath, buf); console.log("wrote " + outPath); });
