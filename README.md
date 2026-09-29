# Computer Science Knowledge RAG

A production-oriented Retrieval-Augmented Generation (RAG) system for the Computer Science department.

The system is designed to provide **accurate, source-grounded answers from institutional records** stored across sources such as Google Drive, PDFs, Excel files, Google Sheets, and other structured or unstructured data.

The primary goal is not simply to build a chatbot. The goal is to build a reliable **institutional knowledge retrieval system** where every answer can be traced back to the original source.

---

## 1. Project Overview

Institutional information is often distributed across multiple files and systems:

* PDF documents
* Meeting minutes
* Event reports
* Notices
* Excel spreadsheets
* Google Sheets
* Images
* Scanned documents
* Structured databases

Finding information manually across these sources is time-consuming.

This project provides a unified natural-language interface for searching this information.

For example:

> What happened in the Computer Science department on 18 July 2026?

The system should identify the relevant records, retrieve the supporting evidence, and generate an answer based only on that evidence.

---

## 2. Core Objectives

The system is designed around the following objectives:

### Accuracy

Answers must be based on actual institutional records rather than unsupported model knowledge.

### Source Grounding

Every factual answer should be traceable to its original source whenever possible.

### Exact Retrieval

Queries involving dates, names, meetings, events, attendance, and other structured information should support exact filtering.

### Hybrid Search

The system will combine:

* Keyword search
* Semantic/vector search
* Metadata filtering
* Structured data retrieval
* Reranking

### Document Understanding

The system should process different types of institutional documents while preserving their original structure and provenance.

### OCR Support

Scanned documents and images containing useful text should be processed using OCR where required.

### Synchronization

When source documents are updated or deleted, the indexed data should reflect the current source state.

### Security

Only authenticated and authorized users should be able to access institutional information.

---

## 3. Current Scope

### Department

The initial implementation focuses on:

**Computer Science Department**

The system is designed so that additional departments can be supported in the future.

### Data Sources

The planned data sources include:

* Google Drive
* Google Sheets
* PDF files
* Excel files
* Images
* Structured databases

The exact production data sources will be confirmed during implementation.

### Example Information

The system may contain information about:

* Faculty meetings
* Staff meetings
* Student activities
* Faculty activities
* Events
* C-START programs
* Notices
* Reports
* Attendance
* Decisions
* Action items
* Department activities

---

## 4. Example Queries

The system should eventually support queries such as:

```text
What happened on 18 July 2026?

What was discussed in the Computer Science meeting on 18 July 2026?

Who attended the meeting?

What decisions were made?

What action items were assigned?

When was the C-START program conducted?

Who was invited to the C-START session?

Show the report for the event conducted in July 2026.

Find all meetings where student engagement was discussed.
```

The system should distinguish between questions that can be answered from available evidence and questions for which reliable evidence does not exist.

---

## 5. High-Level Architecture

```text
                    ┌─────────────────────┐
                    │      User Query     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Query Analysis    │
                    │                     │
                    │ Date / Entity /     │
                    │ Intent / Filters    │
                    └──────────┬──────────┘
                               │
                 ┌─────────────┼─────────────┐
                 │             │             │
                 ▼             ▼             ▼
          Keyword Search  Vector Search  Metadata/
                                         Structured Search
                 │             │             │
                 └─────────────┼─────────────┘
                               ▼
                    ┌─────────────────────┐
                    │     Reranking       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   Evidence Gate     │
                    │                     │
                    │ Is the evidence     │
                    │ sufficient?         │
                    └──────────┬──────────┘
                               │
                         ┌─────┴─────┐
                         │           │
                        YES          NO
                         │           │
                         ▼           ▼
                  ┌────────────┐   Refuse /
                  │    LLM     │   Insufficient
                  └─────┬──────┘   Evidence
                        │
                        ▼
              ┌─────────────────────┐
              │ Answer + Sources +  │
              │ Relevant Images     │
              └─────────────────────┘
```

---

## 6. Data Ingestion Pipeline

Source data will be processed through an ingestion pipeline.

```text
Google Drive
     │
     ▼
File Discovery
     │
     ▼
Document Identification
     │
     ├── PDF
     ├── Excel
     ├── Google Sheet
     ├── Image
     └── Other Supported Format
     │
     ▼
Content Extraction
     │
     ├── Text
     ├── Tables
     ├── Metadata
     ├── Dates
     └── Images
     │
     ▼
OCR (when required)
     │
     ▼
Chunking
     │
     ▼
Embeddings
     │
     ▼
PostgreSQL + pgvector
```

---

## 7. Date-Aware Retrieval

Date-based questions are a major requirement of the system.

A document may contain multiple dates.

For example:

```text
File:
CS Meeting 18 July 2026.pdf

Meeting Date:
18 July 2026

Google Drive Created:
20 July 2026

Google Drive Modified:
02 August 2026
```

These dates represent different things.

The system must therefore preserve different date types rather than treating every date as the same.

Possible date types include:

* Meeting date
* Event date
* Document date
* Filename date
* Date mentioned in content
* Source creation timestamp
* Source modification timestamp

Source creation and modification timestamps must not automatically be treated as the event date.

When conflicting dates are detected, the system should preserve the conflict rather than silently choosing an incorrect date.

---

## 8. Document Provenance

The system must preserve the relationship between an answer and its original source.

```text
Answer
   │
   ▼
Retrieved Chunk
   │
   ▼
Page / Row / Sheet
   │
   ▼
Document
   │
   ▼
Original Source
```

Example citation:

```text
CS Meeting Minutes - July 2026.pdf
Page 4
Google Drive
```

For spreadsheets:

```text
CS_Meetings.xlsx
Sheet: July Meetings
Row: 18
```

This allows users to verify the information themselves.

---

## 9. Hallucination Control

The LLM is not treated as the source of truth.

The source documents are the source of truth.

The intended flow is:

```text
Retrieve Evidence
       ↓
Evaluate Evidence
       ↓
Generate Answer
```

If sufficient evidence cannot be found, the system should not invent an answer.

Example:

```text
User:
What happened on 1 January 1900?

System:
No reliable information was found in the available
Computer Science department records for that date.
```

The evidence policy will be evaluated using a collection of real questions and expected source documents.

---

## 10. OCR and Image Processing

Some institutional information may exist inside:

* Scanned PDFs
* Embedded images
* Screenshots
* Image-based documents

The system will use progressive OCR.

### Level 1

Extract text from normal PDFs first.

### Level 2

OCR images embedded inside documents when necessary.

### Level 3

Detect scanned PDFs and perform page-level OCR.

### Level 4

Handle difficult scans such as rotated or low-quality documents when required.

Handwritten-text support will only be added if the actual data requires it.

OCR results will preserve provenance such as:

```text
Document
```
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      