"""Mermaid diagram utilities and HTML export."""

from __future__ import annotations


def wrap_mermaid(diagram: str) -> str:
    """Ensure a Mermaid diagram is wrapped in fenced code blocks."""
    if not diagram.startswith("```mermaid"):
        return f"```mermaid\n{diagram}\n```"
    return diagram


def to_html(mermaid_str: str) -> str:
    """Generate a standalone HTML file for rendering a Mermaid diagram.

    Opens in any browser. Useful when the diagram is too large for inline rendering.
    """
    # Strip markdown fences if present
    clean = mermaid_str.replace("```mermaid", "").replace("```", "").strip()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Investigation Network Graph</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #1a1a2e;
            color: #eee;
            display: flex;
            justify-content: center;
            padding: 2rem;
        }}
        .mermaid {{
            background: #16213e;
            padding: 2rem;
            border-radius: 12px;
            max-width: 95vw;
            overflow-x: auto;
        }}
    </style>
</head>
<body>
    <div class="mermaid">
{clean}
    </div>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
    </script>
</body>
</html>"""
