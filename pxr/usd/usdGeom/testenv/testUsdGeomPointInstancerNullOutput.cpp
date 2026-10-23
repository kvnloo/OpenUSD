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

#include <vector>

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

    // Non-null output pointers still work for a valid empty instancer.
    {
        TfErrorMark mark;
        VtArray<GfMatrix4d> xforms;
        TF_AXIOM(instancer.ComputeInstanceTransformsAtTime(
            &xforms,
            UsdTimeCode::Default(),
            UsdTimeCode::Default(),
            UsdGeomPointInstancer::ExcludeProtoXform,
            UsdGeomPointInstancer::IgnoreMask));
        TF_AXIOM(xforms.empty());

        std::vector<VtArray<GfMatrix4d>> xformsArray;
        TF_AXIOM(instancer.ComputeInstanceTransformsAtTimes(
            &xformsArray,
            {UsdTimeCode::Default()},
            UsdTimeCode::Default(),
            UsdGeomPointInstancer::ExcludeProtoXform,
            UsdGeomPointInstancer::IgnoreMask));
        TF_AXIOM(xformsArray.size() == 1);
        TF_AXIOM(xformsArray[0].empty());
        TF_AXIOM(mark.IsClean());
    }

    {
        TfErrorMark mark;
        TF_AXIOM(!instancer.ComputeInstanceTransformsAtTime(
            nullptr,
            UsdTimeCode::Default(),
            UsdTimeCode::Default(),
            UsdGeomPointInstancer::ExcludeProtoXform,
            UsdGeomPointInstancer::IgnoreMask));
        TF_AXIOM(!mark.IsClean());
        size_t numErrors = 0;
        const auto error = mark.GetBegin(&numErrors);
        TF_AXIOM(numErrors == 1);
        TF_AXIOM(error->GetCommentary() == "'xforms' is null");
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
        size_t numErrors = 0;
        const auto error = mark.GetBegin(&numErrors);
        TF_AXIOM(numErrors == 1);
        TF_AXIOM(error->GetCommentary() == "'xformsArray' is null");
        mark.Clear();
    }

    return 0;
}
