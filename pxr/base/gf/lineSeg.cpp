//
// Copyright 2016 Pixar
//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//

#include "pxr/pxr.h"
#include "pxr/base/gf/lineSeg.h"
#include "pxr/base/gf/math.h"
#include "pxr/base/gf/ostreamHelpers.h"

#include "pxr/base/tf/type.h"

#include <ostream>

PXR_NAMESPACE_OPEN_SCOPE

// CODE_COVERAGE_OFF_GCOV_BUG
TF_REGISTRY_FUNCTION(TfType) {
    TfType::Define<GfLineSeg>();
}
// CODE_COVERAGE_ON_GCOV_BUG

GfVec3d
GfLineSeg::FindClosestPoint(const GfVec3d &point, double *t) const
{
    // Find the parametric distance, lt, of the closest point on the line 
    // and then clamp lt to be on the line segment.

    double lt;
    if ( _length == 0.0 )
    {
        lt = 0.0;
    }
    else
    {
        _line.FindClosestPoint( point, &lt );

        lt = GfClamp( lt / _length, 0, 1 );
    }

    if ( t )
	*t = lt;

    return GetPoint( lt );
}

bool 
GfFindClosestPoints( const GfLine &line, const GfLineSeg &seg,
		     GfVec3d *p1, GfVec3d *p2,
		     double *t1, double *t2 )
{
    GfVec3d cp1, cp2;
    double lt1, lt2;
    if ( !GfFindClosestPoints( line, seg._line,  &cp1, &cp2, &lt1, &lt2 ) )
	return false;

    lt2 = GfClamp( lt2 / seg._length, 0, 1 );
    cp2 = seg.GetPoint( lt2 );

    // If we clamp the line segment, change the rayPoint to be 
    // the closest point on the ray to the clamped point.
    if (lt2 <= 0 || lt2 >= 1){
        cp1 = line.FindClosestPoint(cp2, &lt1);
    }

    if ( p1 )
	*p1 = cp1;

    if ( p2 )
        *p2 = cp2;

    if ( t1 )
	*t1 = lt1;

    if ( t2 )
	*t2 = lt2;

    return true;
}


bool 
GfFindClosestPoints( const GfLineSeg &seg1, const GfLineSeg &seg2,
		     GfVec3d *p1, GfVec3d *p2,
		     double *t1, double *t2 )
{
    GfVec3d cp1, cp2;
    double lt1, lt2;
    if ( !GfFindClosestPoints( seg1._line, seg2._line,  
			       &cp1, &cp2, &lt1, &lt2 ) )
	return false;

    lt1 = GfClamp( lt1 / seg1._length, 0, 1 );
    lt2 = GfClamp( lt2 / seg2._length, 0, 1 );

    cp1 = seg1.GetPoint(lt1);
    cp2 = seg2.GetPoint(lt2);
    double minDistanceSq = (cp1 - cp2).GetLengthSq();

    // Clamping the two infinite-line parameters independently need not
    // minimize distance between finite segments. A constrained minimum is
    // either interior to both segments or on an endpoint of at least one.
    auto consider = [&](double candidateT1, double candidateT2) {
        const GfVec3d candidate1 = seg1.GetPoint(candidateT1);
        const GfVec3d candidate2 = seg2.GetPoint(candidateT2);
        const double distanceSq = (candidate1 - candidate2).GetLengthSq();
        if (distanceSq < minDistanceSq) {
            minDistanceSq = distanceSq;
            lt1 = candidateT1;
            lt2 = candidateT2;
            cp1 = candidate1;
            cp2 = candidate2;
        }
    };

    for (int endpoint = 0; endpoint != 2; ++endpoint) {
        const double t = static_cast<double>(endpoint);
        double otherT;

        seg2.FindClosestPoint(seg1.GetPoint(t), &otherT);
        consider(t, otherT);

        seg1.FindClosestPoint(seg2.GetPoint(t), &otherT);
        consider(otherT, t);
    }

    if ( p1 )
	*p1 = cp1;

    if ( p2 )
	*p2 = cp2;

    if ( t1 )
	*t1 = lt1;

    if ( t2 )
	*t2 = lt2;

    return true;
}

std::ostream &
operator<<(std::ostream &out, const GfLineSeg &seg)
{
    return out << '(' 
        << "point 1:" << Gf_OstreamHelperP(seg.GetPoint(0.0)) << ' ' 
        << "point 2:" << Gf_OstreamHelperP(seg.GetPoint(1.0)) << ')';
}

PXR_NAMESPACE_CLOSE_SCOPE
