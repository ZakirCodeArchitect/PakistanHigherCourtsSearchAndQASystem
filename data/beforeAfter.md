# Judgments: Raw Data vs After Pipeline (First 3–4 Rows)

This document shows the **actual data** from the first rows of `data/judgments_test.xlsx` and what happens to it through **import → cleaning → pipeline → search indexing**.

---

## Row 1 (Excel)

### BEFORE (raw in Excel)

| Field | Value |
|-------|--------|
| **case_number** | `2011 SBLR 69` |
| **court** | `Balochistan High Court` |
| **decision_date** | `2010-03-08 00:00:00` |
| **judges** | `GHULAM MUSTAFA MENGAL` |
| **disposition** | *(empty)* |
| **who_vs_who** | `MST. SHAHNAZ PARVEEN & OTHERS (PETITIONERS) VERSUS ABDUL AZIZ & ANOTHER (RESPOND...` |
| **full_text** | `2011 SBLR 69\n\n[Balochistan High Court]\n\nJudges:\nGHULAM MUSTAFA MENGAL\n\n\nJudgment GHULAM MUSTAFA MENGAL, J.- This Civil Revision Petition under Section 115 C.P.C is directed against the Judgment and de...` |
| **headnote_text** | `["dismissed.  The precise facts of the case are that the Respondents filed <b>a</b> suit for declaration, cancellation of agreement dated 31.07.1982 attested on 01.08.1982 and possession of house bear...` |
| **advocates** | `MISS SARWAT HINA, ADVOCATE FOR THE PETITIONERS. MR. MANZAR SIDDIQUE, ADVOCATE FO...` |

---

### AFTER PIPELINE

**1. Import** (what gets stored in DB as-is)

- **Case:** `case_number=2011 SBLR 69`, `case_title=MST. SHAHNAZ PARVEEN & OTHERS...` (from who_vs_who), `status=` (from disposition, empty), `bench=GHULAM MUSTAFA MENGAL`, `institution_date=2010-03-08`, `court` → Court "Balochistan High Court".
- **CaseDetail:** `before_bench=GHULAM MUSTAFA MENGAL`, `case_disposal_date=2010-03-08`, `disposed_of_status=` (empty), `advocates_petitioner=MISS SARWAT HINA...`, `headnote_text=` (Excel value as string or list joined with newlines).
- **DocumentText:** `raw_text` and initially `clean_text` = full judgment text (same as full_text).
- **Document:** synthetic, `file_path=imported/1_<uuid>.txt`.

**2. clean_imported_judgment_text** (full_text only)

- **DocumentText.clean_text** is overwritten with cleaned version of full_text:
  - HTML tags removed (none in this snippet).
  - Excessive spaces → single space; multiple newlines → `\n\n`; leading/trailing spaces removed.
  - Unicode normalized (NFKC).
- **Before (snippet):** `"2011 SBLR 69\n\n[Balochistan High Court]\n\nJudges:\nGHULAM MUSTAFA MENGAL\n\n\nJudgment GHULAM..."`
- **After (snippet):** Same structure but `\n\n\n` → `\n\n`, extra spaces within lines collapsed to single space.

**3. Pipeline metadata cleaning** (Case, CaseDetail)

- **disposition** (empty): stays empty; `_normalize_status("")` → `""`.
- **headnote_text:** `_clean_long_text()` applied:
  - **Before:** `...filed <b>a</b> suit for declaration...` (HTML `<b>a</b>`).
  - **After:** `...filed a suit for declaration...` (tags stripped, spaces normalized, paragraph breaks `\n\n` kept).
- **advocates:** `_clean_advocates_text()`:
  - **Before:** `MISS SARWAT HINA, ADVOCATE FOR THE PETITIONERS. MR. MANZAR SIDDIQUE...`
  - **After:** HTML stripped (if any), `;` → `, `, multiple spaces → single space, trim. Same content, normalized separators.

**4. Keyword indexing (SearchMetadata – normalized fields)**

- **case_number_normalized:** `normalize_text("2011 SBLR 69")` → `"2011 sblr 69"` (lowercase; no legal abbrev change for SBLR).
- **case_title_normalized:** from who_vs_who → lowercase, legal abbrevs (e.g. `vs` → `vs`), extra spaces collapsed. Example: `"mst. shahnaz parveen & others (petitioners) versus abdul aziz & another (respond..."`.
- **court_normalized:** `"balochistan high court"`.
- **status_normalized:** `""` (empty).
- **parties_normalized:** parties list joined with ` | ` (e.g. `"MST. SHAHNAZ PARVEEN | ABDUL AZIZ"` if extracted), then not lowercased in the join but the normalize step would lowercase if applied to the string.

So for **Row 1** you see: raw Excel → import into Case/CaseDetail/DocumentText → full_text cleaned in DocumentText → disposition/headnote/advocates cleaned in CaseDetail → normalized copies in SearchMetadata for search.

---

## Row 2 (Excel)

### BEFORE (raw in Excel)

| Field | Value |
|-------|--------|
| **case_number** | `2013 PTCL 563` |
| **court** | `Sindh High Court` |
| **decision_date** | `2013-03-20 00:00:00` |
| **judges** | `MR. JUSTICE FAISAL ARAB AND MR. JUSTICE NADEEM AKHTAR.` |
| **disposition** | *(empty)* |
| **who_vs_who** | `PETITIONERS: RESPONDENTS:M/S. SHELL (PAKISTAN)LTD. VERSUS : FEDERATION OF PAKIST...` |
| **full_text** | `2013 PTCL 563\n\n[Sindh High Court]\n\nJudges:\nMR. JUSTICE FAISAL ARAB AND MR. JUSTICE NADEEM AKHTAR.\n\n\nJudgment ORDER: MR. JUSTICE FAISAL ARAB.--(l). After scrutinizing the tax returns of the petitioners...` |
| **headnote_text** | `["thousands of tax returns is <b>a</b> time consuming job. <b>A</b> taxpayer may have evaded <b>a</b> tax liability...` |
| **advocates** | `REPRESENTED:PETITIONERS BY: MR. MUHAMMAD FAROGH NASEEM, MR, NAVEEDANDRABI AND MR...` |

### AFTER PIPELINE (same steps)

- **Import:** Case (2013 PTCL 563, Sindh High Court, bench = MR. JUSTICE FAISAL ARAB...), CaseDetail (headnote_text with `<b>a</b>`, `<b>A</b>`; advocates with `MR, NAVEEDANDRABI`).
- **clean_imported_judgment_text:** full_text cleaned (spaces, newlines, no HTML in this snippet).
- **Pipeline metadata cleaning:**
  - **headnote_text:** `"<b>a</b>"` → `"a"`, `"<b>A</b>"` → `"a"` (HTML stripped, so text becomes plain).
  - **advocates:** `"MR, NAVEEDANDRABI"` → separator normalized to `", "` (comma-space).
- **Normalized (SearchMetadata):** `case_number_normalized` = `"2013 ptcl 563"`, `court_normalized` = `"sindh high court"`, etc.

---

## Row 3 (Excel)

### BEFORE (raw in Excel)

| Field | Value |
|-------|--------|
| **case_number** | `1961 PLD 515` |
| **court** | `Federal Court Of Pakistan` |
| **decision_date** | `1960-12-23 00:00:00` |
| **judges** | `MUHAMMAD YAQUB ALI, SAJJAD AHMAD AND BASHIR AHMAD` |
| **disposition** | *(empty)* |
| **who_vs_who** | *(empty)* |
| **full_text** | `1961 PLD 515\n\n[Federal Court Of Pakistan]\n\nJudges:\nMUHAMMAD YAQUB ALI, SAJJAD AHMAD AND BASHIR AHMAD\n\n\nJudgment Judgment Bashir Ahmad, J.-This order will dispose of the proceedings against Mr. Sikanda...` |
| **headnote_text** | *(empty)* |
| **advocates** | *(empty)* |

### AFTER PIPELINE

- **Import:** Case (1961 PLD 515, Federal Court Of Pakistan, etc.), CaseDetail (empty headnote_text, empty advocates), DocumentText (full_text).
- **Cleaning:** full_text cleaned; no headnote/advocates to clean.
- **Normalized:** `case_number_normalized` = `"1961 pld 515"`, `court_normalized` = `"federal court of pakistan"`.

---

## Summary: What we do with the data

| Step | What happens |
|------|----------------|
| **Import** | Excel columns → Case, CaseDetail, Document, DocumentText, CaseDocument. Raw strings stored as-is (with length limits). |
| **clean_imported_judgment_text** | `full_text` → strip HTML, collapse spaces, keep `\n\n`, normalize Unicode → **DocumentText.clean_text**. |
| **Pipeline metadata cleaning** | **Case:** status/bench trimmed and status mapped (e.g. dismissed→Dismissed). **CaseDetail:** disposition normalized, **headnote_text** and advocates cleaned: HTML stripped, separators `, `; headnote keeps paragraphs. |
| **Keyword indexing** | Build **SearchMetadata** from Case/CaseDetail: **normalized** fields = lowercase + legal abbreviations (Cr.P.C.→crpc, etc.) + collapse spaces → used for BM25/keyword search. |

So: **before** = raw Excel (and raw DB after import); **after** = cleaned and normalized values in the same DB plus SearchMetadata for search.

---

## Making data searchable (indexing)

After the pipeline, we run **build_indexes** so users can search and filter.

**1. Searchable (find by query)**

- **Vector index:** Judgment text (from UnifiedCaseView / DocumentText.clean_text) is chunked, embedded, and stored in the vector DB (e.g. Pinecone). A user query is embedded and matched to similar chunks. So **full_text** (cleaned) is what makes judgments **searchable by meaning**.
- **Keyword index:** SearchMetadata rows (case_number_normalized, case_title_normalized, parties_normalized, court_normalized, status_normalized, searchable_keywords) are used by BM25/keyword search. So **normalized metadata + keywords** make cases **searchable by words** (case numbers, titles, parties, etc.).

**2. Filterable (narrow by court, year, status, judge)**

Filtering does **not** use the vector or BM25 index content. It uses **structured fields** already stored on **Case** and **CaseDetail** at import (and cleaned by the pipeline):

| Filter | Source in DB | Example (Row 1) |
|--------|----------------|-----------------|
| **court** | Case.court (Court.name) | Balochistan High Court |
| **year** | Case.institution_date or CaseDetail.case_disposal_date (year part) | 2010 |
| **status** | Case.status, CaseDetail.disposed_of_status | (empty) or e.g. Dismissed |
| **judge** | Case.bench, CaseDetail.before_bench | GHULAM MUSTAFA MENGAL |

**How filtering is applied**

- The search API accepts query params: `court`, `year`, `status`, `judge` (e.g. `?court=Balochistan High Court&year=2010`).
- **Vector path:** Chunks in the vector DB have metadata (court, year, status, judge). The search restricts to chunks whose metadata matches the filter (e.g. only court = "Balochistan High Court").
- **Keyword path:** Search runs on the keyword index; then results are restricted to cases that match the filter (by querying Case/CaseDetail or filtering SearchMetadata by court_normalized, institution_date year, status_normalized, bench).
- **Facets:** With `return_facets=true`, the API returns counts per court, status, year (and optionally judge) so the UI can show filter options (e.g. “Balochistan High Court (12)”, “2010 (5)”). Those counts come from Case/CaseDetail in the DB.

So: **searchable** = text in vector + keyword indexes; **filterable** = structured fields on Case/CaseDetail used to restrict or facet results.

---

## Real data example: filter values and how filtering works

Using the **same three rows** from the Excel (Rows 1–3), here is the **exact filterable data** stored for each case after import and pipeline, and how filter queries would behave.

**Row 1 — 2011 SBLR 69**

| Filter dimension | Stored value (from Case / CaseDetail) |
|------------------|---------------------------------------|
| court            | Balochistan High Court                |
| year             | 2010 (from decision_date 2010-03-08)   |
| status           | (empty)                                |
| judge            | GHULAM MUSTAFA MENGAL                  |

- Query **“civil revision”** → can match this case (text search).
- Filter **court = Balochistan High Court** → this case **included**.
- Filter **court = Sindh High Court** → this case **excluded**.
- Filter **year = 2010** → this case **included**.
- Filter **year = 2013** → this case **excluded**.
- Filter **judge = GHULAM MUSTAFA MENGAL** → this case **included**.

**Row 2 — 2013 PTCL 563**

| Filter dimension | Stored value (from Case / CaseDetail) |
|------------------|---------------------------------------|
| court            | Sindh High Court                      |
| year             | 2013 (from decision_date 2013-03-20)  |
| status           | (empty)                               |
| judge            | MR. JUSTICE FAISAL ARAB AND MR. JUSTICE NADEEM AKHTAR. |

- Filter **court = Sindh High Court** → **included**.
- Filter **year = 2013** → **included**.
- Filter **court = Balochistan High Court** → **excluded**.

**Row 3 — 1961 PLD 515**

| Filter dimension | Stored value (from Case / CaseDetail) |
|------------------|---------------------------------------|
| court            | Federal Court Of Pakistan             |
| year             | 1960 (from decision_date 1960-12-23)   |
| status           | (empty)                                |
| judge            | MUHAMMAD YAQUB ALI, SAJJAD AHMAD AND BASHIR AHMAD |

- Filter **court = Federal Court Of Pakistan** → **included**.
- Filter **year = 1960** → **included**.
- Filter **year = 2010** or **2013** → **excluded**.

**Example combined search + filter**

- **Query:** “revision petition”  
- **Filter:** court = Balochistan High Court, year = 2010  

Only cases with court = Balochistan High Court and year = 2010 are considered; among those, results are ranked by the search (vector + keyword). So Row 1 (2011 SBLR 69) can appear, while Row 2 and Row 3 are excluded by the filter.

**Summary**

- **Indexing** makes the judgment text and metadata **searchable** (vector + keyword).
- **Filtering** uses the **same real data** as in the tables above: court, year, status, and judge from Case/CaseDetail. No extra “filter index” is built—the API just restricts results (and facets) to cases matching the chosen court, year, status, and judge.
