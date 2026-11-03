#!/pxrpythonsubst
#
# Copyright 2020 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.

from pxr import Gf, Vt, Usd, UsdGeom
import unittest

class TestUsdGeomExtentFromPlugins(unittest.TestCase):
    primpaths = [ '/capsule', '/capsule_1', '/cone', '/cube', '/cylinder', '/sphere' ]

    def test_Default(self):
        extents = {
            '/capsule' :  Vt.Vec3fArray(2, (Gf.Vec3f(-2.0, -2.0, -3.0),
                                            Gf.Vec3f(2.0, 2.0, 3.0))),
            '/capsule_1': Vt.Vec3fArray(2, (Gf.Vec3f(-8.75, -8.75, -18.0),
                                             Gf.Vec3f(8.75, 8.75, 4.5))),
            '/cone' :     Vt.Vec3fArray(2, (Gf.Vec3f(-2.0, -2.0, -2.0),
                                            Gf.Vec3f(2.0, 2.0, 2.0))),
            '/cube' :     Vt.Vec3fArray(2, (Gf.Vec3f(-2.0, -2.0, -2.0),
                                            Gf.Vec3f(2.0, 2.0, 2.0))),
            '/cylinder' : Vt.Vec3fArray(2, (Gf.Vec3f(-2.0, -2.0, -2.0),
                                            Gf.Vec3f(2.0, 2.0, 2.0))),
            '/sphere' :   Vt.Vec3fArray(2, (Gf.Vec3f(-2.0, -2.0, -2.0),
                                            Gf.Vec3f(2.0, 2.0, 2.0)))
        }
        testFile = "test.usda"
        s = Usd.Stage.Open(testFile)
        for primpath in self.primpaths:
            p = s.GetPrimAtPath(primpath)
            b = UsdGeom.Boundable(p)
            tc = Usd.TimeCode.Default()
            e = UsdGeom.Boundable.ComputeExtentFromPlugins(b, tc)
            self.assertEqual(extents[primpath], e)

    def test_PointsConstantWidths(self):
        stage = Usd.Stage.CreateInMemory()

        constantPoints = UsdGeom.Points.Define(stage, "/constant")
        self.assertTrue(constantPoints.GetPointsAttr().Set(
            [(0, 0, 0), (10, 0, 0)]))
        self.assertTrue(constantPoints.GetWidthsAttr().Set([5]))
        self.assertTrue(constantPoints.SetWidthsInterpolation(
            UsdGeom.Tokens.constant))

        vertexPoints = UsdGeom.Points.Define(stage, "/vertex")
        self.assertTrue(vertexPoints.GetPointsAttr().Set(
            [(0, 0, 0), (10, 0, 0)]))
        self.assertTrue(vertexPoints.GetWidthsAttr().Set([5, 5]))
        self.assertTrue(vertexPoints.SetWidthsInterpolation(
            UsdGeom.Tokens.vertex))

        expected = Vt.Vec3fArray(
            [Gf.Vec3f(-2.5, -2.5, -2.5),
             Gf.Vec3f(12.5, 2.5, 2.5)])

        constantExtent = UsdGeom.Boundable(
            constantPoints.GetPrim()).ComputeExtent(Usd.TimeCode.Default())
        vertexExtent = UsdGeom.Boundable(
            vertexPoints.GetPrim()).ComputeExtent(Usd.TimeCode.Default())

        self.assertEqual(constantExtent, expected)
        self.assertEqual(constantExtent, vertexExtent)

    def test_PointsConstantWidthsWithTransform(self):
        stage = Usd.Stage.CreateInMemory()
        transform = Gf.Matrix4d(1.0)
        transform.SetTranslate(Gf.Vec3d(3.0, -4.0, 2.0))
        expected = Vt.Vec3fArray([
            Gf.Vec3f(0.5, -6.5, -0.5),
            Gf.Vec3f(15.5, -1.5, 4.5)])

        for name, interpolation, widths in (
                ("constant", UsdGeom.Tokens.constant, [5]),
                ("vertex", UsdGeom.Tokens.vertex, [5, 5])):
            with self.subTest(interpolation=name):
                points = UsdGeom.Points.Define(stage, "/" + name)
                self.assertTrue(points.GetPointsAttr().Set(
                    [(0, 0, 0), (10, 0, 0)]))
                self.assertTrue(points.GetWidthsAttr().Set(widths))
                self.assertTrue(points.SetWidthsInterpolation(interpolation))
                boundable = UsdGeom.Boundable(points.GetPrim())
                extent = UsdGeom.Boundable.ComputeExtentFromPlugins(
                    boundable, Usd.TimeCode.Default(), transform)
                self.assertEqual(extent, expected)

    def test_PointsInvalidWidthsCardinality(self):
        stage = Usd.Stage.CreateInMemory()
        cases = (
            (UsdGeom.Tokens.constant, Vt.FloatArray(0)),
            (UsdGeom.Tokens.constant, [5, 5]),
            (UsdGeom.Tokens.vertex, [5]),
        )
        for i, (interpolation, widths) in enumerate(cases):
            with self.subTest(interpolation=interpolation, widths=widths):
                points = UsdGeom.Points.Define(stage, "/invalid%d" % i)
                self.assertTrue(points.GetPointsAttr().Set(
                    [(0, 0, 0), (10, 0, 0)]))
                self.assertTrue(points.GetWidthsAttr().Set(widths))
                self.assertTrue(points.SetWidthsInterpolation(interpolation))
                self.assertIsNone(UsdGeom.Boundable(
                    points.GetPrim()).ComputeExtent(Usd.TimeCode.Default()))

    def test_PointsEmptyConstantWidths(self):
        # A single constant width cannot describe an empty point set.
        # Before constant-width support, this mismatched cardinality failed.
        stage = Usd.Stage.CreateInMemory()
        points = UsdGeom.Points.Define(stage, "/emptyConstant")
        self.assertTrue(points.GetPointsAttr().Set(Vt.Vec3fArray(0)))
        self.assertTrue(points.GetWidthsAttr().Set([5.0]))
        self.assertTrue(points.SetWidthsInterpolation(
            UsdGeom.Tokens.constant))

        boundable = UsdGeom.Boundable(points.GetPrim())
        self.assertIsNone(boundable.ComputeExtent(Usd.TimeCode.Default()))

        transform = Gf.Matrix4d(1.0)
        transform.SetScale(Gf.Vec3d(2.0, 3.0, 4.0))
        self.assertIsNone(UsdGeom.Boundable.ComputeExtentFromPlugins(
            boundable, Usd.TimeCode.Default(), transform))

    def test_PointsConstantWidthsTimeSamples(self):
        stage = Usd.Stage.CreateInMemory()
        points = UsdGeom.Points.Define(stage, "/timeSampledPoints")
        self.assertTrue(points.GetPointsAttr().Set(
            [(0, 0, 0), (10, 0, 0)]))
        self.assertTrue(points.SetWidthsInterpolation(UsdGeom.Tokens.constant))
        self.assertTrue(points.GetWidthsAttr().Set([2], Usd.TimeCode(1)))
        self.assertTrue(points.GetWidthsAttr().Set([6], Usd.TimeCode(2)))
        boundable = UsdGeom.Boundable(points.GetPrim())
        self.assertEqual(boundable.ComputeExtent(Usd.TimeCode(1)),
                         Vt.Vec3fArray([Gf.Vec3f(-1, -1, -1),
                                        Gf.Vec3f(11, 1, 1)]))
        self.assertEqual(boundable.ComputeExtent(Usd.TimeCode(2)),
                         Vt.Vec3fArray([Gf.Vec3f(-3, -3, -3),
                                        Gf.Vec3f(13, 3, 3)]))

    def test_TimeSampled(self):
        extents = {
            '/capsule' :  Vt.Vec3fArray(2, (Gf.Vec3f(-4.0, -4.0, -6.0),
                                            Gf.Vec3f(4.0, 4.0, 6.0))),
            '/capsule_1': Vt.Vec3fArray(2, (Gf.Vec3f(-7.5, -7.5, -14.0),
                                             Gf.Vec3f(7.5, 7.5, 3.5))),
            '/cone' :     Vt.Vec3fArray(2, (Gf.Vec3f(-4.0, -4.0, -3.0),
                                            Gf.Vec3f(4.0, 4.0, 3.0))),
            '/cube' :     Vt.Vec3fArray(2, (Gf.Vec3f(-3.0, -3.0, -3.0),
                                            Gf.Vec3f(3.0, 3.0, 3.0))),
            '/cylinder' : Vt.Vec3fArray(2, (Gf.Vec3f(-4.0, -4.0, -3.0),
                                            Gf.Vec3f(4.0, 4.0, 3.0))),
            '/sphere' :   Vt.Vec3fArray(2, (Gf.Vec3f(-4.0, -4.0, -4.0),
                                            Gf.Vec3f(4.0, 4.0, 4.0)))
        }
        testFile = "test.usda"
        s = Usd.Stage.Open(testFile)
        for primpath in self.primpaths:
            p = s.GetPrimAtPath(primpath)
            b = UsdGeom.Boundable(p)
            tc = Usd.TimeCode(2.0)
            e = UsdGeom.Boundable.ComputeExtentFromPlugins(b, tc)
            self.assertEqual(extents[primpath], e)

    def test_ComputeExtentAndExtentFromPlugin(self):
        authoredExtentOnSphere = Vt.Vec3fArray(2, (Gf.Vec3f(-10.0, -10.0, -10.0),
                                            Gf.Vec3f(10.0, 10.0, 10.0)))
        explicitlyComputedExtent = Vt.Vec3fArray(2, (Gf.Vec3f(-2.0, -2.0, -2.0),
                                            Gf.Vec3f(2.0, 2.0, 2.0)))
        testFile = "test.usda"
        primPath = "/AuthoredExtentSphere"
        stage = Usd.Stage.Open(testFile)
        prim = stage.GetPrimAtPath(primPath)
        boundable = UsdGeom.Boundable(prim)
        tc = Usd.TimeCode.Default()
        extent1 = boundable.ComputeExtent(tc)
        self.assertEqual(extent1, authoredExtentOnSphere)
        extent2 = UsdGeom.Boundable.ComputeExtentFromPlugins(boundable, tc)
        self.assertEqual(extent2, explicitlyComputedExtent)

        # ComputeExtent uses geomtric properties instead of fallback extent when
        # no extent is authored
        primPath = "/sphere"
        prim = stage.GetPrimAtPath(primPath)
        boundable = UsdGeom.Boundable(prim)
        tc = Usd.TimeCode.Default()
        extent = boundable.ComputeExtent(tc)
        self.assertEqual(extent, explicitlyComputedExtent)


if __name__ == "__main__":
    unittest.main()
