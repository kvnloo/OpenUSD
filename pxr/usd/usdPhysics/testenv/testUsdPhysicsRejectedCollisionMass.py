#!/pxrpythonsubst
#
# Copyright 2026 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.

import unittest

from pxr import Gf, Usd, UsdGeom, UsdPhysics


class TestUsdPhysicsRejectedCollisionMass(unittest.TestCase):

    @staticmethod
    def _define_body(stage, names):
        body = UsdGeom.Xform.Define(stage, "/Body")
        rigid_body = UsdPhysics.RigidBodyAPI.Apply(body.GetPrim())
        UsdPhysics.MassAPI.Apply(body.GetPrim()).GetDensityAttr().Set(2.0)

        for name in names:
            cube = UsdGeom.Cube.Define(stage, "/Body/" + name)
            cube.GetSizeAttr().Set(1.0)
            UsdPhysics.CollisionAPI.Apply(cube.GetPrim())

        return rigid_body

    @staticmethod
    def _mass_information(prim):
        info = UsdPhysics.RigidBodyAPI.MassInformation()
        if prim.GetName() == "Rejected":
            info.volume = -1.0
            return info

        info.volume = 1.0
        info.inertia = Gf.Matrix3f(1.0 / 6.0)
        info.centerOfMass = Gf.Vec3f(0.0)
        # Give the supported collider a nonzero offset so the test also
        # exercises center-of-mass aggregation, not just scalar mass.
        info.localPos = Gf.Vec3f(2.0, -1.0, 0.5)
        info.localRot = Gf.Quatf(1.0)
        return info

    def test_rejected_colliders_are_not_aggregated(self):
        # A valid collider by itself establishes the expected mass, inertia,
        # and nonzero center of mass. Rejected colliders must not change any
        # of these outputs, regardless of traversal order.
        baseline_stage = Usd.Stage.CreateInMemory()
        baseline_body = self._define_body(baseline_stage, ["Good"])
        baseline_mass, baseline_inertia, baseline_com, _ = (
            baseline_body.ComputeMassProperties(self._mass_information))
        self.assertAlmostEqual(baseline_mass, 2.0)
        self.assertFalse(Gf.IsClose(baseline_com, Gf.Vec3f(0.0), 1e-5))

        for names in (["Good", "Rejected"], ["Rejected", "Good"]):
            with self.subTest(collision_order=names):
                stage = Usd.Stage.CreateInMemory()
                rigid_body = self._define_body(stage, names)
                mass, inertia, com, _ = rigid_body.ComputeMassProperties(
                    self._mass_information)

                self.assertAlmostEqual(mass, baseline_mass)
                self.assertTrue(Gf.IsClose(inertia, baseline_inertia, 1e-5))
                self.assertTrue(Gf.IsClose(com, baseline_com, 1e-5))

    def test_all_rejected_preserves_invalid_mass_sentinel(self):
        stage = Usd.Stage.CreateInMemory()
        rigid_body = self._define_body(stage, ["Rejected"])

        mass, _, _, _ = rigid_body.ComputeMassProperties(
            self._mass_information)

        # No valid collider supplied mass properties. Preserve the existing
        # negative sentinel rather than manufacturing zero or default mass.
        self.assertAlmostEqual(mass, -1.0)


if __name__ == "__main__":
    unittest.main()
