import json
from gateway.main import app
import os

if __name__ == "__main__":
    openapi_schema = app.openapi()

    # Ensure the directory exists
    os.makedirs("docs/api", exist_ok=True)

    with open("docs/api/openapi.json", "w") as f:
        json.dump(openapi_schema, f, indent=2)
    print("Successfully generated docs/api/openapi.json")
