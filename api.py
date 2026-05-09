from __future__ import annotations

import sys
import os
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from shared.llm_client import LLMClient, get_llm_client
from shared.settings import QUERY_MODEL, GEMINI_API_KEY
from contextlib import asynccontextmanager

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

from shared.json_utils import read_json
from phase_5_query_intelligence.decision_engine.retrieval_engine import RetrievalEngine
from phase_5_query_intelligence.intent_classifier import IntentClassifier
from phase_5_query_intelligence.prompt_builder import PromptBuilder
from phase_5_query_intelligence.synthesis_engine import SynthesisEngine

# Global instances
retrieval_engine: RetrievalEngine = None # type: ignore
classifier: IntentClassifier = None # type: ignore
prompt_builder: PromptBuilder = None # type: ignore
synthesizer: SynthesisEngine = None # type: ignore

@asynccontextmanager
async def lifespan(app: FastAPI):
    global retrieval_engine, classifier, prompt_builder, synthesizer
    
    # Initialize Gemini Client
    get_llm_client()
    
    vector_index_path = PROJECT_ROOT / "phase_4_knowledge_memory" / "memory" / "vector_store" / "vector_index.json"
    evidence_lookup_path = PROJECT_ROOT / "phase_4_knowledge_memory" / "memory" / "outputs" / "debug" / "evidence_lookup.json"
    
    vector_index = read_json(vector_index_path, default=[])
    evidence_lookup = read_json(evidence_lookup_path, default={})
    
    retrieval_engine = RetrievalEngine(vector_index, evidence_lookup)
    classifier = IntentClassifier()
    prompt_builder = PromptBuilder()
    synthesizer = SynthesisEngine()
    
    yield

app = FastAPI(title="GEW Intelligence OS API", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class AskRequest(BaseModel):
    question: str

@app.get("/health")
async def health():
    return {"status": "ok"}

def call_gemini(system_prompt: str, user_prompt: str) -> str:
    try:
        return LLMClient.generate_content(
            model=QUERY_MODEL,
            prompt=user_prompt,
            system_instruction=system_prompt
        )
    except Exception as e:
        return f"Error calling Gemini: {str(e)}"

@app.post("/ask")
async def ask(request: AskRequest):
    try:
        question = request.question
        
        # 1. Intent Classification
        intent = classifier.classify(question)
        
        # 2. Early return for greetings
        if intent["type"] == "greeting":
            system_prompt, user_prompt = prompt_builder.build(intent, question, [], {})
            raw_answer = call_gemini(system_prompt, user_prompt)
            return {
                "answer": raw_answer,
                "insight": "GEW Call Intelligence is ready.",
                "confidence": 1.0,
                "calls_referenced": [],
                "follow_up_suggestions": synthesizer._get_suggestions(intent),
                "intent": intent["type"]
            }
        
        # 3. Retrieval with filters
        results = retrieval_engine.retrieve(question, filters=intent.get("filters", {}))
        
        # 4. Build analytics
        matched_call_ids = set(r["metadata"].get("call_id", "") for r in results if r["metadata"].get("call_id"))
        analytics = {
            "matched_calls": len(matched_call_ids),
            "top_emotions": [],
            "top_salespeople": []
        }
        
        # 5. Format evidence
        evidence = [
            {
                "call_id": r["metadata"].get("call_id", ""),
                "timestamp": r["metadata"].get("start_time", ""),
                "quote": r["metadata"].get("text", ""),
                "counselor_name": r["metadata"].get("salesperson", ""), # Mapping salesperson to counselor_name
                "emotion": r["metadata"].get("dominant_emotion", "neutral"),
                "score": r["score"]
            }
            for r in results[:8]
        ]
        
        # 6. Build prompts
        system_prompt, user_prompt = prompt_builder.build(intent, question, evidence, analytics)
        
        # 7. Call Gemini
        raw_answer = call_gemini(system_prompt, user_prompt)
        
        # 8. Synthesize final result
        result = synthesizer.synthesize(question, intent, evidence, raw_answer)
        result["intent"] = intent["type"]
        
        return result
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
