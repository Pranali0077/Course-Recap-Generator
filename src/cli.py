"""Lightweight Command-Line Interface for Course Recap Generator."""

import argparse
import sys
from pathlib import Path

from src.config import DEFAULT_MODEL, GEMINI_API_KEY, PROJECT_ROOT
from src.generator import generate_course_recap
from src.extractor import extract_pdf_via_mcp


def command_check() -> int:
    """Run diagnostics on environment, MCP server, skill, and sub-agent."""
    print("=" * 60)
    print("Course Recap Generator - System Diagnostics")
    print("=" * 60)

    # 1. Check GEMINI_API_KEY
    try:
        from src.config import get_gemini_api_key
        get_gemini_api_key()
        print("[OK] GEMINI_API_KEY is detected.")
    except ValueError:
        print("[WARN] GEMINI_API_KEY is not set in .env or environment.")

    # 2. Check Custom Skill
    skill_file = PROJECT_ROOT / ".gemini" / "skills" / "course-recap" / "SKILL.md"
    if skill_file.exists():
        print(f"[OK] Custom Skill 'course-recap' found at: {skill_file.relative_to(PROJECT_ROOT)}")
    else:
        print(f"[ERROR] Missing custom skill: {skill_file}")

    # 3. Check Sub-Agent definition
    reviewer_file = PROJECT_ROOT / "src" / "reviewer.py"
    if reviewer_file.exists():
        print("[OK] Sub-agent 'course-reviewer' definition verified in src/reviewer.py")
    else:
        print(f"[ERROR] Missing reviewer module: {reviewer_file}")

    # 4. Check MCP Server
    mcp_script = PROJECT_ROOT / "mcp" / "pdf_server.py"
    if mcp_script.exists():
        print(f"[OK] PDF Extraction MCP Server found at: {mcp_script.relative_to(PROJECT_ROOT)}")
    else:
        print(f"[ERROR] Missing MCP server script: {mcp_script}")

    print("=" * 60)
    return 0


def command_recap(args: argparse.Namespace) -> int:
    """Execute course recap generation on a specified PDF file."""
    pdf_path = Path(args.pdf_path)
    if not pdf_path.exists():
        print(f"[ERROR] PDF file does not exist: {pdf_path}", file=sys.stderr)
        return 1

    try:
        output_file, _ = generate_course_recap(
            pdf_path=pdf_path,
            output_path=Path(args.output) if args.output else None,
            model=args.model,
        )
        print("\n" + "=" * 60)
        print("Course Recap Generated Successfully!")
        print(f"Output File: {output_file}")
        print("=" * 60)
        return 0
    except Exception as exc:
        print(f"\n[ERROR] Recap generation failed: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="course-recap",
        description="Transforms course lecture PDFs into high-yield topic summaries and Mermaid concept diagrams.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: recap
    recap_parser = subparsers.add_parser("recap", help="Generate a course recap from a lecture PDF")
    recap_parser.add_argument("pdf_path", type=str, help="Path to the course PDF file")
    recap_parser.add_argument(
        "--output", "-o", type=str, default=None, help="Custom destination file path (default: outputs/<name>_recap.md)"
    )
    recap_parser.add_argument(
        "--model", "-m", type=str, default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})"
    )

    # Command: check
    subparsers.add_parser("check", help="Verify configuration, MCP server, skill, and sub-agent")

    args = parser.parse_args()

    if args.command == "check":
        sys.exit(command_check())
    elif args.command == "recap":
        sys.exit(command_recap(args))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
