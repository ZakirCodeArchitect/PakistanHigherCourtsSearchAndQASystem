# QA Pipeline Analytics — 2025-11-08  
  
## Upstream PDF Availability  
- Cases in database: 805  
- Cases linked to any PDF (`CaseDocument`): **84**  
- Documents downloaded / processed / cleaned: **160** (all stages complete)  
- Text pages extracted (`DocumentText` rows with content): **407**  
- Cases providing judgement PDFs: 51  
- Orders rows with actual PDF links: 226 (out of 358)  
  
Observations: most `orders_data.view_link` entries are empty strings or empty lists, so only 84 cases yield real documents. Missing PDF links are the main blocker to higher QA coverage.  
  
## QA Processing Snapshot  
- QA entries created after `process_qa_knowledge_base --all-cases --force-reprocess`: **3,794**  
- Cases with QA coverage: **85** (10.6 % of 805)  
- Average content quality score: 0.751  
- Average legal relevance score: 0.538  
- QA entries currently indexed: 544 (14.3 % coverage)  
  
## Next Actions  
1. **Increase PDF coverage**: enhance or re-run scrapers so `orders_data.view_link` and `judgement_data.pdf_url` populate for the remaining cases.  
2. **Re-run the PDF pipeline** (`run_complete_pipeline`) once more links exist to regenerate `Document`, `DocumentText`, and `UnifiedCaseView` content.  
3. **Re-run QA ingestion** (`process_qa_knowledge_base --all-cases --force-reprocess`) to create new chunks.  
4. **Rebuild QA indexes** after ingestion so the new entries are searchable.  


