"""Client interface for the ONE PDF Extraction MCP Server."""

import asyncio
from pathlib import Path
import sys
from typing import Any, Dict
import json

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from src.config import PROJECT_ROOT


async def _extract_pdf_via_mcp_async(pdf_path: Path) -> Dict[str, Any]:
    """Invoke the PDF extraction MCP server over stdio transport."""
    server_script = PROJECT_ROOT / "mcp" / "pdf_server.py"
    if not server_script.exists():
        raise FileNotFoundError(f"MCP server script not found at: {server_script}")

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(server_script)],
        env=None,
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                name="extract_pdf_content",
                arguments={"file_path": str(pdf_path.resolve())},
            )

            # Extract result content from MCP CallToolResult
            # If structured_content is populated, use that; otherwise parse text content
            if getattr(result, "structured_content", None):
                structured = result.structured_content
                if isinstance(structured, dict) and "result" in structured:
                    return structured["result"]
                return structured

            # Fallback: check content blocks
            for content_block in getattr(result, "content", []):
                # Text content could be json string or repr
                block_text = getattr(content_block, "text", "")
                if block_text:
                    try:
                        return json.loads(block_text)
                    except json.JSONDecodeError:
                        pass

            raise RuntimeError(
                f"Unexpected response from PDF Extraction MCP server: {result}"
            )


def extract_pdf_via_mcp(pdf_path: str | Path) -> Dict[str, Any]:
    """Extract structured course content from a PDF using the ONE MCP server.

    Args:
        pdf_path: Path to the course PDF file.

    Returns:
        dict: Extracted metadata, per-page content, and full unified text.
    """
    path = Path(pdf_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"Course PDF not found: {path}")

    return asyncio.run(_extract_pdf_via_mcp_async(path))
