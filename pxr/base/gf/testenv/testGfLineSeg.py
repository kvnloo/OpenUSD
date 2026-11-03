#!/pxrpythonsubst
#
# Copyright 2016 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#
from __future__ import division

import sys
import unittest
import math
from pxr import Gf

def err( msg ):
    return "ERROR: " + msg + " failed"

class TestGfLineSeg(unittest.TestCase):
    
    def test_Constructors(self):
        self.assertIsInstance(Gf.LineSeg(), Gf.LineSeg, err("constructor"))
        self.assertIsInstance(Gf.LineSeg(Gf.Vec3d(), Gf.Vec3d()), Gf.LineSeg, err("constructor"))

    def test_Properties(self):
        l = Gf.LineSeg(Gf.Vec3d(1,2,3), Gf.Vec3d(2,3,4))
        self.assertTrue(l.GetPoint(0) == Gf.Vec3d(1,2,3) and \
            l.direction == (Gf.Vec3d(2,3,4) - Gf.Vec3d(1,2,3)).GetNormalized() and \
            l.length == Gf.GetLength(Gf.Vec3d(2,3,4)-Gf.Vec3d(1,2,3)), \
            err("initializing constructor"))
        
        l = Gf.LineSeg(Gf.Vec3d(0,0,0), Gf.Vec3d(0,1,0))
        self.assertTrue(l.GetPoint(0.5) == Gf.Vec3d(0, 0.5, 0) and \
            l.GetPoint(1.0) == Gf.Vec3d(0, 1, 0), err("GetPoint"))
        
        l = Gf.LineSeg(Gf.Vec3d(1,2,3), Gf.Vec3d(1,1,1))
        self.assertEqual(l.direction, (Gf.Vec3d(1,1,1) - Gf.Vec3d(1,2,3)).GetNormalized(), err("direction"))
        
        l = Gf.LineSeg(Gf.Vec3d(0,0,0), Gf.Vec3d(0,3,4))
        self.assertEqual(l.length, 5, err("length"))
        
    def test_Methods(self):
        l = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        (point, t) = l.FindClosestPoint(Gf.Vec3d(0.5, 0.5, 1))
        self.assertTrue(Gf.IsClose(point, Gf.Vec3d(2./3, 2./3, 2./3), 0.00001), err("FindClosestPoint"))
        self.assertTrue(Gf.IsClose(t, 2./3, 0.0001), err("FindClosestPoint"))

        l = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(0, 0, 0))
        (point, t) = l.FindClosestPoint(Gf.Vec3d(0.5, 0.5, 1))
        self.assertTrue(Gf.IsClose(point, Gf.Vec3d(), 0.00001), err("FindClosestPoint"))
        self.assertTrue(Gf.IsClose(t, 0, 0.0001), err("FindClosestPoint"))

        # seg on seg
        # (parallel case)
        l1 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        l2 = Gf.LineSeg(Gf.Vec3d(1, 0, 0), Gf.Vec3d(2, 1, 1))
        self.assertEqual(Gf.FindClosestPoints(l1, l2)[0], False, err("FindClosestPoints"))

        l1 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        l2 = Gf.LineSeg(Gf.Vec3d(1, 0, 0), Gf.Vec3d(1, -1, 1))
        (intersects, p1, p2, t1, t2) = Gf.FindClosestPoints(l1, l2)
        self.assertTrue(intersects, err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p1, Gf.Vec3d(1./3, 1./3, 1./3), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p2, Gf.Vec3d(1, 0, 0), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(t1, 1./3, 0.00001))
        self.assertTrue(Gf.IsClose(t2, 0, 0.00001))

        l1 = Gf.LineSeg(Gf.Vec3d(), Gf.Vec3d())
        l2 = Gf.LineSeg(Gf.Vec3d(1,1,1), Gf.Vec3d(1,1,1))
        (intersects, p1, p2, t1, t2) = Gf.FindClosestPoints(l1, l2)
        self.assertFalse(intersects, err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p1, Gf.Vec3d(), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p2, Gf.Vec3d(), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(t1, 0, 0.00001))
        self.assertTrue(Gf.IsClose(t2, 0, 0.00001))
        (intersects, p1, p2, t1, t2) = Gf.FindClosestPoints(l2, l1)
        self.assertFalse(intersects, err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p1, Gf.Vec3d(), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p2, Gf.Vec3d(), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(t1, 0, 0.00001))
        self.assertTrue(Gf.IsClose(t2, 0, 0.00001))

        # line on seg
        # (parallel case)
        l1 = Gf.Line(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        l2 = Gf.LineSeg(Gf.Vec3d(1, 0, 0), Gf.Vec3d(2, 1, 1))
        self.assertEqual(Gf.FindClosestPoints(l1, l2)[0], False, err("FindClosestPoints"))

        l1 = Gf.Line(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        l2 = Gf.LineSeg(Gf.Vec3d(1, 0, 0), Gf.Vec3d(1, -1, 1))
        (intersects, p1, p2, t1, t2) = Gf.FindClosestPoints(l1, l2)
        self.assertTrue(intersects, err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p1, Gf.Vec3d(1./3, 1./3, 1./3), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p2, Gf.Vec3d(1, 0, 0), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(t1, 0.57735, 0.00001))
        self.assertTrue(Gf.IsClose(t2, 0, 0.00001))

        l1 = Gf.Line(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        l2 = Gf.LineSeg(Gf.Vec3d(), Gf.Vec3d())
        (intersects, p1, p2, t1, t2) = Gf.FindClosestPoints(l1, l2)
        self.assertFalse(intersects, err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p1, Gf.Vec3d(), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(p2, Gf.Vec3d(), 0.00001), err("FindClosestPoints"))
        self.assertTrue(Gf.IsClose(t1, 0, 0.00001))
        self.assertTrue(Gf.IsClose(t2, 0, 0.00001))
        
    def test_ConstrainedClosestPoints(self):
        # The closest infinite-line intersection lies outside both segments.
        # Clamping both parameters independently returns a nonminimum pair.
        seg1 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(2, 0, 0))
        seg2 = Gf.LineSeg(Gf.Vec3d(-1, -2, 0), Gf.Vec3d(0, -1, 0))
        ok, p1, p2, t1, t2 = Gf.FindClosestPoints(seg1, seg2)
        self.assertTrue(ok)
        self.assertEqual(p1, Gf.Vec3d(0, 0, 0))
        self.assertEqual(p2, Gf.Vec3d(0, -1, 0))
        self.assertAlmostEqual(t1, 0.0)
        self.assertAlmostEqual(t2, 1.0)

        # The answer should not depend on the argument order.
        ok, p2, p1, t2, t1 = Gf.FindClosestPoints(seg2, seg1)
        self.assertTrue(ok)
        self.assertEqual(p1, Gf.Vec3d(0, 0, 0))
        self.assertEqual(p2, Gf.Vec3d(0, -1, 0))
        self.assertAlmostEqual(t1, 0.0)
        self.assertAlmostEqual(t2, 1.0)

        # Keep the unconstrained solution when both parameters are interior.
        seg3 = Gf.LineSeg(Gf.Vec3d(1, -1, 1), Gf.Vec3d(1, 1, 1))
        ok, p1, p3, t1, t3 = Gf.FindClosestPoints(seg1, seg3)
        self.assertTrue(ok)
        self.assertTrue(Gf.IsClose(p1, Gf.Vec3d(1, 0, 0), 1e-8))
        self.assertTrue(Gf.IsClose(p3, Gf.Vec3d(1, 0, 1), 1e-8))
        self.assertAlmostEqual(t1, 0.5)
        self.assertAlmostEqual(t3, 0.5)

        # Preserve the documented false result for parallel segments.
        parallel = Gf.LineSeg(Gf.Vec3d(0, 1, 0), Gf.Vec3d(2, 1, 0))
        self.assertFalse(Gf.FindClosestPoints(seg1, parallel)[0])

    def test_Operators(self):
        l1 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        l2 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        self.assertEqual(l1, l2, err("equality"))

        l1 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 2, 3))
        l2 = Gf.LineSeg(Gf.Vec3d(0, 0, 0), Gf.Vec3d(1, 1, 1))
        self.assertNotEqual(l1, 2, err("inequality"))

        self.assertEqual(l1, eval(repr(l1)), err("repr"))

        self.assertTrue(len(str(Gf.LineSeg())), err("str"))

if __name__ == '__main__':
    unittest.main()
