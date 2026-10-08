"""Entry point for the Course Recap Generator web application."""

import os
import sys
from src.app import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "1").lower() in ("1", "true", "yes")
    print("=" * 60)
    print(" Course Recap Generator - Web Interface")
    print(f" URL: http://127.0.0.1:{port}")
    print(f" Auto-Reload / Debug: {'Enabled' if debug else 'Disabled'}")
    print("=" * 60)
    app.run(host="127.0.0.1", port=port, debug=debug)
