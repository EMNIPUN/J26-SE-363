import json
from pathlib import Path

import pytest

from shared.performance.contracts import SCHEMA_NAMES, load_schema, schema_path


EXPECTED_SCHEMA_IDS = {name: f"https://selvia.dev/schemas/performance/{name}/" for name in SCHEMA_NAMES}


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_performance_contract_is_a_versioned_json_schema(name):
    path = schema_path(name)
    assert path.is_file()
    assert path.suffix == ".json"

    schema = load_schema(name)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["$id"].startswith(EXPECTED_SCHEMA_IDS[name])
    assert schema["type"] == "object"
    assert schema["required"]
    assert schema["properties"]["schema"]["const"] == schema["$id"].rsplit("/", 2)[-2] + "/" + schema["$id"].rsplit("/", 1)[-1]


def test_performance_contract_files_are_valid_json():
    for name in SCHEMA_NAMES:
        with Path(schema_path(name)).open(encoding="utf-8") as schema_file:
            assert isinstance(json.load(schema_file), dict)
