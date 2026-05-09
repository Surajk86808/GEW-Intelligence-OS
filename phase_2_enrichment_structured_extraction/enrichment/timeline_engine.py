from __future__ import annotations

from typing import Any


class TimelineEngine:
    def build(self, emotion_timeline: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not emotion_timeline:
            return []

        merged: list[dict[str, Any]] = [dict(emotion_timeline[0])]
        for item in emotion_timeline[1:]:
            previous = merged[-1]
            if item["emotion"] == previous["emotion"]:
                previous["end"] = item["end"]
                previous["confidence"] = round((float(previous["confidence"]) + float(item["confidence"])) / 2.0, 2)
            else:
                merged.append(dict(item))
        return merged

