import json
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from app.config import settings
from app.schemas import VideoCandidate


class YouTubeService:
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    CACHE_PATH = Path("cache/youtube_search_cache.json")

    def __init__(self) -> None:
        self.api_key = settings.youtube_api_key
        self.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, List[dict]] = self._load_cache()

    def _make_cache_key(self, query: str, max_results: int) -> str:
        return f"{query.strip().lower()}|{max_results}"

    def _load_cache(self) -> Dict[str, List[dict]]:
        if not self.CACHE_PATH.exists():
            return {}

        try:
            with self.CACHE_PATH.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass

        return {}

    def _save_cache(self) -> None:
        with self.CACHE_PATH.open("w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=2)

    def _serialize_candidates(self, candidates: List[VideoCandidate]) -> List[dict]:
        return [candidate.model_dump() for candidate in candidates]

    def _deserialize_candidates(self, data: List[dict]) -> List[VideoCandidate]:
        return [VideoCandidate.model_validate(item) for item in data]

    def search_videos(self, query: str, max_results: Optional[int] = None) -> List[VideoCandidate]:
        max_results = max_results or settings.max_candidates_per_query
        cache_key = self._make_cache_key(query, max_results)

        if cache_key in self.cache:
            print(f"[YouTube cache hit] query='{query}' max_results={max_results}")
            return self._deserialize_candidates(self.cache[cache_key])

        print(f"[YouTube API request] query='{query}' max_results={max_results}")

        params = {
            "key": self.api_key,
            "part": "snippet",
            "q": query,
            "type": "video",
            "maxResults": max_results,
            "videoEmbeddable": "true",
        }

        with httpx.Client(timeout=20.0) as client:
            response = client.get(f"{self.BASE_URL}/search", params=params)

        if response.status_code >= 400:
            raise RuntimeError(f"{response.status_code} {response.text}")

        payload = response.json()

        results: List[VideoCandidate] = []
        for item in payload.get("items", []):
            video_id = item["id"]["videoId"]
            snippet = item.get("snippet", {})
            thumb = snippet.get("thumbnails", {}).get("high", {})

            results.append(
                VideoCandidate(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    channel_title=snippet.get("channelTitle", ""),
                    description=snippet.get("description", ""),
                    published_at=snippet.get("publishedAt"),
                    thumbnail_url=thumb.get("url"),
                    url=f"https://www.youtube.com/watch?v={video_id}",
                )
            )

        self.cache[cache_key] = self._serialize_candidates(results)
        self._save_cache()

        return results