"""End-to-end Course Recap Generator pipeline.

Executes the strict workflow:
Course PDF -> PDF Extraction MCP Server -> Extracted Content -> Main Agent (course-recap skill) -> Draft Recap -> course-reviewer Sub-Agent -> Final Corrected Recap.
"""

from pathlib import Path
from typing import Dict, Any, Tuple
from google import genai

from src.config import PROJECT_ROOT, OUTPUTS_DIR, DEFAULT_MODEL, get_gemini_api_key
from src.extractor import extract_pdf_via_mcp
from src.reviewer import review_recap_with_subagent


def load_course_recap_skill() -> str:
    """Load the ONE custom skill from .gemini/skills/course-recap/SKILL.md."""
    skill_path = PROJECT_ROOT / ".gemini" / "skills" / "course-recap" / "SKILL.md"
    if not skill_path.exists():
        raise FileNotFoundError(f"Custom skill not found at: {skill_path}")
    return skill_path.read_text(encoding="utf-8")


def generate_course_recap(
    pdf_path: str | Path,
    output_path: Path | None = None,
    model: str = DEFAULT_MODEL,
) -> Tuple[Path, str]:
    """Execute the complete end-to-end course recap pipeline.

    Args:
        pdf_path: Path to the real course PDF file.
        output_path: Optional destination path for the markdown recap.
        model: Gemini model identifier (default: gemini-3.8-flash).

    Returns:
        tuple: (output_file_path, final_recap_markdown)
    """
    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.exists():
        raise FileNotFoundError(f"Course PDF does not exist: {pdf_file}")

    api_key = get_gemini_api_key()
    client = genai.Client(api_key=api_key)

    # 1. Extract real PDF content using the ONE MCP server
    print(f"[*] Step 1/4: Invoking PDF Extraction MCP Server for {pdf_file.name}...")
    extracted_data = extract_pdf_via_mcp(pdf_file)
    meta = extracted_data.get("metadata", {})
    full_text = extracted_data.get("full_text", "")
    page_count = meta.get("page_count", len(extracted_data.get("pages", [])))
    print(
        f"    [+] Successfully extracted {len(full_text):,} characters across {page_count} pages."
    )

    if not full_text.strip():
        raise ValueError(
            f"No readable text could be extracted from {pdf_file.name}. Ensure it is not a scanned/image-only PDF."
        )

    # 2. Load the ONE custom reusable skill: course-recap
    print("[*] Step 2/4: Loading custom 'course-recap' skill...")
    skill_instructions = load_course_recap_skill()

    # 3. Main Agent generation guided by the skill
    print(
        f"[*] Step 3/4: Main Agent synthesizing topic breakdown and concept graph ({model})..."
    )
    main_prompt = f"""You are an expert academic curriculum synthesizer. Follow the rules and guidelines in the skill below:

--- COURSE RECAP SKILL GUIDELINES ---
{skill_instructions}
--- END SKILL GUIDELINES ---

Produce a detailed topic-by-topic course summary and a Mermaid concept relationship diagram (`flowchart TD`) based strictly on the following course source material:

--- COURSE SOURCE MATERIAL ---
{full_text}
--- END SOURCE MATERIAL ---
"""

    draft_response = client.models.generate_content(
        model=model,
        contents=main_prompt,
    )
    draft_recap = draft_response.text or ""
    if not draft_recap.strip():
        raise RuntimeError("Main agent failed to generate a draft recap.")

    print(f"    [+] Draft recap generated ({len(draft_recap):,} characters).")

    # 4. Invoke the ONE harness-defined sub-agent: course-reviewer
    print(
        "[*] Step 4/4: Invoking 'course-reviewer' sub-agent to audit against ground truth..."
    )
    final_recap = review_recap_with_subagent(
        client=client,
        source_content=full_text,
        draft_recap=draft_recap,
        model=model,
    )
    print(
        f"    [+] Sub-agent audit complete. Final verified recap ready ({len(final_recap):,} characters)."
    )

    # Determine destination output path
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        target_path = OUTPUTS_DIR / f"{pdf_file.stem}_recap.md"
    else:
        target_path = Path(output_path).resolve()
        target_path.parent.mkdir(parents=True, exist_ok=True)

    target_path.write_text(final_recap, encoding="utf-8")
    print(f"[+] Output written to: {target_path}")

    return target_path, final_recap

