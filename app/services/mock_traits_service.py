from typing import List, Optional, Tuple

from app.schemas import BaseTraits


class MockTraitsService:
    def _add_tag(self, tags: List[str], tag: str) -> None:
        if tag not in tags:
            tags.append(tag)

    def _infer_footprint(
        self,
        footprint_text: str,
        notes_text: str,
    ) -> Tuple[str, List[str], str]:
        combined = f"{footprint_text} {notes_text}".strip().lower()

        tags: List[str] = []
        footprint_guess = "unknown"
        complexity = "unknown"

        has_1x2 = "1x2" in combined
        has_2x1 = "2x1" in combined
        has_2x2 = "2x2" in combined
        has_3x3 = "3x3" in combined
        has_square = "square" in combined
        has_hex = "hex" in combined or "hexagon" in combined
        has_circle = "circle" in combined or "circular" in combined
        has_offset = "offset" in combined

        has_triangle = "triangle" in combined or "triangles" in combined
        has_front_triangle = (
            "front triangle" in combined
            or "triangle front" in combined
            or "triangle on one side" in combined
        )
        has_side_triangle = (
            "side triangle" in combined
            or "triangle side" in combined
            or "side triangles" in combined
        )
        has_double_triangle = (
            "double triangle" in combined
            or "two triangles" in combined
            or "2 triangles" in combined
            or "double side triangle" in combined
            or "double triangle side" in combined
        )
        has_rear_triangle = (
            "rear triangle" in combined
            or "back triangle" in combined
            or "triangle rear" in combined
        )
        has_wing = "wing" in combined or "triangle wing" in combined
        has_shell = "shell" in combined

        if has_1x2:
            footprint_guess = "1x2"
            complexity = "simple"
            self._add_tag(tags, "1x2")

        elif has_2x1:
            footprint_guess = "2x1"
            complexity = "simple"
            self._add_tag(tags, "2x1")

        elif has_2x2:
            footprint_guess = "2x2"
            complexity = "simple"
            self._add_tag(tags, "2x2")

        elif has_3x3:
            footprint_guess = "3x3"
            complexity = "medium"
            self._add_tag(tags, "3x3")

        elif has_hex:
            footprint_guess = "hex core"
            complexity = "medium"
            self._add_tag(tags, "hex")

        elif has_circle:
            footprint_guess = "circle core"
            complexity = "medium"
            self._add_tag(tags, "circle")

        elif has_offset:
            footprint_guess = "offset bunker core"
            complexity = "medium"
            self._add_tag(tags, "offset")

        elif has_square:
            footprint_guess = "square core"
            complexity = "simple"
            self._add_tag(tags, "square_core")

        if has_square and "square_core" not in tags:
            self._add_tag(tags, "square_core")

        if has_offset and "offset" not in tags:
            self._add_tag(tags, "offset")
            if footprint_guess == "unknown":
                footprint_guess = "offset bunker core"
                complexity = "medium"

        if has_shell:
            self._add_tag(tags, "shell")
            if complexity in ("unknown", "simple"):
                complexity = "medium"

        if has_wing:
            self._add_tag(tags, "wing")
            if complexity in ("unknown", "simple"):
                complexity = "medium"

        if has_front_triangle:
            self._add_tag(tags, "triangle_front")

        if has_side_triangle or has_triangle:
            self._add_tag(tags, "triangle_side")

        if has_double_triangle:
            self._add_tag(tags, "triangle_double_side")

        if has_rear_triangle:
            self._add_tag(tags, "triangle_rear")

        triangle_parts: List[str] = []
        if "triangle_front" in tags:
            triangle_parts.append("front triangle")
        if "triangle_side" in tags and "triangle_double_side" not in tags:
            triangle_parts.append("side triangle")
        if "triangle_double_side" in tags:
            triangle_parts.append("double side triangles")
        if "triangle_rear" in tags:
            triangle_parts.append("rear triangle")
        if "wing" in tags and "triangle wing" not in triangle_parts:
            triangle_parts.append("triangle wing")

        if triangle_parts:
            if "2x2" in tags:
                footprint_guess = "2x2 with " + " and ".join(triangle_parts)
                complexity = "medium" if len(triangle_parts) == 1 else "complex"
            elif "square_core" in tags:
                footprint_guess = "square core with " + " and ".join(triangle_parts)
                complexity = "medium" if len(triangle_parts) == 1 else "complex"
            elif footprint_guess == "unknown":
                footprint_guess = "triangle-based core"
                complexity = "medium"

        if has_hex and triangle_parts:
            footprint_guess = "hex core with " + " and ".join(triangle_parts)
            complexity = "complex"

        if has_circle and triangle_parts:
            footprint_guess = "circle core with " + " and ".join(triangle_parts)
            complexity = "complex"

        if not tags and footprint_text.strip():
            if footprint_text.strip().lower() == "unknown":
                footprint_guess = "unknown"
                complexity = "unknown"
            else:
                footprint_guess = footprint_text.strip().lower()
                complexity = "medium"

        return footprint_guess, tags[:5], complexity

    def _build_queries(
        self,
        footprint_guess: str,
        footprint_tags: List[str],
        team_size: str,
        notes_text: str,
        features: List[str],
    ) -> List[str]:
        queries: List[str] = []

        notes_clean = notes_text.strip()
        if notes_clean:
            queries.append(f"rust {notes_clean} base tutorial")

        has_triangle = any(
            tag in footprint_tags
            for tag in ["triangle_front", "triangle_side", "triangle_double_side", "triangle_rear", "wing"]
        )
        has_offset = "offset" in footprint_tags
        has_hex = "hex" in footprint_tags
        has_circle = "circle" in footprint_tags
        has_2x2 = "2x2" in footprint_tags
        has_bunker = "bunker" in features
        has_shooting_floor = "shooting_floor" in features
        has_wide_gaps = "wide_gaps" in features
        has_roof_bunker = "roof_bunker" in features

        if has_2x2 and has_triangle and has_bunker:
            queries.append("rust 2x2 triangle bunker tutorial")
            queries.append(f"rust {team_size} 2x2 triangle bunker base tutorial")
        elif has_2x2 and has_triangle:
            queries.append("rust 2x2 triangle base tutorial")

        if has_offset:
            queries.append("rust offset bunker base tutorial")
            queries.append(f"rust {team_size} offset bunker tutorial")

        if has_hex:
            queries.append("rust hex bunker base tutorial")
            queries.append(f"rust {team_size} hex base tutorial")

        if has_circle:
            queries.append("rust circle bunker base tutorial")
            queries.append(f"rust {team_size} circle base tutorial")

        if has_2x2 and has_bunker and has_shooting_floor:
            queries.append("rust 2x2 bunker shooting floor tutorial")

        if has_2x2 and has_bunker and has_wide_gaps:
            queries.append("rust 2x2 wide gaps bunker tutorial")

        if has_2x2 and has_roof_bunker:
            queries.append("rust 2x2 roof bunker tutorial")

        if has_bunker and has_shooting_floor:
            queries.append("rust bunker shooting floor tutorial")

        if has_bunker and has_wide_gaps:
            queries.append("rust wide gaps bunker tutorial")

        if has_roof_bunker:
            queries.append("rust roof bunker base tutorial")

        if has_bunker:
            queries.append(f"rust {team_size} bunker base tutorial")

        normalized_footprint_for_query = footprint_guess.replace(" with ", " ").replace(",", " ").strip()

        if footprint_guess != "unknown":
            queries.append(f"rust {normalized_footprint_for_query} bunker base tutorial")
            queries.append(f"rust {normalized_footprint_for_query} base tutorial")

        queries.append("rust bunker base tutorial")

        seen = set()
        deduped_queries: List[str] = []
        for query in queries:
            cleaned = " ".join(query.lower().split())
            if cleaned not in seen:
                seen.add(cleaned)
                deduped_queries.append(query)

        return deduped_queries[:8]

    def extract_base_traits(
        self,
        files: List[Tuple[bytes, str]],
        footprint: Optional[str],
        team_size: Optional[str],
        notes: Optional[str],
    ) -> BaseTraits:
        normalized_team_size = (team_size or "duo").strip().lower()
        footprint_text = (footprint or "").strip()
        notes_text = (notes or "").strip()
        notes_lower = notes_text.lower()

        features = ["honeycomb"]

        if "shooting" in notes_lower or "shooting floor" in notes_lower:
            self._add_tag(features, "shooting_floor")
        if "wide" in notes_lower or "wide gaps" in notes_lower or "widegap" in notes_lower:
            self._add_tag(features, "wide_gaps")
        if "bunker" in notes_lower:
            self._add_tag(features, "bunker")
        if "peek" in notes_lower or "peekdown" in notes_lower:
            self._add_tag(features, "peekdowns")
        if "roof" in notes_lower and "bunker" in notes_lower:
            self._add_tag(features, "roof_bunker")
        if "offset" in notes_lower:
            self._add_tag(features, "offset")
        if "open core" in notes_lower:
            self._add_tag(features, "open_core")
        if "compound" in notes_lower:
            self._add_tag(features, "compound")
        if "pixel gap" in notes_lower:
            self._add_tag(features, "pixel_gap")

        footprint_guess, footprint_tags, footprint_complexity = self._infer_footprint(
            footprint_text=footprint_text,
            notes_text=notes_text,
        )

        roof_shapes: List[str] = []
        if "peaked" in notes_lower or "peak" in notes_lower:
            roof_shapes.append("peaked")

        if not roof_shapes and "roof_bunker" in features:
            roof_shapes.append("peaked")

        generated_queries = self._build_queries(
            footprint_guess=footprint_guess,
            footprint_tags=footprint_tags,
            team_size=normalized_team_size,
            notes_text=notes_text,
            features=features,
        )

        reasoning_bits = [
            "Mock mode is enabled, so these traits were generated from your form inputs instead of image analysis."
        ]

        if footprint_text:
            reasoning_bits.append(f"Footprint input was interpreted as: {footprint_guess}.")
        if footprint_tags:
            reasoning_bits.append(f"Footprint tags: {', '.join(footprint_tags)}.")

        return BaseTraits(
            footprint_guess=footprint_guess,
            footprint_tags=footprint_tags,
            footprint_complexity=footprint_complexity,
            floors_visible=3,
            roof_shapes=roof_shapes,
            features=features,
            stage="midgame",
            confidence=0.25,
            generated_queries=generated_queries,
            reasoning_summary=" ".join(reasoning_bits),
        )