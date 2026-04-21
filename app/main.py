from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routers.search import router as search_router

app = FastAPI(title="Rust Base Finder MVP")
app.include_router(search_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def home():
    return """
    <html>
        <head>
            <title>Rust Base Finder</title>
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <style>
                :root {
                    --bg: #0f1115;
                    --panel: #171a21;
                    --panel-2: #1d2230;
                    --text: #e8ecf1;
                    --muted: #9aa4b2;
                    --accent: #4f8cff;
                    --accent-hover: #3b73dc;
                    --border: #2a3142;
                    --good: #34c759;
                }

                * {
                    box-sizing: border-box;
                }

                body {
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: linear-gradient(180deg, #0c0f14 0%, #11151d 100%);
                    color: var(--text);
                }

                .container {
                    max-width: 980px;
                    margin: 0 auto;
                    padding: 32px 20px 48px;
                }

                .hero {
                    margin-bottom: 24px;
                }

                .title {
                    font-size: 36px;
                    font-weight: 700;
                    margin: 0 0 10px;
                }

                .subtitle {
                    color: var(--muted);
                    font-size: 16px;
                    line-height: 1.5;
                    margin: 0;
                    max-width: 760px;
                }

                .panel {
                    background: rgba(23, 26, 33, 0.95);
                    border: 1px solid var(--border);
                    border-radius: 18px;
                    padding: 24px;
                    box-shadow: 0 12px 30px rgba(0, 0, 0, 0.25);
                }

                .grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 16px;
                }

                .field {
                    margin-bottom: 16px;
                }

                .field.full {
                    grid-column: 1 / -1;
                }

                label {
                    display: block;
                    font-size: 14px;
                    font-weight: 700;
                    margin-bottom: 8px;
                    color: var(--text);
                }

                input[type="text"],
                input[type="file"] {
                    width: 100%;
                    padding: 12px 14px;
                    border-radius: 10px;
                    border: 1px solid var(--border);
                    background: var(--panel-2);
                    color: var(--text);
                    font-size: 14px;
                }

                input[type="file"] {
                    padding: 10px;
                }

                .help {
                    color: var(--muted);
                    font-size: 13px;
                    margin-top: 6px;
                    line-height: 1.4;
                }

                .actions {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                    margin-top: 12px;
                    flex-wrap: wrap;
                }

                button {
                    padding: 12px 18px;
                    border: none;
                    border-radius: 10px;
                    background: var(--accent);
                    color: white;
                    font-weight: 700;
                    font-size: 14px;
                    cursor: pointer;
                }

                button:hover {
                    background: var(--accent-hover);
                }

                .api-link {
                    color: var(--muted);
                    font-size: 14px;
                }

                .api-link a {
                    color: #8db8ff;
                    text-decoration: none;
                }

                .feature-row {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 14px;
                    margin-top: 20px;
                }

                .feature {
                    background: rgba(29, 34, 48, 0.7);
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 16px;
                }

                .feature-title {
                    font-weight: 700;
                    margin-bottom: 8px;
                }

                .feature-text {
                    font-size: 14px;
                    color: var(--muted);
                    line-height: 1.5;
                }

                @media (max-width: 800px) {
                    .grid,
                    .feature-row {
                        grid-template-columns: 1fr;
                    }

                    .title {
                        font-size: 28px;
                    }

                    .container {
                        padding: 20px 14px 36px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="hero">
                    <h1 class="title">Rust Base Finder</h1>
                    <p class="subtitle">
                        Upload one or more Rust base screenshots, add optional footprint notes,
                        and find likely matching tutorial videos from YouTube.
                    </p>
                </div>

                <div class="panel">
                    <form action="/api/results" method="post" enctype="multipart/form-data">
                        <div class="grid">
                            <div class="field full">
                                <label for="screenshots">Screenshots</label>
                                <input id="screenshots" name="screenshots" type="file" multiple required>
                                <div class="help">
                                    Upload 1 to 6 screenshots from different angles for better matching.
                                </div>
                            </div>

                            <div class="field">
                                <label for="footprint">Footprint</label>
                                <input id="footprint" name="footprint" type="text" placeholder="2x2">
                            </div>

                            <div class="field">
                                <label for="team_size">Team Size</label>
                                <input id="team_size" name="team_size" type="text" placeholder="duo">
                            </div>

                            <div class="field full">
                                <label for="notes">Notes</label>
                                <input id="notes" name="notes" type="text" placeholder="roof bunker wide gaps">
                                <div class="help">
                                    Useful terms: roof bunker, wide gaps, shooting floor, open core, shell, trio, starter.
                                </div>
                            </div>
                        </div>

                        <div class="actions">
                            <button type="submit">Find Matches</button>
                            <div class="api-link">API docs: <a href="/docs">/docs</a></div>
                        </div>
                    </form>

                    <div class="feature-row">
                        <div class="feature">
                            <div class="feature-title">Focused search</div>
                            <div class="feature-text">
                                Generates a small set of Rust-specific search queries instead of broad YouTube lookups.
                            </div>
                        </div>
                        <div class="feature">
                            <div class="feature-title">Smarter ranking</div>
                            <div class="feature-text">
                                Rewards footprint, bunker, shooting floor, and phrase matches while penalizing shorts.
                            </div>
                        </div>
                        <div class="feature">
                            <div class="feature-title">Faster retests</div>
                            <div class="feature-text">
                                Cached YouTube results make repeated searches faster and save quota during development.
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """