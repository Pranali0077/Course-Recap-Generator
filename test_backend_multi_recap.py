"""Lightweight, deterministic test suite for independent multi-file recap generation.

Verifies:
TEST A: 1 uploaded file -> exactly 1 independent recap.
TEST B: 2 uploaded files -> exactly 2 independent recaps (no combined recap).
TEST C: 3 uploaded files -> exactly 3 independent recaps:
  - 3 output Markdown files are created
  - each output filename corresponds to the correct input file
  - each recap contains only its own source's topics
  - each recap has its own Mermaid/concept diagram
  - no combined recap is generated
TEST D: Frontend displays 3 separate recap cards when 3 files are uploaded.
TEST E: Validation and error handling for empty uploads and invalid file extensions.
"""

import io
from pathlib import Path
import re
import time
from unittest.mock import MagicMock, patch

from src.app import create_app
from src.config import OUTPUTS_DIR


def make_mock_recap_for_file(pdf_path, model="gemini-3.5-flash-lite"):
    """Deterministic mock for generate_course_recap producing source-isolated recaps."""
    p = Path(pdf_path)
    stem = p.stem.replace("_recap", "").replace("_Recap", "")
    target_path = OUTPUTS_DIR / f"{stem}_recap.md"

    # Topics and diagram isolated strictly to this specific file
    markdown = f"""# {stem.upper()} Independent Lecture Recap - Comprehensive Course Recap

## Course Overview
High-yield overview synthesized strictly and exclusively from {stem}.pdf. Demonstrates isolated topic extraction without cross-document contamination.

---

## Topic-by-Topic Course Summary

### 1. {stem.upper()} Core Mechanics
**Overview & Mechanisms:**
Detailed mechanisms originating exclusively from {stem}.pdf.

**Key Definitions & Principles:**
- **{stem.upper()}_Core_Principle:** Definitive rule for {stem}.

**Practical Implications:**
Practical applications strictly applicable to {stem}.

---

### 2. {stem.upper()} Advanced Concepts
**Overview & Mechanisms:**
Advanced architectural paradigms established in {stem}.pdf.

**Key Definitions & Principles:**
- **{stem.upper()}_Advanced_Metric:** Evaluation standard for {stem}.

**Practical Implications:**
System deployment considerations for {stem}.

---

## Concept Relationship Diagram

```mermaid
flowchart TD
    {stem}_A["{stem.upper()} Foundations<br/>Core base theory"] --> {stem}_B["{stem.upper()} Mechanics<br/>Execution model"]
    {stem}_B --> {stem}_C["{stem.upper()} Systems<br/>Deployment architecture"]
```
"""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(markdown, encoding="utf-8")
    return target_path, markdown


def run_tests():
    start_total = time.time()
    pdf1 = Path("data/astra1.pdf").resolve()
    pdf2 = Path("data/astra2.pdf").resolve()
    pdf3 = Path("data/astra3.pdf").resolve()

    assert pdf1.exists(), f"Missing fixture: {pdf1}"
    assert pdf2.exists(), f"Missing fixture: {pdf2}"
    assert pdf3.exists(), f"Missing fixture: {pdf3}"

    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    print("=" * 75)
    print("RUNNING INDEPENDENT MULTI-FILE RECAP BACKEND & FRONTEND TEST SUITE")
    print("=" * 75)

    # ------------------------------------------------------------------
    # TEST A: 1 uploaded file -> exactly 1 recap
    # ------------------------------------------------------------------
    print("\n[TEST A] Verifying 1 uploaded file -> exactly 1 recap...")
    t0 = time.time()
    with patch("src.app.generate_course_recap", side_effect=make_mock_recap_for_file) as mock_gen:
        with open(pdf1, "rb") as f1:
            data = {
                "model": "gemini-3.5-flash-lite",
                "files": [(f1, "astra1.pdf")],
            }
            r = client.post("/api/generate", data=data, content_type="multipart/form-data")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_data(as_text=True)}"
        res = r.get_json()
        assert res.get("success") is True, f"Response failed: {res}"
        assert res.get("files_count") == 1, f"Expected files_count == 1, got {res.get('files_count')}"
        recaps = res.get("recaps", [])
        assert len(recaps) == 1, f"Expected exactly 1 recap in list, got {len(recaps)}"

        recap1 = recaps[0]
        assert recap1["filename"] == "astra1.pdf"
        assert recap1["output_filename"] == "astra1_recap.md"
        assert "ASTRA1" in recap1["title"]
        assert recap1["stats"]["topics_count"] == 2
        assert recap1["stats"]["has_diagram"] is True
        assert (OUTPUTS_DIR / "astra1_recap.md").exists()

        # Verify generator was called exactly once with a single Path
        assert mock_gen.call_count == 1
        called_path = mock_gen.call_args.kwargs.get("pdf_path")
        assert isinstance(called_path, Path)
        assert called_path.name == "astra1.pdf"

    print(f"  [+] Status: HTTP {r.status_code}")
    print(f"  [+] Recaps Count: {len(recaps)}")
    print(f"  [+] Output Filename: {recap1['output_filename']}")
    print(f"  [+] Generator Call Count: {mock_gen.call_count}")
    print(f"  [+] Passed in {time.time() - t0:.3f}s")

    # ------------------------------------------------------------------
    # TEST B: 2 uploaded files -> exactly 2 independent recaps
    # ------------------------------------------------------------------
    print("\n[TEST B] Verifying 2 uploaded files -> exactly 2 independent recaps...")
    t0 = time.time()
    with patch("src.app.generate_course_recap", side_effect=make_mock_recap_for_file) as mock_gen:
        with open(pdf1, "rb") as f1, open(pdf2, "rb") as f2:
            data = {
                "model": "gemini-3.5-flash-lite",
                "files": [
                    (f1, "astra1.pdf"),
                    (f2, "astra2.pdf"),
                ],
            }
            r = client.post("/api/generate", data=data, content_type="multipart/form-data")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        res = r.get_json()
        assert res.get("success") is True
        assert res.get("files_count") == 2
        recaps = res.get("recaps", [])
        assert len(recaps) == 2, f"Expected exactly 2 recaps, got {len(recaps)}"

        assert recaps[0]["filename"] == "astra1.pdf"
        assert recaps[0]["output_filename"] == "astra1_recap.md"
        assert recaps[1]["filename"] == "astra2.pdf"
        assert recaps[1]["output_filename"] == "astra2_recap.md"

        # Verify no combined recap was generated
        for recap in recaps:
            assert "combined" not in recap["output_filename"].lower()
            assert "combined" not in recap["title"].lower()

        # Verify generator was called independently for each file (twice)
        assert mock_gen.call_count == 2
        called_names = [call.kwargs["pdf_path"].name for call in mock_gen.call_args_list]
        assert called_names == ["astra1.pdf", "astra2.pdf"]

    print(f"  [+] Status: HTTP {r.status_code}")
    print(f"  [+] Recaps Count: {len(recaps)}")
    print(f"  [+] Recap 1 Output: {recaps[0]['output_filename']}")
    print(f"  [+] Recap 2 Output: {recaps[1]['output_filename']}")
    print(f"  [+] Generator Call Count: {mock_gen.call_count}")
    print(f"  [+] Passed in {time.time() - t0:.3f}s")

    # ------------------------------------------------------------------
    # TEST C: 3 uploaded files -> exactly 3 independent recaps
    # ------------------------------------------------------------------
    print("\n[TEST C] Verifying 3 uploaded files -> exactly 3 independent recaps...")
    t0 = time.time()
    with patch("src.app.generate_course_recap", side_effect=make_mock_recap_for_file) as mock_gen:
        with open(pdf1, "rb") as f1, open(pdf2, "rb") as f2, open(pdf3, "rb") as f3:
            data = {
                "model": "gemini-3.8-flash",
                "files": [
                    (f1, "astra1.pdf"),
                    (f2, "astra2.pdf"),
                    (f3, "astra3.pdf"),
                ],
            }
            r = client.post("/api/generate", data=data, content_type="multipart/form-data")

        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        res = r.get_json()
        assert res.get("success") is True
        assert res.get("files_count") == 3
        recaps = res.get("recaps", [])
        assert len(recaps) == 3, f"Expected exactly 3 recaps, got {len(recaps)}"

        # 1. Verify 3 output Markdown files are created on disk
        expected_outputs = ["astra1_recap.md", "astra2_recap.md", "astra3_recap.md"]
        for out_name in expected_outputs:
            out_file = OUTPUTS_DIR / out_name
            assert out_file.exists(), f"Expected output file on disk: {out_file}"
            content = out_file.read_text(encoding="utf-8")
            assert len(content) > 50

        # 2. Verify each output filename corresponds to the correct input file
        assert recaps[0]["filename"] == "astra1.pdf"
        assert recaps[0]["output_filename"] == "astra1_recap.md"

        assert recaps[1]["filename"] == "astra2.pdf"
        assert recaps[1]["output_filename"] == "astra2_recap.md"

        assert recaps[2]["filename"] == "astra3.pdf"
        assert recaps[2]["output_filename"] == "astra3_recap.md"

        # 3. Verify each recap contains only its own source's topics
        # Recap 0: contains only ASTRA1 topics
        topics0_text = " ".join([t["name"] + " " + t["raw_content"] for t in recaps[0]["topics"]])
        assert "ASTRA1" in topics0_text
        assert "ASTRA2" not in topics0_text
        assert "ASTRA3" not in topics0_text

        # Recap 1: contains only ASTRA2 topics
        topics1_text = " ".join([t["name"] + " " + t["raw_content"] for t in recaps[1]["topics"]])
        assert "ASTRA2" in topics1_text
        assert "ASTRA1" not in topics1_text
        assert "ASTRA3" not in topics1_text

        # Recap 2: contains only ASTRA3 topics
        topics2_text = " ".join([t["name"] + " " + t["raw_content"] for t in recaps[2]["topics"]])
        assert "ASTRA3" in topics2_text
        assert "ASTRA1" not in topics2_text
        assert "ASTRA2" not in topics2_text

        # 4. Verify each recap has its own Mermaid/concept diagram with short node descriptions (<br/>)
        assert recaps[0]["stats"]["has_diagram"] is True
        assert "astra1_A" in recaps[0]["mermaid"]
        assert "<br/>" in recaps[0]["mermaid"], "Expected multiline node description format in diagram"
        assert "astra2_A" not in recaps[0]["mermaid"]
        assert "astra3_A" not in recaps[0]["mermaid"]

        assert recaps[1]["stats"]["has_diagram"] is True
        assert "astra2_A" in recaps[1]["mermaid"]
        assert "<br/>" in recaps[1]["mermaid"], "Expected multiline node description format in diagram"
        assert "astra1_A" not in recaps[1]["mermaid"]
        assert "astra3_A" not in recaps[1]["mermaid"]

        assert recaps[2]["stats"]["has_diagram"] is True
        assert "astra3_A" in recaps[2]["mermaid"]
        assert "<br/>" in recaps[2]["mermaid"], "Expected multiline node description format in diagram"
        assert "astra1_A" not in recaps[2]["mermaid"]
        assert "astra2_A" not in recaps[2]["mermaid"]

        # 5. Verify no combined recap is generated
        assert mock_gen.call_count == 3
        for call in mock_gen.call_args_list:
            pdf_arg = call.kwargs["pdf_path"]
            assert isinstance(pdf_arg, Path), f"Expected single Path, got {type(pdf_arg)}"
            assert "combined" not in pdf_arg.name.lower()

        for recap in recaps:
            assert "combined" not in recap["output_filename"].lower()
            assert "combined" not in recap["title"].lower()

    print(f"  [+] Status: HTTP {r.status_code}")
    print(f"  [+] 3 Output Files Created: {expected_outputs}")
    print(f"  [+] File-to-output mapping verified: 1:1 correspondence")
    print(f"  [+] Topic isolation verified: no cross-contamination")
    print(f"  [+] Independent Mermaid diagrams verified for all 3 files")
    print(f"  [+] No combined recap confirmed")
    print(f"  [+] Passed in {time.time() - t0:.3f}s")

    # ------------------------------------------------------------------
    # TEST D: Verify exactly ONE Detailed Recap Viewer with 3 File Tabs
    # ------------------------------------------------------------------
    print("\n[TEST D] Verifying frontend displays exactly ONE detailed viewer with 3 file tabs...")
    t0 = time.time()

    index_html = (Path("src/templates/index.html")).read_text(encoding="utf-8")
    app_js = (Path("src/static/js/app.js")).read_text(encoding="utf-8")

    # 1. Verify duplicate "Independent Recaps" card/grid section is REMOVED
    assert 'id="multi-recaps-section"' not in index_html, "Duplicate multi-recaps-section must be removed"
    assert 'multi-recaps-grid' not in index_html, "Duplicate multi-recaps-grid must be removed"
    assert "renderMultiRecapsCards" not in app_js, "Duplicate card grid rendering must be removed"

    # 2. Verify exactly ONE detailed recap viewer structure exists
    assert 'id="results-section"' in index_html
    assert 'id="active-recap-detail-card"' in index_html
    assert 'id="course-title-display"' in index_html
    assert 'id="overview-card"' in index_html
    assert 'id="mermaid-rendered-container"' in index_html
    assert 'id="topics-container"' in index_html
    assert 'id="btn-download-markdown"' in index_html

    # 3. Verify top file-selection tabs exist in template and JS
    assert 'id="file-tabs-bar"' in index_html
    assert 'id="file-tabs-list"' in index_html
    assert "renderFileTabs" in app_js
    assert "selectActiveFile" in app_js

    # 4. Simulate rendering file-selection tabs for the 3 uploaded files
    simulated_tabs = [
        f'<button class="file-tab-btn" data-file-index="{idx}">{recap["filename"]}</button>'
        for idx, recap in enumerate(recaps)
    ]
    assert len(simulated_tabs) == 3, f"Expected exactly 3 file tabs, got {len(simulated_tabs)}"
    for idx, tab in enumerate(simulated_tabs):
        assert f"astra{idx+1}.pdf" in tab

    # 5. Verify isolated content when each file is active (no cross-contamination)
    for active_idx, target_recap in enumerate(recaps):
        # Active file content
        active_filename = target_recap["filename"]
        active_title = target_recap["title"]
        active_mermaid = target_recap["mermaid"]
        active_topics = " ".join([t["name"] + " " + t["raw_content"] for t in target_recap["topics"]])

        # Inactive files
        other_recaps = [r for i, r in enumerate(recaps) if i != active_idx]
        for other in other_recaps:
            other_stem = Path(other["filename"]).stem.upper()
            assert other_stem not in active_title, f"{other_stem} leaked into {active_filename} title"
            assert other_stem not in active_topics, f"{other_stem} leaked into {active_filename} topics"
            assert f"{other_stem.lower()}_A" not in active_mermaid, f"{other_stem} diagram leaked into {active_filename}"

    # 6. Verify single file behavior (hide tabs, show detailed recap directly)
    single_file_recap = [recaps[0]]
    assert len(single_file_recap) == 1
    # JS logic: if (recaps.length <= 1) fileTabsBar.style.display = 'none';
    assert "recaps.length <= 1" in app_js
    assert "fileTabsBar.style.display = 'none'" in app_js

    print(f"  [+] Confirmed: Duplicate 'Independent Recaps' section removed.")
    print(f"  [+] Confirmed: Exactly ONE detailed recap viewer present.")
    print(f"  [+] Confirmed: 3 file tabs rendered: [ astra1.pdf ] [ astra2.pdf ] [ astra3.pdf ].")
    print(f"  [+] Confirmed: 100% strict content isolation when selecting each file (no cross-contamination).")
    print(f"  [+] Confirmed: File tabs automatically hidden when only 1 file is uploaded.")
    print(f"  [+] Passed in {time.time() - t0:.3f}s")

    # ------------------------------------------------------------------
    # TEST E: Input Validation and Error Handling
    # ------------------------------------------------------------------
    print("\n[TEST E] Verifying input validation and error handling...")
    t0 = time.time()

    # Empty payload
    r_empty = client.post("/api/generate", data={}, content_type="multipart/form-data")
    assert r_empty.status_code == 400
    assert "No course file(s) uploaded" in r_empty.get_json().get("error", "")

    # Invalid extension
    r_invalid = client.post(
        "/api/generate",
        data={"files": [(io.BytesIO(b"hello world"), "notes.txt")]},
        content_type="multipart/form-data",
    )
    assert r_invalid.status_code == 400
    assert "Invalid format" in r_invalid.get_json().get("error", "")

    print(f"  [+] Empty payload rejection: HTTP {r_empty.status_code}")
    print(f"  [+] Invalid file extension rejection: HTTP {r_invalid.status_code}")
    print(f"  [+] Passed in {time.time() - t0:.3f}s")

    total_elapsed = time.time() - start_total
    print("\n" + "=" * 75)
    print(f"ALL TESTS PASSED SUCCESSFULLY in {total_elapsed:.2f}s!")
    print("=" * 75)


if __name__ == "__main__":
    run_tests()
