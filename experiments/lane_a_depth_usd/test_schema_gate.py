"""Synthetic USD physics interchange gate; no renderer or simulator claims.

Run `python -m pytest -q test_schema_gate.py`. For a required OpenUSD gate,
set LANE_A_REQUIRE_PXR=1: missing pxr then fails rather than skips.
"""
import ast
from collections import Counter
import math
import os
from pathlib import Path
import re

import pytest


def make_usda() -> str:
    """Write a calibrated depth grid and a closed, static 5 cm collider."""
    w, h = 8, 6
    f = w / (2.0 * math.tan(math.pi / 6))
    vertices = [((c + 0.5 - w / 2) * 2 / f,
                 -(r + 0.5 - h / 2) * 2 / f, -2.0)
                for r in range(h) for c in range(w)]
    upper = [(r * w + c, (r + 1) * w + c, r * w + c + 1)
             for r in range(h - 1) for c in range(w - 1)]
    upper += [(r * w + c + 1, (r + 1) * w + c, (r + 1) * w + c + 1)
              for r in range(h - 1) for c in range(w - 1)]
    assert len(vertices) == 48 and len(upper) == 70
    shell = vertices + [(x, y, z - 0.05) for x, y, z in vertices]
    n = len(vertices)
    faces = list(upper) + [tuple(i + n for i in t[::-1]) for t in upper]
    border = ([r * w for r in range(h)]
              + [(h - 1) * w + c for c in range(1, w)]
              + [r * w + w - 1 for r in range(h - 2, -1, -1)]
              + [c for c in range(w - 2, 0, -1)])
    for i, j in zip(border, border[1:] + border[:1]):
        faces += [(i, i + n, j), (j, i + n, j + n)]
    assert len(shell) == 96 and len(faces) == 188

    def mesh(name, points, triangles, collider=False):
        p = ", ".join(f"({x:.12g}, {y:.12g}, {z:.12g})" for x, y, z in points)
        f = ", ".join(str(k) for tri in triangles for k in tri)
        api = ' (prepend apiSchemas = ["PhysicsCollisionAPI", "PhysicsMeshCollisionAPI"])' if collider else ""
        meta = ('bool physics:collisionEnabled = true\n'
                'uniform token physics:approximation = "convexHull"\n'
                'uniform token purpose = "guide"\n') if collider else ""
        return (f'def Mesh "{name}"{api} {{\n{meta}'
                f'uniform token subdivisionScheme = "none"\n'
                f'point3f[] points = [{p}]\n'
                f'int[] faceVertexCounts = [{", ".join(["3"] * len(triangles))}]\n'
                f'int[] faceVertexIndices = [{f}]\n}}')

    return f'''#usda 1.0
(
    defaultPrim = "World"
    metersPerUnit = 1
    upAxis = "Y"
)
def Xform "World" {{
  def Xform "Capture" {{
    float xformOp:rotateX = -90
    uniform token[] xformOpOrder = ["xformOp:rotateX"]
    def Camera "Sensor" {{
      token projection = "perspective"
      float focalLength = {0.36 / (2 * math.tan(math.pi / 6)):.12g}
      float horizontalAperture = 0.36
      float verticalAperture = 0.27
      float2 clippingRange = (0.1, 10)
    }}
    {mesh('Reconstruction', vertices, upper)}
    {mesh('CollisionSlab', shell, faces, True)}
  }}
  def Sphere "DropSphere" (prepend apiSchemas = ["PhysicsRigidBodyAPI", "PhysicsCollisionAPI", "PhysicsMassAPI"]) {{
    double radius = 0.1
    double3 xformOp:translate = (0, -1, 0)
    uniform token[] xformOpOrder = ["xformOp:translate"]
    bool physics:rigidBodyEnabled = true
    bool physics:collisionEnabled = true
    float physics:mass = 1
  }}
  def PhysicsScene "PhysicsWorld" {{
    vector3f physics:gravityDirection = (0, -1, 0)
    float physics:gravityMagnitude = 9.81
  }}
}}
'''



def test_closed_collider_has_metric_volume_and_manifold_edges():
    """Reject malformed collider triangles before trusting USD physics APIs."""
    src = make_usda().split('def Mesh "CollisionSlab"', 1)[1]
    vertex_text = re.search(r"point3f\[\] points = \[([^]]*)\]", src)
    index_text = re.search(r"int\[\] faceVertexIndices = \[([^]]*)\]", src)
    assert vertex_text is not None and index_text is not None
    vertices = ast.literal_eval("[" + vertex_text.group(1) + "]")
    indices = ast.literal_eval("[" + index_text.group(1) + "]")
    assert len(vertices) == 96 and len(indices) == 188 * 3
    triangles = list(zip(indices[::3], indices[1::3], indices[2::3]))
    assert all(len(set(face)) == 3 and all(0 <= i < len(vertices) for i in face)
               for face in triangles)
    directed = Counter((a, b) for face in triangles
                       for a, b in zip(face, face[1:] + face[:1]))
    undirected = Counter(tuple(sorted(edge)) for edge in directed.elements())
    assert all(count == 2 for count in undirected.values())
    assert all(directed[(b, a)] == 1 and count == 1
               for (a, b), count in directed.items())
    signed_volume = 0.0
    for a, b, c in triangles:
        x0, y0, z0 = vertices[a]
        x1, y1, z1 = vertices[b]
        x2, y2, z2 = vertices[c]
        signed_volume += (x0 * (y1*z2-y2*z1) + x1 * (y2*z0-y0*z2)
                          + x2 * (y0*z1-y1*z0)) / 6.0
    assert math.isclose(signed_volume, 0.14583333333333334, abs_tol=1e-9)
    assert math.isclose(math.sqrt(2 * (1 - 0.1) / 9.81), 0.4283529368781193,
                        abs_tol=1e-12)


def get_pxr():
    """Refuse silent skips when the CI environment requires the real parser."""
    try:
        from pxr import Gf, Usd, UsdGeom, UsdPhysics
    except ImportError:
        if os.getenv("LANE_A_REQUIRE_PXR") == "1":
            raise
        pytest.skip("OpenUSD pxr is unavailable; no parser claim")
    return Gf, Usd, UsdGeom, UsdPhysics


def test_synthetic_stage_source():
    """Check the generated scene includes the camera, collider, and physics actors."""
    source = make_usda()
    assert 'defaultPrim = "World"' in source
    assert 'def PhysicsScene "PhysicsWorld"' in source
    assert 'PhysicsMeshCollisionAPI' in source
    assert 'def Sphere "DropSphere"' in source


def test_openusd_parse_schemas_and_reference(tmp_path: Path):
    """Use native OpenUSD to parse and reference the entire authored scene."""
    Gf, Usd, UsdGeom, UsdPhysics = get_pxr()
    path = tmp_path / "synthetic_capture.usda"
    path.write_text(make_usda(), encoding="utf-8")
    stage = Usd.Stage.Open(str(path))
    assert stage is not None
    assert str(stage.GetDefaultPrim().GetPath()) == "/World"
    assert math.isclose(UsdGeom.GetStageMetersPerUnit(stage), 1.0)
    assert UsdGeom.GetStageUpAxis(stage) == "Y"
    capture = stage.GetPrimAtPath("/World/Capture")
    rot = UsdGeom.XformCache().GetLocalToWorldTransform(capture)
    assert abs(rot.TransformDir(Gf.Vec3d(0, 0, 1))[1] - 1) < 1e-8
    camera = UsdGeom.Camera.Get(stage, "/World/Capture/Sensor")
    assert camera.GetPrim().IsValid()
    assert math.isclose(camera.GetHorizontalApertureAttr().Get(), 0.36, abs_tol=1e-7)
    collider = stage.GetPrimAtPath("/World/Capture/CollisionSlab")
    assert collider.IsA(UsdGeom.Mesh)
    assert collider.HasAPI(UsdPhysics.CollisionAPI)
    assert collider.HasAPI(UsdPhysics.MeshCollisionAPI)
    assert UsdPhysics.MeshCollisionAPI(collider).GetApproximationAttr().Get() == "convexHull"
    assert not stage.GetPrimAtPath("/World/Capture/Reconstruction").HasAPI(UsdPhysics.CollisionAPI)
    body = stage.GetPrimAtPath("/World/DropSphere")
    assert body.HasAPI(UsdPhysics.RigidBodyAPI)
    assert body.HasAPI(UsdPhysics.MassAPI)
    assert math.isclose(UsdPhysics.MassAPI(body).GetMassAttr().Get(), 1.0)
    scene = UsdPhysics.Scene.Get(stage, "/World/PhysicsWorld")
    assert scene.GetPrim().IsValid()
    assert math.isclose(scene.GetGravityMagnitudeAttr().Get(), 9.81, abs_tol=1e-5)

    ref_stage = Usd.Stage.CreateInMemory()
    instance = ref_stage.DefinePrim("/Instance", "Xform")
    assert instance.GetReferences().AddReference(str(path))
    for name in ("Capture", "DropSphere", "PhysicsWorld"):
        assert ref_stage.GetPrimAtPath(f"/Instance/{name}").IsValid()
