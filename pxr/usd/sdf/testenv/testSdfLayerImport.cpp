// Licensed under the terms set forth in the LICENSE.txt file available at
// https://openusd.org/license.
//

#include "pxr/pxr.h"

#include "pxr/usd/sdf/layer.h"
#include "pxr/usd/sdf/primSpec.h"

#include "pxr/base/arch/fileSystem.h"
#include "pxr/base/tf/diagnostic.h"
#include "pxr/base/tf/errorMark.h"

#include <string>

PXR_NAMESPACE_USING_DIRECTIVE

static void
_TestReadOnlyCrossFormatImport(
    const std::string& destinationExtension,
    const std::string& sourceExtension)
{
    const std::string sourcePath = ArchMakeTmpFileName(
        "testSdfLayerImport_source_", sourceExtension);
    SdfLayerRefPtr sourceLayer = SdfLayer::CreateNew(sourcePath);
    TF_AXIOM(sourceLayer);
    sourceLayer->SetComment("source");
    TF_AXIOM(SdfCreatePrimInLayer(sourceLayer, SdfPath("/ImportedRoot")));
    TF_AXIOM(sourceLayer->Save());

    const std::string destinationPath = ArchMakeTmpFileName(
        "testSdfLayerImport_destination_", destinationExtension);
    SdfLayerRefPtr destinationLayer = SdfLayer::CreateNew(destinationPath);
    TF_AXIOM(destinationLayer);
    destinationLayer->SetComment("destination");
    TF_AXIOM(destinationLayer->Save());

    const std::string originalIdentifier = destinationLayer->GetIdentifier();
    const SdfFileFormatConstPtr originalFormat = destinationLayer->GetFileFormat();
    std::string originalContent;
    TF_AXIOM(destinationLayer->ExportToString(&originalContent));

    // TransferContent emits an error and returns void for read-only layers.
    // The C++ Import return value must also be false in that case, without
    // modifying the destination's data, identifier, or format.
    destinationLayer->SetPermissionToEdit(false);
    {
        TfErrorMark mark;
        const bool imported = destinationLayer->Import(sourcePath);
        TF_AXIOM(!imported);
        TF_AXIOM(!mark.IsClean());
        mark.Clear();
    }
    std::string afterRejectedImport;
    TF_AXIOM(destinationLayer->ExportToString(&afterRejectedImport));
    TF_AXIOM(afterRejectedImport == originalContent);
    TF_AXIOM(destinationLayer->GetIdentifier() == originalIdentifier);
    TF_AXIOM(destinationLayer->GetFileFormat() == originalFormat);

    // Permission can be restored and the same cross-format import succeeds.
    destinationLayer->SetPermissionToEdit(true);
    {
        TfErrorMark mark;
        TF_AXIOM(destinationLayer->Import(sourcePath));
        TF_AXIOM(mark.IsClean());
    }
    TF_AXIOM(destinationLayer->GetComment() == "source");
    TF_AXIOM(destinationLayer->GetPrimAtPath(SdfPath("/ImportedRoot")));
    TF_AXIOM(destinationLayer->GetIdentifier() == originalIdentifier);
    TF_AXIOM(destinationLayer->GetFileFormat() == originalFormat);
}

int
main()
{
    _TestReadOnlyCrossFormatImport(".usda", ".usdc");
    _TestReadOnlyCrossFormatImport(".usdc", ".usda");
    return 0;
}
