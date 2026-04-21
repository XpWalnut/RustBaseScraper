from collections import OrderedDict
from datetime import datetime, timezone
from typing import List

from app.schemas import BaseTraits, RankedMatch, VideoCandidate


def _normalize(text: str) -> str:
    return (text or "").lower().replace("-", " ").replace("_", " ")


PHRASE_BOOSTS = {
    "2x2 bunker": 0.20,
    "shooting floor": 0.18,
    "wide gaps": 0.18,
    "roof bunker": 0.22,
    "2x2 base tutorial": 0.08,
    "triangle bunker": 0.18,
    "offset bunker": 0.20,
    "hex base": 0.14,
    "hex bunker": 0.18,
    "circle base": 0.14,
}

SHORTS_TERMS = [
    "#shorts",
    " shorts ",
    "#rustshorts",
    "rustshorts",
    "#short",
    "#rusttok",
]

HASHTAG_HEAVY_TERMS = [
    "#rust",
    "#viral",
    "#rustpvp",
    "#rustconsole",
    "#rustduo",
    "#rustsolobase",
]

FEATURE_ALIASES = {
    "honeycomb": ["honeycomb"],
    "shooting_floor": ["shooting floor", "shootingfloor"],
    "wide_gaps": ["wide gaps", "widegaps"],
    "bunker": ["bunker", "roof bunker", "stability bunker"],
    "pixel_gap": ["pixel gap", "pixelgap"],
    "peekdowns": ["peekdown", "peekdowns", "peeks"],
    "open_core": ["open core"],
    "roof_bunker": ["roof bunker"],
    "compound": ["compound"],
    "offset": ["offset", "offset bunker"],
}

FOOTPRINT_TAG_ALIASES = {
    "1x2": ["1x2"],
    "2x1": ["2x1"],
    "2x2": ["2x2"],
    "3x3": ["3x3"],
    "square_core": ["square core"],
    "triangle_front": ["front triangle", "triangle front"],
    "triangle_side": ["side triangle", "triangle side", "triangle"],
    "triangle_double_side": ["double triangle", "double side triangles", "side triangles", "triangle shell"],
    "triangle_rear": ["rear triangle", "back triangle", "triangle rear"],
    "offset": ["offset", "offset bunker"],
    "hex": ["hex", "hexagon"],
    "circle": ["circle", "circular"],
    "shell": ["shell", "triangle shell"],
    "wing": ["wing", "triangle wing"],
}


def recency_bonus(published_at: str) -> float:
    if not published_at:
        return 0.0

    try:
        published_dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        age_days = (datetime.now(timezone.utc) - published_dt).days

        if age_days < 90:
            return 0.06
        if age_days < 365:
            return 0.04
        if age_days < 730:
            return 0.02
    except Exception:
        return 0.0

    return 0.0


class RankingService:
    def dedupe(self, candidates: List[VideoCandidate]) -> List[VideoCandidate]:
        unique = OrderedDict()
        for candidate in candidates:
            unique[candidate.video_id] = candidate
        return list(unique.values())

    def rank(self, traits: BaseTraits, candidates: List[VideoCandidate]) -> List[RankedMatch]:
        ranked: List[RankedMatch] = []

        for candidate in candidates:
            haystack = _normalize(
                f"{candidate.title} {candidate.description} {candidate.channel_title}"
            )
            reasons: List[str] = []
            score = 0.0

            if traits.footprint_guess and _normalize(traits.footprint_guess) in haystack:
                score += 0.22
                if len(reasons) < 5:
                    reasons.append(f"Mentions footprint: {traits.footprint_guess}")

            for tag in traits.footprint_tags:
                aliases = FOOTPRINT_TAG_ALIASES.get(tag, [_normalize(tag)])
                for alias in aliases:
                    if _normalize(alias) in haystack:
                        score += 0.12
                        if len(reasons) < 5:
                            reasons.append(f"Matches footprint tag: {alias}")
                        break

            for feature in traits.features:
                aliases = FEATURE_ALIASES.get(feature, [_normalize(feature)])
                for alias in aliases:
                    if _normalize(alias) in haystack:
                        score += 0.15
                        if len(reasons) < 5:
                            reasons.append(f"Matches feature: {alias}")
                        break

            for roof in traits.roof_shapes:
                if _normalize(roof) in haystack:
                    score += 0.08
                    if len(reasons) < 5:
                        reasons.append(f"Matches roof/style term: {roof}")

            title_lower = _normalize(candidate.title)

            if "tutorial" in title_lower:
                score += 0.05
            if "rust" in title_lower:
                score += 0.03

            if traits.footprint_guess and _normalize(traits.footprint_guess) in title_lower:
                score += 0.08

            for tag in traits.footprint_tags:
                aliases = FOOTPRINT_TAG_ALIASES.get(tag, [_normalize(tag)])
                for alias in aliases:
                    if _normalize(alias) in title_lower:
                        score += 0.06
                        break

            for phrase, boost in PHRASE_BOOSTS.items():
                if phrase in haystack:
                    score += boost
                    if len(reasons) < 5:
                        reasons.append(f"Phrase match: {phrase}")

            shorts_penalty = 0.0
            haystack_padded = f" {haystack} "

            for term in SHORTS_TERMS:
                if term in haystack_padded:
                    shorts_penalty -= 0.25
                    break

            hashtag_count = sum(1 for term in HASHTAG_HEAVY_TERMS if term in haystack)
            if hashtag_count >= 2:
                shorts_penalty -= 0.10

            if shorts_penalty != 0.0:
                score += shorts_penalty
                if len(reasons) < 5:
                    reasons.append(f"Penalty: shorts/hashtag content {shorts_penalty:.2f}")

            bonus = recency_bonus(candidate.published_at or "")
            score += bonus
            if bonus > 0 and len(reasons) < 5:
                reasons.append(f"Recent upload bonus: +{bonus:.2f}")

            ranked.append(
                RankedMatch(
                    **candidate.model_dump(),
                    score=round(score, 4),
                    reasons=reasons[:5],
                )
            )

        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:10]