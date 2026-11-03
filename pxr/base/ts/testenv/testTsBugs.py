#!/pxrpythonsubst

#
# Copyright 2025 Pixar
#
# Licensed under the terms set forth in the LICENSE.txt file available at
# https://openusd.org/license.
#

from pxr import Gf, Ts

import unittest

class TestBugs(unittest.TestCase):
    def testUSD_12830(self):
        # A bounded clip beyond either end must preserve linear extrapolation.
        spline = Ts.Spline('double')
        for time in (0.0, 10.0):
            knot = Ts.Knot('double')
            knot.SetTime(time)
            knot.SetValue(time)
            knot.SetNextInterpolation(Ts.InterpLinear)
            spline.SetKnot(knot)
        linear = Ts.Extrapolation(Ts.ExtrapLinear)
        spline.SetPreExtrapolation(linear)
        spline.SetPostExtrapolation(linear)
        block = Ts.Extrapolation(Ts.ExtrapValueBlock)

        for lo, hi, times in (
            (5.0, 20.0, (6.0, 15.0, 18.0)),  # crosses last knot
            (12.0, 20.0, (13.0, 15.0, 18.0)), # beyond last knot
            (-20.0, -12.0, (-18.0, -15.0, -13.0)), # before first knot
        ):
            with self.subTest(interval=(lo, hi)):
                truncated = spline.GetTruncated(
                    Gf.Interval(lo, hi), block, block)
                for time in times:
                    self.assertAlmostEqual(spline.Eval(time), time)
                    self.assertAlmostEqual(truncated.Eval(time), time)
                    self.assertAlmostEqual(truncated.EvalDerivative(time), 1.0)
                self.assertIsNone(truncated.Eval(lo - 1.0))
                self.assertIsNone(truncated.Eval(hi + 1.0))

    def testUSD_11046(self):
        """
        An uninitialized read was leading to the possibility that we could read
        past the end of a vector producing random values in the last sample
        point returned by TsSpline::Sample
        """
        spline = Ts.Spline('float')
        spline.SetKnot(Ts.Knot('float', time=  1, value=0.000,
                               nextInterp=Ts.InterpCurve))
        spline.SetKnot(Ts.Knot('float', time=200, value=0.001))

        samples = spline.Sample(Gf.Interval(0, 192), 1, 1, 0.5)

        print(spline)
        print(samples.polylines)

        polyline = samples.polylines[0]

        self.assertTrue(Gf.IsClose(polyline[2],
                                   Gf.Vec2d(192.0, 0.0009597990405628804),
                                   1.0e-10))

if __name__ == '__main__':
    # 'buffer' means that all stdout will be captured and swallowed, unless
    # there is an error, in which case the stdout of the erroring case will be
    # printed on stderr along with the test results.  Suppressing the output of
    # passing cases makes it easier to find the output of failing ones.
    unittest.main(testRunner = unittest.TextTestRunner(buffer = True))
