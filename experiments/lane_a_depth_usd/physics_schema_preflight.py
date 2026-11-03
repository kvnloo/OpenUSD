"""Narrow, fixture-specific USD Physics metadata preflight.

This is not a general USD reader. A real OpenUSD parser must separately parse
stages and a downstream physics engine must separately validate runtime effects.
It guards the three authored physics prims in the Lane A synthetic scene against
metadata typos the C++ USD parser accepts without enforcing USD Physics semantics.
"""
from __future__ import annotations

import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
PRIMS = {
    "CollisionSlab": {"type": "Mesh", "apis": {"PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"},
                      "attributes": {"physics:collisionEnabled": "PhysicsCollisionAPI",
                                     "physics:approximation": "PhysicsMeshCollisionAPI"}},
    "DropSphere": {"type": "Sphere", "apis": {"PhysicsRigidBodyAPI", "PhysicsCollisionAPI", "PhysicsMassAPI"},
                   "attributes": {"physics:rigidBodyEnabled": "PhysicsRigidBodyAPI",
                                  "physics:collisionEnabled": "PhysicsCollisionAPI",
                                  "physics:mass": "PhysicsMassAPI"}},
    "PhysicsWorld": {"type": "PhysicsScene", "apis": set(),
                     "attributes": {"physics:gravityDirection": "PhysicsScene",
                                    "physics:gravityMagnitude": "PhysicsScene"}},
}
ATTR_RE = re.compile(r'^\s*((?:uniform\s+)?\w+)\s+(physics:\w+)\s*=\s*([^\n]*)$', re.M)


class PhysicsFixtureError(ValueError):
    """The targeted fixture's authored USD Physics contract is inconsistent."""


def _prim(source: str, type_name: str, name: str) -> tuple[str, str]:
    match = re.search(r'\bdef\s+' + re.escape(type_name) + r'\s+"' + re.escape(name) + r'"', source)
    if match is None:
        raise PhysicsFixtureError(f"missing prim {name} ({type_name})")
    opening = source.find("{", match.end())
    if opening < 0:
        raise PhysicsFixtureError(f"missing prim body {name}")
    header = source[match.end():opening]
    depth = 1
    pos = opening + 1
    while pos < len(source) and depth:
        depth += (source[pos] == "{") - (source[pos] == "}")
        pos += 1
    if depth:
        raise PhysicsFixtureError(f"unclosed prim {name}")
    return header, source[opening + 1:pos - 1]


def _direct_prim_body(body: str) -> str:
    """Exclude descendants: their authored properties do not belong to a parent."""
    depth = 0
    quoted = False
    escaped = False
    commented = False
    direct = []
    for char in body:
        if char == "\n":
            direct.append("\n")
            commented = False
            escaped = False
            continue
        if commented:
            direct.append(" ")
            continue
        if char == '"' and not escaped:
            quoted = not quoted
        if char == "#" and not quoted:
            commented = True
            direct.append(" ")
            continue
        if not quoted and char in "{}":
            depth += 1 if char == "{" else -1
            if depth < 0:
                raise PhysicsFixtureError("unexpected closing brace in prim")
            direct.append(" ")
            continue
        direct.append(char if depth == 0 else " ")
        escaped = quoted and char == "\\" and not escaped
    if depth:
        raise PhysicsFixtureError("unclosed nested prim body")
    return "".join(direct)


def validate_fixture(source: str, contract: dict) -> dict:
    """Validate only our three known authored physics prims against a pinned schema."""
    if not contract.get("source", {}).get("sha256"):
        raise PhysicsFixtureError("contract lacks source provenance")
    schemas = contract["schemas"]
    for name, spec in PRIMS.items():
        header, body = _prim(source, spec["type"], name)
        schemas_text = re.search(r'apiSchemas\s*=\s*\[([^]]*)\]', header)
        applied = set(re.findall(r'"([A-Za-z_][\w]*)"', schemas_text.group(1))) if schemas_text else set()
        if applied != spec["apis"]:
            raise PhysicsFixtureError(f"{name}: expected applied APIs {sorted(spec['apis'])}; got {sorted(applied)}")
        actual = {}
        for attr_type, key, value in ATTR_RE.findall(_direct_prim_body(body)):
            if key in actual:
                raise PhysicsFixtureError(f"{name}: duplicated {key}")
            actual[key] = (attr_type, value.strip())
        for attr, schema in spec["attributes"].items():
            if attr not in actual:
                raise PhysicsFixtureError(f"{name}: missing {attr}")
            attr_type, value = actual[attr]
            expected = schemas[schema]["attributes"][attr]
            if attr_type != expected:
                raise PhysicsFixtureError(f"{name}.{attr}: expected type {expected}, got {attr_type}")
            valid = schemas[schema].get("allowed_values", {}).get(attr)
            if valid is not None and value.strip('"') not in valid:
                raise PhysicsFixtureError(f"{name}.{attr}: unsupported token {value}")
    return {"classification": "source-level fixture metadata preflight only",
            "prims": sorted(PRIMS), "schema_sha256": contract["source"]["sha256"]}


def main() -> None:
    import argparse
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("scene", type=Path)
    cli.add_argument("--contract", type=Path, default=HERE / "usd_physics_contract.json")
    args = cli.parse_args()
    print(json.dumps(validate_fixture(args.scene.read_text(), json.loads(args.contract.read_text())), indent=2))


if __name__ == "__main__":
    main()
