"""PDF Extraction MCP Server.

Dedicated solely to real PDF text and content extraction.
Exposes tool: `extract_pdf_content(file_path: str) -> dict`.
"""

from pathlib import Path
from typing import Any, Dict, List
import json
import os
import pypdf
from mcp.server.mcpserver import MCPServer

# Initialize the ONE MCP Server
mcp_server = MCPServer(
    name="pdf-extractor",
    instructions="A dedicated MCP server for extracting structured text and metadata from PDF course slides and documents.",
    version="1.0.0",
)


@mcp_server.tool(
    name="extract_pdf_content",
    description="Extracts structured text, page breakdown, and metadata from a local course PDF document.",
)
def extract_pdf_content(file_path: str) -> Dict[str, Any]:
    """Extract real content from a local PDF file.

    Args:
        file_path: Absolute or relative path to the PDF file.

    Returns:
        dict: A structured dictionary containing:
            - metadata: File size, page count, document title, author.
            - pages: List of per-page text content and page numbers.
            - full_text: Aggregated clean text with page boundary markers.
            - total_characters: Total extracted character count.
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found at path: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a regular file: {file_path}")
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF (expected .pdf extension): {file_path}")

    try:
        reader = pypdf.PdfReader(str(path))
    except Exception as exc:
        raise ValueError(f"Failed to parse PDF document {path.name}: {exc}") from exc

    page_count = len(reader.pages)
    file_size = path.stat().st_size

    # Extract metadata safely
    raw_meta = reader.metadata or {}
    metadata = {
        "file_name": path.name,
        "file_path": str(path),
        "file_size_bytes": file_size,
        "page_count": page_count,
        "title": getattr(raw_meta, "title", None) or path.stem,
        "author": getattr(raw_meta, "author", None) or "Unknown",
    }

    pages_data: List[Dict[str, Any]] = []
    text_parts: List[str] = []

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        try:
            page_text = page.extract_text() or ""
        except Exception:
            page_text = ""

        # Normalize line endings and strip trailing whitespace
        cleaned_text = "\n".join(
            line.strip() for line in page_text.splitlines() if line.strip()
        )

        pages_data.append(
            {
                "page_number": page_num,
                "text": cleaned_text,
                "character_count": len(cleaned_text),
            }
        )

        text_parts.append(f"--- [Page {page_num}] ---\n{cleaned_text}")

    full_text = "\n\n".join(text_parts)

    return {
        "metadata": metadata,
        "pages": pages_data,
        "full_text": full_text,
        "total_characters": len(full_text),
    }


if __name__ == "__main__":
    # Runs the MCP server over stdio
    mcp_server.run(transport="stdio")
