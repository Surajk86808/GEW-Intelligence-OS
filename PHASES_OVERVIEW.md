# GEW Intelligence OS - Pipeline Phases Overview

This document provides a detailed breakdown of the processing pipeline for the GEW Intelligence OS. The architecture is designed as a sequential, multi-stage pipeline where each phase enriches the data before passing it to the next.

## Phase 1: CRM Mapping & Audio Acquisition
**Directory:** `phase_1_map_and_download`  
**Purpose:** The entry point of the system. It bridges the gap between the CRM (Excel/Master Sheets) and the raw audio data.
- **CRM Integration:** Parses lead sheets and master workbooks to identify calls that require processing.
- **Lead-Call Linkage:** Maps unique lead identifiers to specific recording URLs or local audio files.
- **Audio Acquisition:** Downloads recordings from cloud storage (or identifies local paths) for the processing environment.
- **Manifest Generation:** Produces the `call_manifest.json`, which serves as the "source of truth" and workload definition for all subsequent phases.

## Phase 2: High-Fidelity Transcription
**Directory:** `phase_2_transcription`  
**Purpose:** Transforms raw audio into structured, timestamped text.
- **Audio Preprocessing:** Normalizes sample rates, removes silence, and optimizes audio quality for AI models.
- **Speech-to-Text (STT):** Utilizes Faster-Whisper models for highly accurate, multi-lingual transcription.
- **Diarization:** Distinguishes between different speakers (e.g., Salesperson vs. Customer) to maintain conversational context.
- **Transcript Structuring:** Outputs JSON-formatted transcripts with word-level timestamps, speaker labels, and metadata.

## Phase 3: Voice Intelligence & Acoustic Analysis
**Directory:** `phase_3_ai_reasoning_enrichment_layer`  
**Purpose:** Extracts emotional and acoustic signals that go beyond simple text, capturing "how" things were said.
- **Emotion Detection:** Identifies sentiment shifts (Interest, Frustration, Confidence) across the conversation timeline.
- **Acoustic Metrics:** Measures volume variance, pitch, and speech rate to detect stress, hesitation, or escalation.
- **Silence & Engagement:** Tracks pauses, interruptions, and "talk-to-listen" ratios to measure conversational flow and engagement.
- **Unified Timeline:** Merges acoustic and emotional data into a searchable "Intelligence Timeline" for every call.

## Phase 4: Strategic Reasoning (LLM Analysis)
**Directory:** `phase_4_reasoning`  
**Purpose:** Performs high-level semantic analysis of the conversation using Large Language Models.
- **Strategic Summary:** Generates concise, executive-level summaries of the call's outcome and next steps.
- **Reasoning Tags:** Applies categorical tags for downstream filtering (e.g., "Pricing Objection," "Competition Comparison," "Technical Query").
- **Intent Analysis:** Identifies the primary goal of the caller and evaluates the salesperson's effectiveness in addressing it.
- **Logic Engine:** Uses Gemini models to "read between the lines," identifying subtle cues and business opportunities.

## Knowledge Layer: Conversational Memory & LLM Feeding
**Directory:** `phase_4_knowledge_layer & llm_feeding`  
**Purpose:** Prepares data for long-term memory, RAG (Retrieval-Augmented Generation), and rapid cross-call analysis.
- **Semantic Chunking:** Breaks long conversations into meaningful, context-aware segments.
- **Vector Embeddings:** Converts conversation chunks into high-dimensional numerical vectors for semantic similarity search.
- **Indexing:** Manages a local vector database and metadata store, allowing the system to "remember" details across thousands of historical calls.
- **Evidence Retrieval:** Provides the infrastructure to query the entire call history for specific patterns or recurring objections.

## Phase 5: Decision Intelligence & Recommendations
**Directory:** `phase_5_decision_intelligence`  
**Purpose:** Translates raw insights into actionable business intelligence and automated recommendations.
- **Analytics Engine:** Aggregates performance data across different campaigns, regions, and salespeople.
- **Recommendation Engine:** Suggests concrete "Next Best Actions" based on the call's reasoning and emotional trajectory.
- **Citation & Evidence:** Ensures every AI-generated claim is backed by specific, timestamped evidence from the original transcript.
- **Reporting:** Generates automated, branded performance reports and dashboards for management stakeholders.

## Phase 6: Structured Export & Schema Validation
**Directory:** `phase_6_structured_json`  
**Purpose:** Finalizes the data for ingestion into production CRM systems or Business Intelligence (BI) platforms.
- **Data Compilation:** Merges outputs from all previous phases into a single, unified, and comprehensive JSON record per call.
- **Schema Validation:** Strictly enforces data contracts to ensure that every export is consistent and machine-readable.
- **Structured Storage:** Archives the final enriched data in a standardized format, ready for long-term storage or API integration.
