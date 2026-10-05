import json
from pathlib import Path
from jsonschema.validators import Draft202012Validator

ROOT=Path(__file__).resolve().parents[2]

def test_all_json_schemas_are_valid():
    for path in sorted((ROOT/"schemas").glob("*.schema.json")):
        schema=json.loads(path.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
