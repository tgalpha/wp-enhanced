/*******************************************************************************
The content of this file includes portions of the AUDIOKINETIC Wwise Technology
released in source code form as part of the SDK installer package.

Commercial License Usage

Licensees holding valid commercial licenses to the AUDIOKINETIC Wwise Technology
may use this file in accordance with the end user license agreement provided
with the software or, alternatively, in accordance with the terms contained in a
written agreement between you and Audiokinetic Inc.

Apache License Usage

Alternatively, this file may be used under the Apache License, Version 2.0 (the
"Apache License"); you may not use this file except in compliance with the
Apache License. You may obtain a copy of the Apache License at
http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software distributed
under the Apache License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES
OR CONDITIONS OF ANY KIND, either express or implied. See the Apache License for
the specific language governing permissions and limitations under the License.

  Copyright (c) 2021 Audiokinetic Inc.
*******************************************************************************/
// [wp-enhanced template] **Do not delete this line**

#include "TestPluginFXParams.h"

#include <AK/Tools/Common/AkBankReadHelpers.h>
#include <sstream>

TestPluginFXParams::TestPluginFXParams()
{
}

TestPluginFXParams::~TestPluginFXParams()
{
}

TestPluginFXParams::TestPluginFXParams(const TestPluginFXParams& in_rParams)
{
    InnerType = in_rParams.InnerType;
    RTPC = in_rParams.RTPC;
    NonRTPC = in_rParams.NonRTPC;
    m_paramChangeHandler.SetAllParamChanges();
}

AK::IAkPluginParam* TestPluginFXParams::Clone(AK::IAkPluginMemAlloc* in_pAllocator)
{
    return AK_PLUGIN_NEW(in_pAllocator, TestPluginFXParams(*this));
}

AKRESULT TestPluginFXParams::Init(AK::IAkPluginMemAlloc* in_pAllocator, const void* in_pParamsBlock, AkUInt32 in_ulBlockSize)
{
    if (in_ulBlockSize == 0)
    {
        // Initialize default parameters here
        // [ParameterInitialization]
        NonRTPC.bBoolParamAsCheckbox = true;
        RTPC.iIntParamAsComboBox = 0;
        RTPC.fFloatParamAsSlider = 0;
        // [/ParameterInitialization]
        m_paramChangeHandler.SetAllParamChanges();
        return AK_Success;
    }

    return SetParamsBlock(in_pParamsBlock, in_ulBlockSize);
}

AKRESULT TestPluginFXParams::Term(AK::IAkPluginMemAlloc* in_pAllocator)
{
    AK_PLUGIN_DELETE(in_pAllocator, this);
    return AK_Success;
}

AKRESULT TestPluginFXParams::SetParamsBlock(const void* in_pParamsBlock, AkUInt32 in_ulBlockSize)
{
    AKRESULT eResult = AK_Success;
    AkUInt8* pParamsBlock = (AkUInt8*)in_pParamsBlock;

    // Read bank data here
    // [ReadBankData]
    NonRTPC.bBoolParamAsCheckbox = READBANKDATA(bool, pParamsBlock, in_ulBlockSize);
    RTPC.iIntParamAsComboBox = READBANKDATA(AkInt32, pParamsBlock, in_ulBlockSize);
    RTPC.fFloatParamAsSlider = READBANKDATA(AkReal32, pParamsBlock, in_ulBlockSize);
    // [/ReadBankData]
    CHECKBANKDATASIZE(in_ulBlockSize, eResult);
    m_paramChangeHandler.SetAllParamChanges();

    return eResult;
}

AKRESULT TestPluginFXParams::SetParam(AkPluginParamID in_paramID, const void* in_pValue, AkUInt32 in_ulParamSize)
{
    AKRESULT eResult = AK_Success;

    // Handle parameter change here
    switch (in_paramID)
    {
    // [SetParameters]
    case PARAM_BOOL_PARAM_AS_CHECKBOX_ID:
        NonRTPC.bBoolParamAsCheckbox = *((bool*)in_pValue);
        m_paramChangeHandler.SetParamChange(PARAM_BOOL_PARAM_AS_CHECKBOX_ID);
        break;
    case PARAM_INT_PARAM_AS_COMBO_BOX_ID:
        RTPC.iIntParamAsComboBox = static_cast<AkInt32>(*(AkReal32*)in_pValue);
        m_paramChangeHandler.SetParamChange(PARAM_INT_PARAM_AS_COMBO_BOX_ID);
        break;
    case PARAM_FLOAT_PARAM_AS_SLIDER_ID:
        RTPC.fFloatParamAsSlider = *((AkReal32*)in_pValue);
        m_paramChangeHandler.SetParamChange(PARAM_FLOAT_PARAM_AS_SLIDER_ID);
        break;
    // [/SetParameters]
    default:
        eResult = AK_InvalidParameter;
        break;
    }

    return eResult;
}

bool TestPluginFXParams::ValidateParams()
{
    // [ValidateParameters]
    if (RTPC.fFloatParamAsSlider < -96 || RTPC.fFloatParamAsSlider > 24)
        return false;
    // [/ValidateParameters]
    return true;
}

std::string TestPluginFXParams::FormatParams()
{
    std::ostringstream oss;
    // [FormatParameters]
    oss << "NonRTPC.bBoolParamAsCheckbox = " << NonRTPC.bBoolParamAsCheckbox << std::endl;
    oss << "RTPC.iIntParamAsComboBox = " << RTPC.iIntParamAsComboBox << std::endl;
    oss << "RTPC.fFloatParamAsSlider = " << RTPC.fFloatParamAsSlider << std::endl;
    // [/FormatParameters]
    return oss.str();
}
