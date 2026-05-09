from __future__ import annotations

import time
from typing import Any

from config import QUERY_HISTORY_PATH, SESSION_MEMORY_PATH
from shared.json_utils import read_json, write_json


class SessionMemoryStore:
    def __init__(self) -> None:
        self._sessions = read_json(SESSION_MEMORY_PATH, default={}) or {}
        self._history = read_json(QUERY_HISTORY_PATH, default=[]) or []

    def load(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.get(session_id, {})
        return {
            "current_investigation_topic": session.get("current_investigation_topic", ""),
            "active_filters": session.get("active_filters", {}),
            "referenced_campaigns": session.get("referenced_campaigns", []),
            "referenced_counselors": session.get("referenced_counselors", []),
            "referenced_customer_segments": session.get("referenced_customer_segments", []),
            "previous_analytical_context": session.get("previous_analytical_context", []),
            "last_query": session.get("last_query", ""),
        }

    def update(
        self,
        session_id: str,
        query: str,
        filters: dict[str, Any],
        retrieved_results: list[dict[str, Any]],
        response_summary: str,
    ) -> dict[str, Any]:
        prior = self.load(session_id)
        campaigns = set(prior.get("referenced_campaigns", []))
        counselors = set(prior.get("referenced_counselors", []))
        customer_segments = set(prior.get("referenced_customer_segments", []))
        context = list(prior.get("previous_analytical_context", []))

        for result in retrieved_results:
            metadata = result.get("metadata", {})
            campaign = str(metadata.get("campaign", "")).strip()
            salesperson = str(metadata.get("salesperson", "")).strip()
            customer_id = str(metadata.get("customer_id", "")).strip()
            if campaign:
                campaigns.add(campaign)
            if salesperson:
                counselors.add(salesperson)
            if customer_id:
                customer_segments.add(customer_id)

        if response_summary:
            context.append(response_summary)
            context = context[-5:]

        session = {
            "current_investigation_topic": query,
            "active_filters": filters or prior.get("active_filters", {}),
            "referenced_campaigns": sorted(campaigns),
            "referenced_counselors": sorted(counselors),
            "referenced_customer_segments": sorted(customer_segments),
            "previous_analytical_context": context,
            "last_query": query,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._sessions[session_id] = session
        self._history.append(
            {
                "session_id": session_id,
                "query": query,
                "filters": filters,
                "updated_at": session["updated_at"],
            }
        )
        write_json(SESSION_MEMORY_PATH, self._sessions)
        write_json(QUERY_HISTORY_PATH, self._history)
        return session

