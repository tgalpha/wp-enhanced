cmake_minimum_required(VERSION 3.21)
project(test)

set(CMAKE_CXX_STANDARD 17)

# Define NOMINMAX to fix failure with MSVC: https://github.com/catchorg/Catch2/pull/2702#issuecomment-1586336031
add_compile_definitions(CATCH_CONFIG_ENABLE_BENCHMARKING NOMINMAX)

include_directories(%(test_util)s)
include_directories(../SoundEnginePlugin)
include_directories($ENV{WWISESDK}/include)

# [PremakeDefinedIncludes]
# [/PremakeDefinedIncludes]

set(catch2 catch2/catch_amalgamated.hpp catch2/catch_amalgamated.cpp)

set(test_case main.cpp)


add_executable(test ${test_case} ${catch2} ${plugin_link})
target_link_libraries(test $ENV{WWISESDK}/x64_vc160/Release/lib/%(name)sFX.lib)
