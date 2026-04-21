import base64
import io
import json
from pathlib import Path
from typing import List, Optional, Tuple

from openai import OpenAI
from PIL import Image

from app.config import settings
from app.schemas import BaseTraits

PROMPT_PATH = Path("app/prompts/extract_base_traits.txt")


class OpenAIService:
    def __init__(self) -> None:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is missing.")
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.prompt = PROMPT_PATH.read_text(encoding="utf-8")

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
        return BaseTraits.model_validate(data)