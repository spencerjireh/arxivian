"""Write the API's OpenAPI document to stdout as sorted JSON.

`just types` runs this inside the backend container and redirects it to
`frontend/openapi.json`, which `openapi-typescript` turns into `frontend/src/types/api.gen.ts`.
CI regenerates both and fails on a diff, so the committed files always match the code.
Needs the same environment as the API (`CLERK_DOMAIN` at least); run as
`uv run python -m scripts.export_openapi` from `backend/`.
"""

import json
import sys


def main() -> None:
    # Importing the app configures structlog against the stdout of that moment; point it at
    # stderr while the app loads so log lines never land in the document.
    real_stdout = sys.stdout
    sys.stdout = sys.stderr
    try:
        from src.main import app
    finally:
        sys.stdout = real_stdout
    real_stdout.write(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
