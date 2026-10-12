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
