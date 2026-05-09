from __future__ import annotations

import re
from typing import Any

# Initial list of counselor names, can be updated at runtime from metadata
COUNSELOR_NAMES = ["Shraddha", "Shuman", "Shraddha Bhaskar"]

class IntentClassifier:
    """
    Classifies user questions into strategic intents for better retrieval and reasoning.
    """
    def __init__(self, counselor_names: list[str] | None = None) -> None:
        self.counselor_names = counselor_names or COUNSELOR_NAMES
        
        # Trigger patterns
        self.greetings = [r"\bhi\b", r"\bhello\b", r"\bhey\b", r"good morning", r"how are you"]
        self.trends = [r"\bwhy\b", r"what is happening", r"\bpattern\b", r"\btrend\b", r"\brecently\b", 
                      r"\bdropping\b", r"\bincreasing\b", r"most common", r"\brecurring\b"]
        self.rankings = [r"\bbest\b", r"\bworst\b", r"\btop\b", r"\bbottom\b", r"\bhighest\b", 
                        r"\blowest\b", r"who performs", r"\bcompare\b", r"\bversus\b", r"\bvs\b"]
        self.retrievals = [r"show me", r"\bfind\b", r"\blist\b", r"give me", r"which calls"]
        
        # Regex for entity extraction
        self.entity_extractors = [
            r"who is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"tell me about ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            r"show me ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'s calls",
            r"how is ([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?) performing"
        ]

    def classify(self, question: str) -> dict[str, Any]:
        """
        Classifies a question and extracts entities/filters.
        Detection order: Greeting -> Entity -> Trend -> Ranking -> Retrieval -> Casual
        """
        # 1. Check for greetings
        for pattern in self.greetings:
            if re.search(pattern, question, re.IGNORECASE):
                return {"type": "greeting", "entity": "", "filters": {}}
        
        # 2. Check for entity analysis (counselor, campaign, etc.)
        # Pattern-based extraction
        for pattern in self.entity_extractors:
            match = re.search(pattern, question, re.IGNORECASE)
            if match:
                entity = match.group(1).strip()
                return {
                    "type": "entity_analysis",
                    "entity": entity,
                    "filters": self._build_entity_filters(entity)
                }
        
        # Direct counselor name matching
        for name in self.counselor_names:
            if re.search(rf"\b{re.escape(name)}\b", question, re.IGNORECASE):
                return {
                    "type": "entity_analysis",
                    "entity": name,
                    "filters": {"salesperson": name}
                }

        # 3. Check for trend analysis
        for pattern in self.trends:
            if re.search(pattern, question, re.IGNORECASE):
                return {"type": "trend_analysis", "entity": "", "filters": {}}

        # 4. Check for ranking/comparison
        for pattern in self.rankings:
            if re.search(pattern, question, re.IGNORECASE):
                return {"type": "ranking", "entity": "", "filters": {}}

        # 5. Check for direct retrieval
        for pattern in self.retrievals:
            if re.search(pattern, question, re.IGNORECASE):
                return {"type": "retrieval", "entity": "", "filters": {}}

        # 6. Default to casual
        return {"type": "casual", "entity": "", "filters": {}}

    def _build_entity_filters(self, entity: str) -> dict[str, Any]:
        """Maps an extracted entity to the appropriate metadata filter."""
        entity_lower = entity.lower()
        # If it's a known counselor, filter by salesperson
        if any(c.lower() == entity_lower for c in self.counselor_names):
            return {"salesperson": entity}
        
        # Otherwise, use a generic entity filter (supported by some retrieval engines)
        return {"entity": entity}
