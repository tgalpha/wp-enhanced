#pragma once
#include <AK/SoundEngine/Common/AkCommonDefs.h>

DEFINEDUMMYASSERTHOOK

inline void FillWithRandomSamples(AkSampleType* in_pBuffer, AkUInt32 in_uSize)
{
    srand(0);
    for (int i = 0; i < in_uSize; ++i)
    {
        *in_pBuffer++ = (static_cast<AkSampleType>(rand()) / RAND_MAX) * 2 - 1;
    }
}


inline void FillWithRandomSamples(AkAudioBuffer* in_pBuffer)
{
    in_pBuffer->eState = AK_DataReady;
    FillWithRandomSamples(in_pBuffer->GetChannel(0), in_pBuffer->MaxFrames() * in_pBuffer->NumChannels());
}
