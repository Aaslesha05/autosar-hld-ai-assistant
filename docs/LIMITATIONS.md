# AUTOSAR HLD AI Assistant — Known Limitations & Roadmap

This document outlines the known boundaries, limitations, and future architectural enhancements of the system.

---

## 1. Known Architectural Limitations

1. **Retrieval Confidence Indicator vs. Model Certainty**
   - The confidence score returned by the system is derived strictly from cosine similarity metrics and evidence coverage across retrieved chunks.
   - It is explicitly labeled as a **retrieval confidence indicator** and must not be interpreted as a mathematical guarantee of LLM internal certainty.

2. **Single-Node Persistent Vector Store**
   - ChromaDB runs as a local embedded persistent client (`data/chroma`). While fully isolated and performant for standalone and team environments, multi-node clustering or distributed indexing is reserved for enterprise scaling phases.

3. **Multi-Page Table Continuity**
   - Tables that span multiple pages are currently extracted on a per-page basis with their respective page headers. Cross-page table stitching into a single virtual entity is slated for future enhancements.

4. **Multi-Version Ambiguity Notice**
   - When a user submits a question across the entire repository without scoping to a specific document ID or version tag, chunks from both `v1.0` and `v2.0` may be retrieved. The system returns an advisory notice in `limitations`, but does not attempt to unilaterally resolve intentional specification conflicts between versions.

5. **OCR Processing Latency**
   - Scanned or purely image-based PDF pages incur additional image rendering and Tesseract processing time compared to native vector PDF pages.

---

## 2. Planned Roadmap & Future Enhancements

The following capabilities were intentionally excluded from Phase 4 per the master delivery specifications and are planned for future phases:

| Phase | Capability | Description |
|---|---|---|
| **Phase 5** | Entity Extraction & Architecture Knowledge Graph | Graph-based representation of SWCs, Interfaces, Ports, and Runnables using React Flow. |
| **Phase 6** | Safety & Inconsistency Rule Engine | Rule-based validation checking ISO 26262 ASIL-B crossing rules, port interface mismatch, and timing discrepancies. |
| **Phase 7** | Multi-Version Architectural Diff Engine | Visual side-by-side comparison highlighting added/modified SWCs, interfaces, and timing changes between HLD revisions. |
| **Phase 8** | Structured Engineering Report Generator | Automated export of formal architecture verification reports in PDF and Markdown format. |
| **Phase 9** | Enterprise RBAC & Cloud Deployment | Role-based access control, SSO integration, and Kubernetes orchestration manifests. |
