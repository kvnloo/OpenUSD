"""Guard the USD Physics metadata behind a successful scene parser."""
import json
from pathlib import Path

import pytest

from physics_schema_preflight import PhysicsFixtureError, validate_fixture
from test_schema_gate import make_usda

CONTRACT = json.loads(Path(__file__).with_name('usd_physics_contract.json').read_text())


def test_authored_schema_metadata_matches_pinned_openusd():
    assert validate_fixture(make_usda(), CONTRACT)['schema_sha256'] == '86e189bb4eeb853394faee3612ceccfae19e6e5327be0f89215f3fdb1a60df90'


@pytest.mark.parametrize('old,new,error', [
    ('"PhysicsMeshCollisionAPI"', '"PhysicsMeshCollisonAPI"', 'expected applied APIs'),
    ('bool physics:collisionEnabled = true','float physics:collisionEnabled = 1','expected type bool'),
    ('physics:approximation = "convexHull"', 'physics:approximation = "convexHul"', 'unsupported token'),
    ('"PhysicsRigidBodyAPI"', '"PhysicsRigidBdyAPI"', 'expected applied APIs'),
])
def test_schema_negative_controls(old,new,error):
    source=make_usda()
    assert source.count(old)>=1
    with pytest.raises(PhysicsFixtureError, match=error):
        validate_fixture(source.replace(old,new,1),CONTRACT)

@pytest.mark.parametrize("prim,original,replacement", [
    (
        "CollisionSlab",
        'bool physics:collisionEnabled = true\nuniform token physics:approximation',
        'def Xform "Nested" {\n  bool physics:collisionEnabled = true\n}\nuniform token physics:approximation',
    ),
    (
        "DropSphere",
        '    float physics:mass = 1\n',
        '    def Xform "Nested" {\n      float physics:mass = 1\n    }\n',
    ),
    (
        "PhysicsWorld",
        '    float physics:gravityMagnitude = 9.81\n',
        '    def Xform "Nested" {\n      float physics:gravityMagnitude = 9.81\n    }\n',
    ),
])
def test_descendant_attribute_cannot_satisfy_parent_schema(prim, original, replacement):
    """A nested child must not spoof the parent's required Physics properties."""
    source = make_usda()
    assert source.count(original) == 1
    mutated = source.replace(original, replacement, 1)
    with pytest.raises(PhysicsFixtureError, match=rf"{prim}: missing physics:"):
        validate_fixture(mutated, CONTRACT)

