# GEW Intelligence OS

GEW Intelligence OS is a high-performance, multi-phase pipeline designed to transform raw call data into actionable business intelligence. It bridges the gap between CRM data and voice interactions using advanced AI for transcription, acoustic analysis, emotional intelligence, and strategic reasoning.

## 🚀 Key Features

- **End-to-End Pipeline:** Automates the journey from raw CRM leads to deep conversational insights.
- **High-Fidelity Transcription:** Uses `faster-whisper` for accurate, timestamped, and diarized transcripts.
- **Voice Intelligence:** Extracts emotional shifts, acoustic metrics (stress, pitch, volume), and engagement scores.
- **Strategic Reasoning:** Leverages Gemini (LLM) to perform semantic analysis, intent detection, and strategic summarization.
- **Knowledge Layer:** Implements RAG (Retrieval-Augmented Generation) with semantic chunking and vector embeddings for long-term conversational memory.
- **Query Intelligence:** Advanced decision engine for analytics, reporting, and evidence-backed recommendations.

## 📁 Project Structure

The project is organized into sequential phases, each building upon the output of the previous one.

### [Phase 1: Audio Ingestion & Transcription](./phase_1_audio_ingestion_transcription/)
- **Ingestion:** Maps CRM data (Excel/Master Sheets) to audio files and downloads recordings.
- **Transcription:** Normalizes audio and generates high-fidelity transcripts with speaker labels.

### [Phase 2: Enrichment & Structured Extraction](./phase_2_enrichment_structured_extraction/)
- **Voice Intelligence:** Analyzes acoustic signals and emotional trajectories.
- **Enrichment:** Merges transcript data with voice metrics to create a unified intelligence timeline.

### [Phase 3: AI Reasoning](./phase_3_ai_reasoning/)
- **LLM Analysis:** Uses Large Language Models to extract strategic insights, identify objections, and evaluate performance.
- **Recommendation Engine:** Suggests "Next Best Actions" based on the call's outcome.

### [Phase 4: Knowledge & Memory](./phase_4_knowledge_memory/)
- **Semantic Memory:** Chunks and embeds conversations into a vector store.
- **Retrieval:** Provides the infrastructure for cross-call analysis and semantic search.

### [Phase 5: Query Intelligence](./phase_5_query_intelligence/)
- **Decision Engine:** Aggregates data for analytics, report generation, and executive dashboards.
- **Citation Engine:** Ensures all insights are linked back to specific evidence in the transcripts.

### [Shared Infrastructure](./shared/)
- Centralized utilities for logging, configuration, JSON handling, workbook I/O, and data schemas.

## 🛠️ Tech Stack

- **Language:** Python 3.10+
- **Transcription:** [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- **AI/LLM:** Google GenAI (Gemini), Hugging Face Transformers
- **Audio Processing:** Librosa, FFmpeg
- **Data Science:** Pandas, NumPy, Scikit-learn
- **Workbook Handling:** openpyxl
- **CLI/UI:** Rich

## 🏁 Getting Started

### Prerequisites

- Python 3.10 or higher
- FFmpeg installed on your system
- A `.env` file with necessary API keys (see `.env.template`)

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Gew
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

Copy `.env.template` to `.env` and fill in your credentials:
```bash
cp .env.template .env
```
Key requirements:
- `GOOGLE_API_KEY`: For Gemini-based reasoning and analysis.

## 🚀 Running the Pipeline

The pipeline is designed to be run in stages.

- **Phase 1 (Ingestion & Transcription):**
  ```bash
  python main.py
  ```

- **Downstream Phases (Knowledge & Query):**
  ```bash
  python run_current_phases.py
  ```

- **Individual Phases:**
  Each phase can be run as a module:
  ```bash
  python -m phase_2_enrichment_structured_extraction.main
  python -m phase_3_ai_reasoning.main
  ```

## 🔍 Development Tools

- `tools/validate_architecture.py`: Ensures architectural integrity by blocking illegal cross-phase imports. Run this before committing changes.

## 📄 Documentation

- [Phases Overview](./PHASES_OVERVIEW.md): Detailed breakdown of each phase's goals.
- [Architecture Cleanup Report](./ARCHITECTURE_CLEANUP_REPORT.md): Details on the refactored system structure and validation rules.
- [Transcription Rebuild](./TRANSCRIPTION_REBUILD.md): Documentation on the transcription engine update.
- [Background Processing](./BACKGROUND_PROCESSING.md): Guide for running long-running tasks.
