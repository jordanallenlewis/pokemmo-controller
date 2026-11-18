"""A small JSON Schema checker (standard library only) for the subset the spec/schema files use:
type, const, enum, required, properties, additionalProperties, items, minItems, maxItems,
uniqueItems, minimum, maximum, maxLength, pattern, oneOf and a relative $ref."""
import json, re
from pathlib import Path


def _type_ok(v, t):
    return {"object": isinstance(v, dict), "array": isinstance(v, list), "string": isinstance(v, str),
            "boolean": isinstance(v, bool), "null": v is None,
            "integer": isinstance(v, int) and not isinstance(v, bool),
            "number": isinstance(v, (int, float)) and not isinstance(v, bool)}[t]


def errors(value, schema, base: Path, path="$"):
    if "$ref" in schema:
        return errors(value, json.loads((base / schema["$ref"]).read_text(encoding="utf-8")), base, path)
    out = []
    if "type" in schema and not _type_ok(value, schema["type"]):
        return [f"{path}: expected {schema['type']}"]
    if "const" in schema and value != schema["const"]:
        out.append(f"{path}: must be {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path}: {value!r} is not one of the allowed values")
    if "oneOf" in schema:
        ok = [s for s in schema["oneOf"] if not errors(value, s, base, path)]
        if len(ok) != 1:
            out.append(f"{path}: matches {len(ok)} of the allowed shapes, expected exactly 1")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        pass
    else:
        if "minimum" in schema and value < schema["minimum"]:
            out.append(f"{path}: below {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            out.append(f"{path}: above {schema['maximum']}")
    if isinstance(value, str):
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            out.append(f"{path}: longer than {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            out.append(f"{path}: does not match {schema['pattern']}")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            out.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") and len({json.dumps(i, sort_keys=True) for i in value}) != len(value):
            out.append(f"{path}: items are not unique")
        for i, item in enumerate(value):
            if "items" in schema:
                out += errors(item, schema["items"], base, f"{path}[{i}]")
    if isinstance(value, dict):
        for k in schema.get("required", []):
            if k not in value:
                out.append(f"{path}: missing {k!r}")
        props = schema.get("properties", {})
        for k, v in value.items():
            if k in props:
                out += errors(v, props[k], base, f"{path}.{k}")
            elif schema.get("additionalProperties") is False:
                out.append(f"{path}: unknown key {k!r}")
            elif isinstance(schema.get("additionalProperties"), dict):
                out += errors(v, schema["additionalProperties"], base, f"{path}.{k}")
    return out
