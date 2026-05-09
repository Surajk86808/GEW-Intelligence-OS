# Architecture Decision Record: Transcription Pipeline Rebuild

## 1. Original Vision

The initial goal of the GEW Intelligence OS transcription phase was to establish a robust foundation for automated sales intelligence. The pipeline was designed to:
- Ingest recorded sales calls at scale.
- Map these calls to corresponding CRM lead profiles.
- Generate highly accurate transcripts of telephonic conversations.
- Support complex, multilingual Indian telephonic conversations (primarily mixing Hindi, English, and Hinglish).
- Feed the resulting transcripts into Gemini for downstream semantic intelligence and structural analysis.

## 2. Initial Architecture

The first iteration of the pipeline attempted a semi-generative approach to speech transcription. The flow operated as follows:

`Raw Audio → Generative/Semi-Generative ASR Engine → Transcript Text → Gemini Analysis`

The system utilized early implementations of speech decoding coupled with generative prompt injection. Audio was fed directly into the model, often bypassing strict normalization, and utilized prompts instructing the model to "transcribe it faithfully" to attempt handling of multilingual constraints.

## 3. Problems Observed

During real-world testing and deployment with production telephonic audio, critical failures were observed. The pipeline proved entirely unsuitable for call intelligence due to the following anomalies:

- **Mixed Speech Corruption:** Conversations blending Hindi and English consistently corrupted, resulting in nonsensical output.
- **Multilingual Hallucinations:** The model regularly hallucinated entirely unrelated scripts, producing text in Urdu, Korean, Thai, and other random languages not present in the audio.
- **Transcript Discrepancies:** Generated text frequently did not match the actual spoken words, effectively rewriting sentences rather than transcribing them.
- **Audio Truncation:** The engine routinely skipped large chunks of audio. Three-minute calls frequently resulted in partial, truncated transcripts covering only the first few seconds.
- **Prompt Leakage:** The engine frequently hallucinated phrases directly from its own instructions, outputting the text "Transcribe it faithfully" as if it had been spoken by the caller.
- **Performance Degradation:** Inference was extremely slow, blocking batch processing capabilities.
- **Analytical Unreliability:** The combined output was vastly unreliable for any production-level analytics.

## 4. Root Cause Analysis

An investigation into these failures revealed several architectural flaws:

- **Improper ASR Architecture:** The system relied on an architecture that mixed language modeling behaviors with acoustic recognition, leading to generative decoding instability.
- **Prompt Leakage & Hallucination:** The ASR model was highly susceptible to prompt injection. The initial prompt ("This call may contain a mix of Hindi and English. Transcribe it faithfully.") leaked into the output distribution.
- **Lack of Audio Normalization:** Passing raw, unnormalized MP3s directly to the acoustic model resulted in irregular sampling rates and corrupted feature extraction.
- **Faulty VAD Configuration:** Aggressive Voice Activity Detection (VAD) configurations and unsuitable streaming logic caused the model to silently drop valid audio segments.
- **Non-Production Pipeline:** The implementation lacked the guardrails of a production-grade speech pipeline, attempting to rely on LLM-like generative capabilities for a purely deterministic signal processing task.

## 5. Why This Is Dangerous

Poor transcription compromises the entirety of a downstream AI system. In the context of a sales intelligence platform:

- **Sentiment Analysis Becomes Unreliable:** Hallucinated words completely invert customer sentiment metrics.
- **Invalid Lead Scoring:** Missing audio chunks cause the pipeline to miss critical buying signals, incorrectly scoring leads.
- **Corrupted Sales Intelligence:** Extracting customer intents, objections, and pain points fails entirely if the source text is hallucinated.
- **Misleading Analytics:** Aggregated analytics based on hallucinated data drive incorrect business decisions.
- **Trust Collapse:** End-users and sales teams will permanently abandon the intelligence platform if the fundamental transcripts do not match the call recordings.

## 6. New Architecture Decision

To resolve these systemic failures, the architecture has been entirely rebuilt to strictly separate acoustic recognition from semantic reasoning. 

The new flow is as follows:

`Raw Audio → Audio Normalization (FFmpeg: 16kHz, Mono WAV) → Faster-Whisper large-v3 → Clean Multilingual Transcript → Gemini Phase 2 Intelligence Analysis`

This separation of concerns ensures that transcription remains a deterministic mapping of audio to text, while Gemini is reserved strictly for Phase 2 semantic reasoning.

## 7. Why Faster-Whisper Was Chosen

Faster-Whisper (utilizing the `large-v3` model) was selected as the replacement engine for the following technical reasons:

- **Multilingual & Hinglish Support:** Native capability to accurately transcribe code-switched Hindi/English telephonic speech.
- **Stability:** Elimination of generative hallucination loops via zero-temperature decoding.
- **Timestamp Quality:** Accurate, deterministic segment chunking suitable for injecting structural `[MM:SS]` metadata.
- **GPU Acceleration:** Efficient CTranslate2 backend supporting CUDA `float16` compute types, drastically reducing inference latency.
- **Local Processing:** Ensures data privacy and avoids API rate limits during large batch processing.
- **Audio Robustness:** Proven capability to handle noisy, low-fidelity Indian telephonic audio accurately.

## 8. Engineering Principles Going Forward

To prevent architectural regressions, the following engineering principles must be adhered to in future development:

1. **LLMs are for Reasoning, not ASR:** Gemini or similar generative models must never be used for raw speech transcription.
2. **Deterministic Processing:** Transcription must remain a deterministic process. Generative completion or temperature-based sampling must be disabled (`temperature=0`).
3. **Fidelity Over Fluency:** The original spoken language, including pauses, stutters, and grammatical errors, must be preserved exactly as spoken.
4. **No Mid-Pipeline Translation:** No translation or aggressive normalization should occur during the transcription phase. Translation is a reasoning task reserved for later intelligence phases.
5. **Strict Modularity:** The ASR architecture must remain fully modular, ensuring it can be tested, swapped, and benchmarked independently of the LLM pipeline.

## 9. Final Production Goal

This architectural rebuild establishes the foundation required for a highly scalable AI sales intelligence engine. 

With deterministic, accurate transcripts guaranteed, the platform can safely proceed to its long-term objectives:
- Advanced multilingual call analytics.
- Accurate customer emotion and sentiment understanding.
- Real-time objection detection.
- Automated sales coaching and performance reviews.
- High-fidelity lead quality intelligence.
- Autonomous research and CRM synchronization workflows.