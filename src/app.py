"""Flask Web Application for Course Recap Generator."""

from pathlib import Path
import re
import os
from typing import Dict, Any, List, Tuple
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from src.config import (
    PROJECT_ROOT,
    OUTPUTS_DIR,
    DATA_DIR,
    DEFAULT_MODEL,
    get_gemini_api_key,
)
from src.generator import generate_course_recap


def parse_recap_markdown(content: str, fallback_title: str = "Course Recap") -> Dict[str, Any]:
    """Parse structured elements from a generated course recap Markdown file.

    Extracts:
    - Title
    - Course Overview
    - Topic-by-Topic items (with mechanisms, definitions, and practical sections)
    - Mermaid diagram syntax
    - Full raw markdown
    """
    # 1. Extract Title
    title_match = re.search(
        r"^#\s*(.*?)(?:\s*-\s*Comprehensive Course Recap)?$",
        content,
        re.MULTILINE,
    )
    title = title_match.group(1).strip() if title_match else fallback_title

    # 2. Extract Course Overview
    overview_match = re.search(
        r"##\s*Course Overview\s*\n+(.*?)(?=\n+---\s*\n+|\n+##\s*Topic-by-Topic|\Z)",
        content,
        re.DOTALL,
    )
    overview = overview_match.group(1).strip() if overview_match else ""

    # 3. Extract Mermaid Diagram syntax
    mermaid_match = re.search(r"```mermaid\s*\n(.*?)```", content, re.DOTALL)
    mermaid_code = mermaid_match.group(1).strip() if mermaid_match else ""

    # 4. Extract Topic Modules
    topic_section_match = re.search(
        r"##\s*Topic-by-Topic Course Summary\s*\n+(.*?)(?=\n+##\s*Concept|\Z)",
        content,
        re.DOTALL,
    )
    topics: List[Dict[str, Any]] = []

    if topic_section_match:
        topic_section = topic_section_match.group(1)
        raw_topics = re.findall(
            r"###\s*([^\n]+)\n+(.*?)(?=\n+###|\Z)",
            topic_section,
            re.DOTALL,
        )
        for t_heading, t_body in raw_topics:
            t_heading = t_heading.strip()
            t_body = re.sub(r"\n+---\s*$", "", t_body.strip()).strip()
            num_match = re.match(r"^(\d+)[\.\)]?\s*(.*)$", t_heading)
            if num_match:
                topic_num = num_match.group(1)
                topic_name = num_match.group(2)
            else:
                topic_num = str(len(topics) + 1)
                topic_name = t_heading


            mech_m = re.search(
                r"\*\*Overview & Mechanisms:\*\*\s*\n*(.*?)(?=\n*\*\*Key Definitions|\n*\*\*Practical|\Z)",
                t_body,
                re.DOTALL,
            )
            defs_m = re.search(
                r"\*\*Key Definitions & Principles:\*\*\s*\n*(.*?)(?=\n*\*\*Practical|\Z)",
                t_body,
                re.DOTALL,
            )
            prac_m = re.search(
                r"\*\*Practical Implications(?:\s*&\s*Applications)?:\*\*\s*\n*(.*?)(?=\Z)",
                t_body,
                re.DOTALL,
            )

            topics.append(
                {
                    "number": topic_num,
                    "name": topic_name,
                    "raw_content": t_body.strip(),
                    "mechanisms": mech_m.group(1).strip() if mech_m else "",
                    "definitions": defs_m.group(1).strip() if defs_m else "",
                    "practical": prac_m.group(1).strip() if prac_m else "",
                }
            )

    return {
        "title": title,
        "overview": overview,
        "topics": topics,
        "mermaid": mermaid_code,
        "markdown": content,
    }


def create_app() -> Flask:
    """Create and configure the Flask web application."""
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "src" / "templates"),
        static_folder=str(PROJECT_ROOT / "src" / "static"),
    )

    # Max upload size: 50 MB
    app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
    app.config["TEMPLATES_AUTO_RELOAD"] = True
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    @app.after_request
    def add_header(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    uploads_dir = DATA_DIR / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    @app.route("/")
    def index():
        """Render the main Course Recap Generator user interface."""
        return render_template("index.html")

    @app.route("/api/health", methods=["GET"])
    def health():
        """System health and configuration check."""
        has_key = False
        try:
            get_gemini_api_key()
            has_key = True
        except ValueError:
            has_key = False

        return jsonify(
            {
                "status": "ok",
                "api_key_configured": has_key,
                "default_model": DEFAULT_MODEL,
            }
        )

    @app.route("/api/history", methods=["GET"])
    def get_history():
        """Return a list of previously generated recaps from the outputs directory."""
        recaps = []
        if OUTPUTS_DIR.exists():
            for file_path in sorted(
                OUTPUTS_DIR.glob("*_Recap.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            ):
                stat = file_path.stat()
                # Read first line for title
                title = file_path.stem
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        first_line = f.readline()
                        m = re.match(r"^#\s*(.*?)(?:\s*-\s*Comprehensive.*)?$", first_line)
                        if m and m.group(1).strip():
                            title = m.group(1).strip()
                except Exception:
                    pass

                recaps.append(
                    {
                        "filename": file_path.name,
                        "title": title,
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                )
        return jsonify({"recaps": recaps})

    @app.route("/api/recap/<filename>", methods=["GET"])
    def load_recap(filename: str):
        """Retrieve and parse a previously generated recap file."""
        safe_name = secure_filename(filename)
        file_path = OUTPUTS_DIR / safe_name
        if not file_path.exists() or not file_path.is_file():
            return jsonify({"success": False, "error": f"Recap not found: {safe_name}"}), 404

        try:
            content = file_path.read_text(encoding="utf-8")
            parsed = parse_recap_markdown(content, fallback_title=file_path.stem)
            return jsonify(
                {
                    "success": True,
                    "filename": safe_name,
                    "output_filename": safe_name,
                    "title": parsed["title"],
                    "overview": parsed["overview"],
                    "topics": parsed["topics"],
                    "mermaid": parsed["mermaid"],
                    "markdown": parsed["markdown"],
                    "stats": {
                        "characters": len(content),
                        "topics_count": len(parsed["topics"]),
                        "has_diagram": bool(parsed["mermaid"]),
                    },
                }
            )
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/generate", methods=["POST"])
    def generate():
        """Generate a course recap from one or more uploaded course files."""
        # Support both 'files' and 'file' field keys
        uploaded_files = request.files.getlist("files")
        if not uploaded_files or not any(f.filename for f in uploaded_files):
            uploaded_files = request.files.getlist("file")

        valid_files = [f for f in uploaded_files if f and f.filename and f.filename.strip()]
        if not valid_files:
            return jsonify({"success": False, "error": "No course file(s) uploaded."}), 400

        saved_files: List[Tuple[str, Path]] = []

        for idx, uploaded_file in enumerate(valid_files):
            original_name = uploaded_file.filename
            if not original_name.lower().endswith((".pdf", ".pptx", ".ppt")):
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": f"Invalid format for '{original_name}'. Please upload course documents (.pdf).",
                        }
                    ),
                    400,
                )

            safe_name = secure_filename(original_name)
            if not safe_name:
                safe_name = f"course_doc_{idx + 1}.pdf"

            saved_path = uploads_dir / safe_name
            if saved_path.exists() and safe_name in [p.name for _, p in saved_files]:
                stem = saved_path.stem
                suffix = saved_path.suffix
                saved_path = uploads_dir / f"{stem}_{idx + 1}{suffix}"

            uploaded_file.save(str(saved_path))
            saved_files.append((original_name, saved_path))

        model = request.form.get("model", DEFAULT_MODEL)

        try:
            # Process EACH uploaded file independently through the existing pipeline
            recaps: List[Dict[str, Any]] = []

            for original_name, saved_path in saved_files:
                output_file, recap_markdown = generate_course_recap(
                    pdf_path=saved_path,
                    model=model,
                )

                fallback_title = output_file.stem.replace("_recap", "").replace("_Recap", "")
                parsed = parse_recap_markdown(
                    recap_markdown,
                    fallback_title=fallback_title,
                )

                recaps.append(
                    {
                        "success": True,
                        "filename": original_name,
                        "output_filename": output_file.name,
                        "title": parsed["title"],
                        "overview": parsed["overview"],
                        "topics": parsed["topics"],
                        "mermaid": parsed["mermaid"],
                        "markdown": recap_markdown,
                        "stats": {
                            "characters": len(recap_markdown),
                            "topics_count": len(parsed["topics"]),
                            "has_diagram": bool(parsed["mermaid"]),
                        },
                    }
                )

            first_recap = recaps[0]
            return jsonify(
                {
                    "success": True,
                    "count": len(recaps),
                    "files_count": len(recaps),
                    "recaps": recaps,
                    "filename": first_recap["filename"],
                    "filenames": [r["filename"] for r in recaps],
                    "output_filename": first_recap["output_filename"],
                    "title": first_recap["title"],
                    "overview": first_recap["overview"],
                    "topics": first_recap["topics"],
                    "mermaid": first_recap["mermaid"],
                    "markdown": first_recap["markdown"],
                    "stats": first_recap["stats"],
                }
            )
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/download/<filename>", methods=["GET"])
    def download_file(filename: str):
        """Download a generated recap Markdown file."""
        safe_name = secure_filename(filename)
        target = OUTPUTS_DIR / safe_name
        if not target.exists():
            return jsonify({"error": f"File not found: {safe_name}"}), 404
        return send_from_directory(
            str(OUTPUTS_DIR),
            safe_name,
            as_attachment=True,
            mimetype="text/markdown",
        )

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=True)
