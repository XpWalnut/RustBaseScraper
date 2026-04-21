from typing import List, Optional, Tuple

from app.schemas import BaseTraits


class MockTraitsService:
    FEATURE_OPTIONS = [
        "bunker",
        "roof_bunker",
        "shooting_floor",
        "wide_gaps",
        "peekdowns",
        "open_core",
        "offset",
        "pixel_gap",
        "shell",
        "high_external_walls",
        "disconnectable_tcs",
        "china_wall",
        "multi_tc",
        "wide_peeks",
        "jump_ups",
        "furnace_base",
    ]

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
            footprint_guess = "offset core"
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
                footprint_guess = "offset core"
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
        if "wing" in tags:
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

    def _infer_features_from_notes(self, notes_text: str) -> List[str]:
        notes_lower = (notes_text or "").lower()
        features: List[str] = []

        if "bunker" in notes_lower:
            self._add_tag(features, "bunker")
        if "roof bunker" in notes_lower or ("roof" in notes_lower and "bunker" in notes_lower):
            self._add_tag(features, "roof_bunker")
        if "shooting floor" in notes_lower or "shootingfloor" in notes_lower:
            self._add_tag(features, "shooting_floor")
        if "wide gaps" in notes_lower or "widegap" in notes_lower:
            self._add_tag(features, "wide_gaps")
        if "peekdown" in notes_lower or "peekdowns" in notes_lower:
            self._add_tag(features, "peekdowns")
        if "open core" in notes_lower:
            self._add_tag(features, "open_core")
        if "offset" in notes_lower:
            self._add_tag(features, "offset")
        if "pixel gap" in notes_lower:
            self._add_tag(features, "pixel_gap")
        if "shell" in notes_lower:
            self._add_tag(features, "shell")
        if "high external wood walls" in notes_lower or "external wood walls" in notes_lower:
            self._add_tag(features, "high_external_walls")
        if "disconnectable tc" in notes_lower or "disconnectable tcs" in notes_lower:
            self._add_tag(features, "disconnectable_tcs")
        if "china wall" in notes_lower:
            self._add_tag(features, "china_wall")
        if "multi tc" in notes_lower or "multi-tc" in notes_lower:
            self._add_tag(features, "multi_tc")
        if "wide peeks" in notes_lower or "wide peek" in notes_lower:
            self._add_tag(features, "wide_peeks")
        if "jump up" in notes_lower or "jump-ups" in notes_lower or "jump ups" in notes_lower:
            self._add_tag(features, "jump_ups")
        if "furnace base" in notes_lower:
            self._add_tag(features, "furnace_base")

        return features

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
        has_bunker = "bunker" in features
        has_roof_bunker = "roof_bunker" in features
        has_shooting_floor = "shooting_floor" in features
        has_wide_gaps = "wide_gaps" in features
        has_peekdowns = "peekdowns" in features
        has_open_core = "open_core" in features
        has_offset = "offset" in features or "offset" in footprint_tags
        has_pixel_gap = "pixel_gap" in features
        has_shell = "shell" in features or "shell" in footprint_tags
        has_high_external_walls = "high_external_walls" in features
        has_disconnectable_tcs = "disconnectable_tcs" in features
        has_china_wall = "china_wall" in features
        has_multi_tc = "multi_tc" in features
        has_wide_peeks = "wide_peeks" in features
        has_jump_ups = "jump_ups" in features
        has_furnace_base = "furnace_base" in features

        has_triangle = any(
            tag in footprint_tags
            for tag in ["triangle_front", "triangle_side", "triangle_double_side", "triangle_rear", "wing"]
        )
        has_hex = "hex" in footprint_tags
        has_circle = "circle" in footprint_tags

        normalized_footprint = (footprint_guess or "unknown").replace(" with ", " ").replace(",", " ").strip()
        footprint_known = normalized_footprint and normalized_footprint != "unknown"

        if notes_clean and len(notes_clean.split()) <= 4:
            queries.append(f"rust {notes_clean} base tutorial")

        # Neutral foundation searches first.
        if footprint_known:
            queries.append(f"rust {normalized_footprint} base tutorial")
            queries.append(f"rust {team_size} {normalized_footprint} base tutorial")
        else:
            queries.append(f"rust {team_size} rust base tutorial")
            queries.append("rust base tutorial")

        # Footprint-specific neutral searches.
        if has_triangle:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} triangle base tutorial")
            queries.append("rust triangle base tutorial")

        if has_hex:
            queries.append("rust hex base tutorial")

        if has_circle:
            queries.append("rust circle base tutorial")

        if has_offset:
            queries.append("rust offset base tutorial")

        # Core structure queries.
        if has_bunker:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} bunker base tutorial")
            queries.append(f"rust {team_size} bunker base tutorial")

        if has_roof_bunker:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} roof bunker tutorial")
            queries.append("rust roof bunker base tutorial")

        if has_shooting_floor:
            if has_bunker:
                if footprint_known:
                    queries.append(f"rust {normalized_footprint} bunker shooting floor tutorial")
                queries.append("rust bunker shooting floor tutorial")
            else:
                if footprint_known:
                    queries.append(f"rust {normalized_footprint} shooting floor base tutorial")
                queries.append("rust shooting floor base tutorial")

        if has_wide_gaps:
            if has_bunker:
                if footprint_known:
                    queries.append(f"rust {normalized_footprint} wide gaps bunker tutorial")
                queries.append("rust wide gaps bunker tutorial")
            else:
                if footprint_known:
                    queries.append(f"rust {normalized_footprint} wide gaps base tutorial")
                queries.append("rust wide gaps base tutorial")

        if has_peekdowns:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} peekdowns tutorial")
            queries.append("rust peekdowns base tutorial")

        if has_open_core:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} open core base tutorial")
            queries.append("rust open core base tutorial")

        if has_pixel_gap:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} pixel gap tutorial")
            queries.append("rust pixel gap base tutorial")

        if has_shell:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} shell base tutorial")
            queries.append("rust shell base tutorial")

        # Outer defense / externals.
        if has_high_external_walls:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} high external wood walls tutorial")
            queries.append("rust high external wood walls base tutorial")

        if has_disconnectable_tcs:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} disconnectable tcs tutorial")
            queries.append("rust disconnectable tcs base tutorial")

        if has_china_wall:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} china wall tutorial")
            queries.append("rust china wall base tutorial")

        if has_multi_tc:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} multi tc base tutorial")
            queries.append("rust multi tc base tutorial")

        if has_wide_peeks:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} wide peeks tutorial")
            queries.append("rust wide peeks base tutorial")

        if has_jump_ups:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} jump up tutorial")
            queries.append("rust jump up base tutorial")

        if has_furnace_base:
            if footprint_known:
                queries.append(f"rust {normalized_footprint} furnace base tutorial")
            queries.append("rust furnace base tutorial")

        seen = set()
        deduped_queries: List[str] = []
        for query in queries:
            cleaned = " ".join(query.lower().split())
            if cleaned not in seen:
                seen.add(cleaned)
                deduped_queries.append(query)

        return deduped_queries[:8]

    def build_traits_from_overrides(
        self,
        footprint: Optional[str],
        team_size: Optional[str],
        notes: Optional[str],
        selected_features: Optional[List[str]] = None,
        floors_visible: Optional[int] = None,
        roof_shapes: Optional[List[str]] = None,
        confidence: float = 0.25,
        reasoning_summary: Optional[str] = None,
    ) -> BaseTraits:
        footprint_text = (footprint or "").strip()
        team_size_text = (team_size or "duo").strip().lower()
        notes_text = (notes or "").strip()

        if selected_features is None:
            features = self._infer_features_from_notes(notes_text)
        else:
            features = [feature for feature in selected_features if feature in self.FEATURE_OPTIONS]

        footprint_guess, footprint_tags, footprint_complexity = self._infer_footprint(
            footprint_text=footprint_text,
            notes_text=notes_text,
        )

        final_roof_shapes = list(roof_shapes or [])
        if "roof_bunker" in features and "peaked" not in final_roof_shapes:
            final_roof_shapes.append("peaked")

        generated_queries = self._build_queries(
            footprint_guess=footprint_guess,
            footprint_tags=footprint_tags,
            team_size=team_size_text,
            notes_text=notes_text,
            features=features,
        )

        if not reasoning_summary:
            reasoning_bits = []
            if footprint_text:
                reasoning_bits.append(f"Footprint input was interpreted as: {footprint_guess}.")
            if features:
                reasoning_bits.append(f"Selected features: {', '.join(features)}.")
            reasoning_summary = " ".join(reasoning_bits).strip() or "Traits were built from user inputs."

        return BaseTraits(
            footprint_guess=footprint_guess,
            footprint_tags=footprint_tags,
            footprint_complexity=footprint_complexity,
            floors_visible=floors_visible,
            roof_shapes=final_roof_shapes,
            features=features,
            stage="midgame",
            confidence=confidence,
            generated_queries=generated_queries,
            reasoning_summary=reasoning_summary,
        )

    def extract_base_traits(
        self,
        files: List[Tuple[bytes, str]],
        footprint: Optional[str],
        team_size: Optional[str],
        notes: Optional[str],
    ) -> BaseTraits:
        reasoning = (
            "Mock mode is enabled, so these traits were generated from your form inputs "
            "instead of image analysis."
        )

        return self.build_traits_from_overrides(
            footprint=footprint,
            team_size=team_size,
            notes=notes,
            selected_features=None,
            floors_visible=3,
            roof_shapes=[],
            confidence=0.25,
            reasoning_summary=reasoning,
        )