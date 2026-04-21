import json
from html import escape
from typing import Annotated, List, Optional, Tuple

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from app.config import settings
from app.schemas import SearchResponse
from app.services.mock_traits_service import MockTraitsService
from app.services.openai_service import OpenAIService
from app.services.ranking_service import RankingService
from app.services.youtube_service import YouTubeService

router = APIRouter()

traits_service = MockTraitsService() if settings.use_mock_traits else OpenAIService()
youtube_service = YouTubeService()
ranking_service = RankingService()


@router.post("/search", response_model=SearchResponse)
async def search_base_tutorials(
    screenshots: Annotated[List[UploadFile], File(...)],
    footprint: Annotated[Optional[str], Form()] = None,
    team_size: Annotated[Optional[str], Form()] = None,
    notes: Annotated[Optional[str], Form()] = None,
) -> SearchResponse:
    if not screenshots:
        raise HTTPException(status_code=400, detail="At least one screenshot is required.")

    print("\n=== New /api/search request ===")
    print(f"screenshots_received={len(screenshots)}")
    print(f"footprint={footprint}")
    print(f"team_size={team_size}")
    print(f"notes={notes}")
    print(f"use_mock_traits={settings.use_mock_traits}")
    print(f"openai_model={settings.openai_model}")
    print(f"max_images_for_trait_extraction={settings.max_images_for_trait_extraction}")

    file_payloads: List[Tuple[bytes, str]] = []
    for shot in screenshots[:6]:
        content = await shot.read()
        mime_type = shot.content_type or "image/png"
        file_payloads.append((content, mime_type))

    try:
        traits = traits_service.extract_base_traits(
            files=file_payloads,
            footprint=footprint,
            team_size=team_size,
            notes=notes,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Trait extraction failed: {e}")

    print(f"footprint_guess={traits.footprint_guess}")
    print(f"footprint_tags={traits.footprint_tags}")
    print(f"footprint_complexity={traits.footprint_complexity}")

    print("generated_queries:")
    for index, query in enumerate(traits.generated_queries[: settings.max_search_queries], start=1):
        print(f"  {index}. {query}")

    all_candidates = []
    try:
        for query in traits.generated_queries[: settings.max_search_queries]:
            query_candidates = youtube_service.search_videos(query=query)
            print(f"query='{query}' returned {len(query_candidates)} candidates")
            all_candidates.extend(query_candidates)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"YouTube search failed: {e}")

    print(f"total_candidates_before_dedupe={len(all_candidates)}")
    deduped = ranking_service.dedupe(all_candidates)
    print(f"total_candidates_after_dedupe={len(deduped)}")

    ranked = ranking_service.rank(traits=traits, candidates=deduped)
    print(f"ranked_results_returned={len(ranked)}")

    if ranked:
        print("top_3_results:")
        for index, match in enumerate(ranked[:3], start=1):
            print(f"  {index}. score={match.score} title={match.title}")

    return SearchResponse(extracted_traits=traits, matches=ranked)


@router.post("/results", response_class=HTMLResponse)
async def search_results_page(
    screenshots: Annotated[List[UploadFile], File(...)],
    footprint: Annotated[Optional[str], Form()] = None,
    team_size: Annotated[Optional[str], Form()] = None,
    notes: Annotated[Optional[str], Form()] = None,
) -> HTMLResponse:
    result = await search_base_tutorials(
        screenshots=screenshots,
        footprint=footprint,
        team_size=team_size,
        notes=notes,
    )

    def badge_for_index(index: int) -> str:
        if index == 0:
            return '<span class="badge badge-gold">Best Match</span>'
        if index == 1:
            return '<span class="badge badge-silver">Strong Match</span>'
        if index == 2:
            return '<span class="badge badge-bronze">Good Match</span>'
        return '<span class="badge">Candidate</span>'

    def score_percent(score: float) -> int:
        capped = max(0.0, min(score, 1.2))
        return int((capped / 1.2) * 100)

    features = ", ".join(result.extracted_traits.features) if result.extracted_traits.features else "None"
    queries = " | ".join(result.extracted_traits.generated_queries[: settings.max_search_queries])
    footprint_tags = ", ".join(result.extracted_traits.footprint_tags) if result.extracted_traits.footprint_tags else "None"

    trait_html = f"""
    <div class="traits-panel">
        <div class="traits-grid">
            <div class="trait-box">
                <div class="trait-label">Footprint</div>
                <div class="trait-value">{escape(result.extracted_traits.footprint_guess or "unknown")}</div>
            </div>
            <div class="trait-box">
                <div class="trait-label">Footprint Complexity</div>
                <div class="trait-value">{escape(result.extracted_traits.footprint_complexity or "unknown")}</div>
            </div>
            <div class="trait-box">
                <div class="trait-label">Floors Visible</div>
                <div class="trait-value">{result.extracted_traits.floors_visible or "unknown"}</div>
            </div>
            <div class="trait-box trait-wide">
                <div class="trait-label">Footprint Tags</div>
                <div class="trait-value">{escape(footprint_tags)}</div>
            </div>
            <div class="trait-box trait-wide">
                <div class="trait-label">Features</div>
                <div class="trait-value">{escape(features)}</div>
            </div>
            <div class="trait-box trait-wide">
                <div class="trait-label">Queries Used</div>
                <div class="trait-value">{escape(queries)}</div>
            </div>
            <div class="trait-box trait-wide">
                <div class="trait-label">Reasoning</div>
                <div class="trait-value">{escape(result.extracted_traits.reasoning_summary)}</div>
            </div>
        </div>
    </div>
    """

    cards = []
    for index, match in enumerate(result.matches):
        reasons = "".join(f"<li>{escape(reason)}</li>" for reason in match.reasons)
        thumbnail = (
            f'<img src="{escape(match.thumbnail_url)}" alt="thumbnail" class="thumb">'
            if match.thumbnail_url
            else '<div class="thumb thumb-placeholder">No thumbnail</div>'
        )

        cards.append(
            f"""
            <div class="result-card">
                <div class="thumb-wrap">
                    {thumbnail}
                </div>
                <div class="result-content">
                    <div class="result-top">
                        {badge_for_index(index)}
                        <div class="score-chip">Score {match.score:.2f}</div>
                    </div>

                    <h2 class="result-title">
                        <a href="{escape(match.url)}" target="_blank" rel="noopener noreferrer">
                            {escape(match.title)}
                        </a>
                    </h2>

                    <div class="meta-row">
                        <span><strong>Channel:</strong> {escape(match.channel_title)}</span>
                        <span><strong>Published:</strong> {escape(match.published_at or "Unknown")}</span>
                    </div>

                    <div class="score-bar">
                        <div class="score-fill" style="width: {score_percent(match.score)}%;"></div>
                    </div>

                    <p class="description">{escape(match.description or "No description available.")}</p>

                    <div class="reason-block">
                        <div class="reason-title">Why it matched</div>
                        <ul>
                            {reasons}
                        </ul>
                    </div>

                    <div class="actions-row">
                        <a class="watch-link" href="{escape(match.url)}" target="_blank" rel="noopener noreferrer">
                            Watch on YouTube
                        </a>
                    </div>
                </div>
            </div>
            """
        )

    raw_json = json.dumps(result.model_dump(), indent=2)
    raw_json_html = escape(raw_json)

    notes_value = escape(notes or "")
    footprint_value = escape(footprint or "")
    team_size_value = escape(team_size or "")

    html = f"""
    <html>
        <head>
            <title>Rust Base Finder Results</title>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
                :root {{
                    --bg: #0f1115;
                    --panel: #171a21;
                    --panel-2: #1d2230;
                    --text: #e8ecf1;
                    --muted: #9aa4b2;
                    --accent: #4f8cff;
                    --accent-hover: #3b73dc;
                    --border: #2a3142;
                    --gold: #f5c451;
                    --silver: #b7c3d7;
                    --bronze: #d6935b;
                }}

                * {{ box-sizing: border-box; }}

                body {{
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: linear-gradient(180deg, #0c0f14 0%, #11151d 100%);
                    color: var(--text);
                }}

                .container {{
                    max-width: 1120px;
                    margin: 0 auto;
                    padding: 28px 20px 40px;
                }}

                .topbar {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 16px;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                }}

                .page-title {{
                    font-size: 32px;
                    margin: 0;
                }}

                .back-link {{
                    color: #8db8ff;
                    text-decoration: none;
                    font-weight: 700;
                }}

                .retry-panel,
                .traits-panel,
                .json-panel {{
                    background: rgba(23, 26, 33, 0.95);
                    border: 1px solid var(--border);
                    border-radius: 18px;
                    padding: 20px;
                    margin-bottom: 20px;
                    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
                }}

                .retry-title,
                .json-title {{
                    margin: 0 0 14px;
                    font-size: 20px;
                }}

                .retry-grid {{
                    display: grid;
                    grid-template-columns: 1fr 1fr 1fr;
                    gap: 12px;
                }}

                .retry-grid .full {{
                    grid-column: 1 / -1;
                }}

                label {{
                    display: block;
                    margin-bottom: 8px;
                    font-size: 14px;
                    font-weight: 700;
                }}

                input[type="text"],
                input[type="file"] {{
                    width: 100%;
                    padding: 12px 14px;
                    border-radius: 10px;
                    border: 1px solid var(--border);
                    background: var(--panel-2);
                    color: var(--text);
                    font-size: 14px;
                }}

                .submit-btn {{
                    margin-top: 14px;
                    padding: 12px 18px;
                    border: none;
                    border-radius: 10px;
                    background: var(--accent);
                    color: white;
                    font-weight: 700;
                    cursor: pointer;
                }}

                .submit-btn:hover {{
                    background: var(--accent-hover);
                }}

                .traits-grid {{
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 12px;
                }}

                .trait-box {{
                    background: rgba(29, 34, 48, 0.72);
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 14px;
                }}

                .trait-wide {{
                    grid-column: span 3;
                }}

                .trait-label {{
                    color: var(--muted);
                    font-size: 13px;
                    margin-bottom: 8px;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                }}

                .trait-value {{
                    font-size: 15px;
                    line-height: 1.5;
                }}

                .results-grid {{
                    display: grid;
                    gap: 18px;
                }}

                .result-card {{
                    display: grid;
                    grid-template-columns: 260px 1fr;
                    gap: 18px;
                    background: rgba(23, 26, 33, 0.95);
                    border: 1px solid var(--border);
                    border-radius: 18px;
                    padding: 18px;
                    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.22);
                }}

                .thumb-wrap {{ width: 100%; }}

                .thumb {{
                    width: 100%;
                    height: auto;
                    display: block;
                    border-radius: 14px;
                    border: 1px solid var(--border);
                }}

                .thumb-placeholder {{
                    width: 100%;
                    min-height: 140px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 14px;
                    background: var(--panel-2);
                    color: var(--muted);
                    border: 1px solid var(--border);
                }}

                .result-content {{ min-width: 0; }}

                .result-top {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 10px;
                    flex-wrap: wrap;
                    margin-bottom: 10px;
                }}

                .badge {{
                    display: inline-flex;
                    align-items: center;
                    padding: 6px 10px;
                    border-radius: 999px;
                    font-size: 12px;
                    font-weight: 700;
                    background: #25304a;
                    border: 1px solid var(--border);
                }}

                .badge-gold {{
                    background: rgba(245, 196, 81, 0.12);
                    color: var(--gold);
                    border-color: rgba(245, 196, 81, 0.35);
                }}

                .badge-silver {{
                    background: rgba(183, 195, 215, 0.12);
                    color: var(--silver);
                    border-color: rgba(183, 195, 215, 0.35);
                }}

                .badge-bronze {{
                    background: rgba(214, 147, 91, 0.12);
                    color: var(--bronze);
                    border-color: rgba(214, 147, 91, 0.35);
                }}

                .score-chip {{
                    font-size: 13px;
                    color: var(--muted);
                    font-weight: 700;
                }}

                .result-title {{
                    margin: 0 0 10px;
                    font-size: 24px;
                    line-height: 1.3;
                }}

                .result-title a {{
                    color: #90bbff;
                    text-decoration: none;
                }}

                .result-title a:hover {{
                    text-decoration: underline;
                }}

                .meta-row {{
                    display: flex;
                    gap: 18px;
                    flex-wrap: wrap;
                    color: var(--muted);
                    font-size: 14px;
                    margin-bottom: 12px;
                }}

                .score-bar {{
                    width: 100%;
                    height: 10px;
                    border-radius: 999px;
                    background: #242b39;
                    overflow: hidden;
                    margin-bottom: 14px;
                }}

                .score-fill {{
                    height: 100%;
                    background: linear-gradient(90deg, #4f8cff 0%, #34c759 100%);
                }}

                .description {{
                    color: #d6dde7;
                    line-height: 1.6;
                    font-size: 14px;
                    margin-bottom: 14px;
                }}

                .reason-block {{
                    background: rgba(29, 34, 48, 0.72);
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 14px;
                    margin-bottom: 14px;
                }}

                .reason-title {{
                    font-weight: 700;
                    margin-bottom: 8px;
                }}

                .reason-block ul {{
                    margin: 0;
                    padding-left: 18px;
                    color: #d6dde7;
                }}

                .reason-block li {{ margin-bottom: 6px; }}

                .actions-row {{
                    display: flex;
                    align-items: center;
                    gap: 10px;
                    flex-wrap: wrap;
                }}

                .watch-link {{
                    display: inline-block;
                    padding: 10px 14px;
                    border-radius: 10px;
                    background: var(--accent);
                    color: white;
                    text-decoration: none;
                    font-weight: 700;
                }}

                .watch-link:hover {{
                    background: var(--accent-hover);
                }}

                .json-help {{
                    color: var(--muted);
                    margin-bottom: 12px;
                    line-height: 1.5;
                    font-size: 14px;
                }}

                .json-box {{
                    width: 100%;
                    min-height: 340px;
                    border-radius: 12px;
                    border: 1px solid var(--border);
                    background: #0d1117;
                    color: #d7e0ea;
                    padding: 14px;
                    font-family: Consolas, monospace;
                    font-size: 13px;
                    line-height: 1.5;
                    white-space: pre-wrap;
                    overflow: auto;
                }}

                @media (max-width: 900px) {{
                    .retry-grid,
                    .traits-grid {{
                        grid-template-columns: 1fr;
                    }}

                    .trait-wide {{
                        grid-column: span 1;
                    }}

                    .result-card {{
                        grid-template-columns: 1fr;
                    }}

                    .thumb {{
                        max-height: 260px;
                        object-fit: cover;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="topbar">
                    <h1 class="page-title">Rust Base Finder Results</h1>
                    <a class="back-link" href="/">← Back to search</a>
                </div>

                <div class="retry-panel">
                    <h2 class="retry-title">Try another search</h2>
                    <form action="/api/results" method="post" enctype="multipart/form-data">
                        <div class="retry-grid">
                            <div class="full">
                                <label for="screenshots">Screenshots</label>
                                <input id="screenshots" name="screenshots" type="file" multiple required>
                            </div>
                            <div>
                                <label for="footprint">Footprint</label>
                                <input id="footprint" name="footprint" type="text" value="{footprint_value}" placeholder="2x2 or square core with side triangles">
                            </div>
                            <div>
                                <label for="team_size">Team Size</label>
                                <input id="team_size" name="team_size" type="text" value="{team_size_value}" placeholder="duo">
                            </div>
                            <div class="full">
                                <label for="notes">Notes</label>
                                <input id="notes" name="notes" type="text" value="{notes_value}" placeholder="roof bunker wide gaps">
                            </div>
                        </div>
                        <button class="submit-btn" type="submit">Run Search Again</button>
                    </form>
                </div>

                {trait_html}

                <div class="results-grid">
                    {''.join(cards)}
                </div>

                <div class="json-panel">
                    <h2 class="json-title">Raw JSON</h2>
                    <div class="json-help">
                        Copy this block when you want to inspect or share the exact backend output.
                    </div>
                    <pre class="json-box">{raw_json_html}</pre>
                </div>
            </div>
        </body>
    </html>
    """

    return HTMLResponse(content=html)