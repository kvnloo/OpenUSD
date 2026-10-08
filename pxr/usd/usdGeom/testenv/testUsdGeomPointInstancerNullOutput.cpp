//
// Copyright 2026
//
// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//

#include "pxr/pxr.h"
#include "pxr/base/tf/diagnostic.h"
#include "pxr/base/tf/errorMark.h"
#include "pxr/usd/usd/stage.h"
#include "pxr/usd/usdGeom/pointInstancer.h"

PXR_NAMESPACE_USING_DIRECTIVE

int
main()
{
    UsdStageRefPtr stage = UsdStage::CreateInMemory();
    UsdGeomPointInstancer instancer =
        UsdGeomPointInstancer::Define(stage, SdfPath("/Instancer"));

    TF_AXIOM(instancer);
    TF_AXIOM(instancer.GetProtoIndicesAttr().Set(VtIntArray()));
    TF_AXIOM(instancer.GetPositionsAttr().Set(VtVec3fArray()));

    {
        TfErrorMark mark;
        TF_AXIOM(!instancer.ComputeInstanceTransformsAtTime(
            nullptr,
            UsdTimeCode::Default(),
            UsdTimeCode::Default(),
            UsdGeomPointInstancer::ExcludeProtoXform,
            UsdGeomPointInstancer::IgnoreMask));
        TF_AXIOM(!mark.IsClean());
        mark.Clear();
    }

    {
        TfErrorMark mark;
        TF_AXIOM(!instancer.ComputeInstanceTransformsAtTimes(
            nullptr,
            {UsdTimeCode::Default()},
            UsdTimeCode::Default(),
            UsdGeomPointInstancer::ExcludeProtoXform,
            UsdGeomPointInstancer::IgnoreMask));
        TF_AXIOM(!mark.IsClean());
        mark.Clear();
    }

    return 0;
}
