import base64
import io
import json
from pathlib import Path
from typing import List, Optional, Tuple

from openai import OpenAI
from PIL import Image

from app.config import settings
from app.schemas import BaseTraits
from app.services.mock_traits_service import MockTraitsService

PROMPT_PATH = Path("app/prompts/extract_base_traits.txt")


class OpenAIService:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing.")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.prompt = PROMPT_PATH.read_text(encoding="utf-8")
        self.mock_helper = MockTraitsService()

    @staticmethod
    def _resize_image(file_bytes: bytes, mime_type: str) -> Tuple[bytes, str]:
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image = image.convert("RGB")

            max_dim = settings.max_image_dimension
            width, height = image.size
            longest_side = max(width, height)

            if longest_side > max_dim:
                scale = max_dim / float(longest_side)
                new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
                image = image.resize(new_size, Image.LANCZOS)

            output = io.BytesIO()
            image.save(output, format="JPEG", quality=80, optimize=True)
            return output.getvalue(), "image/jpeg"
        except Exception:
            return file_bytes, mime_type

    @staticmethod
    def _to_data_url(file_bytes: bytes, mime_type: str) -> str:
        encoded = base64.b64encode(file_bytes).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"

    def _merge_user_hints(
        self,
        ai_traits: BaseTraits,
        footprint: Optional[str],
        team_size: Optional[str],
        notes: Optional[str],
    ) -> BaseTraits:
        notes_text = (notes or "").strip()
        notes_lower = notes_text.lower()
        normalized_team_size = (team_size or "duo").strip().lower()

        # If the user supplied a footprint, trust it over the AI footprint guess.
        if footprint and footprint.strip():
            footprint_guess, footprint_tags, footprint_complexity = self.mock_helper._infer_footprint(
                footprint_text=footprint.strip(),
                notes_text=notes_text,
            )
            ai_traits.footprint_guess = footprint_guess
            ai_traits.footprint_tags = footprint_tags
            ai_traits.footprint_complexity = footprint_complexity

        # Merge in easy note-derived features if the AI missed them.
        merged_features = list(ai_traits.features)

        def add_feature(name: str) -> None:
            if name not in merged_features:
                merged_features.append(name)

        if "bunker" in notes_lower:
            add_feature("bunker")
        if "roof" in notes_lower and "bunker" in notes_lower:
            add_feature("roof_bunker")
        if "shooting floor" in notes_lower or "shooting" in notes_lower:
            add_feature("shooting_floor")
        if "wide gaps" in notes_lower or "widegap" in notes_lower or "wide" in notes_lower:
            add_feature("wide_gaps")
        if "peekdown" in notes_lower or "peek" in notes_lower:
            add_feature("peekdowns")
        if "open core" in notes_lower:
            add_feature("open_core")
        if "compound" in notes_lower:
            add_feature("compound")
        if "offset" in notes_lower:
            add_feature("offset")
        if "pixel gap" in notes_lower:
            add_feature("pixel_gap")

        ai_traits.features = merged_features

        # If AI returned no useful queries, or if the user supplied a footprint,
        # rebuild queries using the more reliable hybrid logic.
        if footprint and footprint.strip():
            ai_traits.generated_queries = self.mock_helper._build_queries(
                footprint_guess=ai_traits.footprint_guess or "unknown",
                footprint_tags=ai_traits.footprint_tags,
                team_size=normalized_team_size,
                notes_text=notes_text,
                features=ai_traits.features,
            )
        elif not ai_traits.generated_queries:
            ai_traits.generated_queries = self.mock_helper._build_queries(
                footprint_guess=ai_traits.footprint_guess or "unknown",
                footprint_tags=ai_traits.footprint_tags,
                team_size=normalized_team_size,
                notes_text=notes_text,
                features=ai_traits.features,
            )

        reasoning_parts = [ai_traits.reasoning_summary.strip()] if ai_traits.reasoning_summary else []

        if footprint and footprint.strip():
            reasoning_parts.append(
                f"User-provided footprint was prioritized as: {ai_traits.footprint_guess}."
            )

        if notes_text:
            reasoning_parts.append("User notes were merged into feature/query generation.")

        ai_traits.reasoning_summary = " ".join(part for part in reasoning_parts if part).strip()
        return ai_traits

    def extract_base_traits(
        self,
        files: List[Tuple[bytes, str]],
        footprint: Optional[str],
        team_size: Optional[str],
        notes: Optional[str],
    ) -> BaseTraits:
        limited_files = files[: settings.max_images_for_trait_extraction]

        input_content = [
            {
                "type": "input_text",
                "text": (
                    "Analyze these Rust base screenshots conservatively.\n\n"
                    f"Optional user hints:\n"
                    f"footprint={footprint or 'unknown'}\n"
                    f"team_size={team_size or 'unknown'}\n"
                    f"notes={notes or 'none'}\n\n"
                    "If the footprint is not visually obvious, return unknown for footprint fields.\n"
                    "Focus on easier visual traits like bunker, roof bunker, shooting floor, wide gaps, and honeycomb.\n"
                    "Return strict JSON only."
                ),
            }
        ]

        for original_bytes, mime_type in limited_files:
            resized_bytes, resized_mime = self._resize_image(original_bytes, mime_type)
            input_content.append(
                {
                    "type": "input_image",
                    "image_url": self._to_data_url(resized_bytes, resized_mime),
                }
            )

        response = self.client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": [{"type": "input_text", "text": self.prompt}],
                },
                {
                    "role": "user",
                    "content": input_content,
                },
            ],
        )

        text = response.output_text.strip()
        data = json.loads(text)
        ai_traits = BaseTraits.model_validate(data)

        return self._merge_user_hints(
            ai_traits=ai_traits,
            footprint=footprint,
            team_size=team_size,
            notes=notes,
        )