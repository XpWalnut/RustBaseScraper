import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.schemas import SearchResponse


class EvaluationService:
    EVAL_PATH = Path("cache/search_evaluations.jsonl")

    def __init__(self) -> None:
        self.EVAL_PATH.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def extract_video_id(youtube_url: str) -> Optional[str]:
        if not youtube_url:
            return None

        text = youtube_url.strip()

        if "watch?v=" in text:
            return text.split("watch?v=", 1)[1].split("&", 1)[0].strip()

        if "youtu.be/" in text:
            return text.split("youtu.be/", 1)[1].split("?", 1)[0].strip()

        if len(text) == 11 and "/" not in text and " " not in text:
            return text

        return None

    @staticmethod
    def find_expected_rank(matches: List[Dict[str, Any]], expected_video_id: str) -> Optional[int]:
        for index, match in enumerate(matches, start=1):
            if match.get("video_id") == expected_video_id:
                return index
        return None

    def save_evaluation(
        self,
        result: SearchResponse,
        expected_video_url: str,
        actual_footprint: Optional[str],
        actual_features: Optional[List[str]],
        closeness_note: Optional[str],
        user_notes: Optional[str],
    ) -> Dict[str, Any]:
        expected_video_id = self.extract_video_id(expected_video_url or "")
        match_dicts = [match.model_dump() for match in result.matches]
        expected_rank = (
            self.find_expected_rank(match_dicts, expected_video_id)
            if expected_video_id
            else None
        )

        record = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "expected_video_url": expected_video_url,
            "expected_video_id": expected_video_id,
            "expected_rank_in_results": expected_rank,
            "found_in_top_results": expected_rank is not None,
            "actual_footprint": actual_footprint,
            "actual_features": actual_features or [],
            "closeness_note": closeness_note,
            "user_notes": user_notes,
            "extracted_traits": result.extracted_traits.model_dump(),
            "matches": match_dicts,
        }

        with self.EVAL_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record