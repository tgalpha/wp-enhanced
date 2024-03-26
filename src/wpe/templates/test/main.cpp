#include <test_mem_alloc.hpp>
#include <test_util.hpp>
#include "catch2/catch_amalgamated.hpp"


const auto CHANNEL_CONFIG = AkChannelConfig{
    2,
    AK_SPEAKER_SETUP_STEREO
};
constexpr AkUInt32 SAMPLE_RATE = 48000;
constexpr AkUInt16 FRAME_SIZE = 1024;

// Process 500*1024/48000 = 10.67 seconds of audio
constexpr AkUInt32 BENCHMARK_FRAME_COUNT = 500;

TEST_CASE("TestCase")
{
    // Memory allocator which implements AK::IAkPluginMemAlloc
    TestMemAlloc testAllocator;

    // Fill inBuffer with random float between -1~1
    AkAudioBuffer ioBuffer;
    auto samples = std::vector<AkSampleType>(FRAME_SIZE * CHANNEL_CONFIG.uNumChannels);
    ioBuffer.AttachContiguousDeinterleavedData(samples.data(), FRAME_SIZE, FRAME_SIZE, CHANNEL_CONFIG);
    FillWithRandomSamples(&ioBuffer);

    BENCHMARK("Process")
    {
        for (auto i = 0; i < BENCHMARK_FRAME_COUNT; ++i)
        {
            // Process...
        }
    };
    testAllocator.TakeSnapshotLog();

    INFO(testAllocator.GetSnapshotLog());
    CHECK(testAllocator.Empty());
}
