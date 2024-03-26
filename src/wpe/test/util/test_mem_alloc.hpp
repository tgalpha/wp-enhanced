#pragma once

#include <map>
#include <string>
#include <cstdlib>
#include <AK/Tools/Common/AkAllocator.h>


struct PointerInfo
{
    size_t uSize;
    std::string sFile;
    AkUInt32 uLine;
};


class TestMemAlloc : public AK::IAkPluginMemAlloc
{
public:
    ~TestMemAlloc()
    {
    }

    void* Malloc(size_t in_uSize, const char* in_pszFile, AkUInt32 in_uLine)
    {
        auto p = malloc(in_uSize);
        m_normalPointers[p] = PointerInfo{in_uSize, in_pszFile, in_uLine};
        return p;
    }

    void* Realloc(void* in_pMemAddress, size_t in_uSize, const char* in_pszFile, AkUInt32 in_uLine)
    {
        m_normalPointers.erase(in_pMemAddress);
        auto p = realloc(in_pMemAddress, in_uSize);
        m_normalPointers[p] = PointerInfo{in_uSize, in_pszFile, in_uLine};
        return p;
    }

    void Free(void* in_pMemAddress)
    {
#if __cplusplus >= 202002L
             if (m_memAlignedPointers.contains(in_pMemAddress))
#else
        if (m_memAlignedPointers.count(in_pMemAddress))
#endif
        {
            _aligned_free(in_pMemAddress);
            m_memAlignedPointers.erase(in_pMemAddress);
        }
#if __cplusplus >= 202002L
             else if (m_normalPointers.contains(in_pMemAddress))
#else
        else if (m_normalPointers.count(in_pMemAddress))
#endif
        {
            free(in_pMemAddress);
            m_normalPointers.erase(in_pMemAddress);
        }
    }

    void* Malign(size_t in_uSize, size_t in_uAlignment, const char* in_pszFile, AkUInt32 in_uLine)
    {
#ifdef AK_WIN
        void* p = _aligned_malloc(in_uSize, in_uAlignment);
#else
              void* p = aligned_alloc(in_uAlignment, in_uSize);
#endif
        m_memAlignedPointers[p] = PointerInfo{in_uSize, in_pszFile, in_uLine};
        return p;
    }

    void* ReallocAligned(void* in_pMemAddress, size_t in_uSize, size_t in_uAlignment, const char* in_pszFile,
                         AkUInt32 in_uLine)
    {
        m_memAlignedPointers.erase(in_pMemAddress);
#ifdef AK_WIN
        void* p = _aligned_realloc(in_pMemAddress, in_uSize, in_uAlignment);
#else
          	AKASSERT(!"ReallocAligned is not supported: using realloc")
              void* p = realloc(in_pMemAddress, in_uSize);
#endif
        m_memAlignedPointers[p] = PointerInfo{in_uSize, in_pszFile, in_uLine};
        return p;
    }

    bool Empty()
    {
        return m_normalPointers.empty() && m_memAlignedPointers.empty();
    }

    void TakeSnapshotLog()
    {
        const auto fNotAlignedMemKB = static_cast<float>(MemAllocated()) / 1024;
        const auto fAlignedMemKB = static_cast<float>(AlignedMemAllocated()) / 1024;
        m_snapshotLog = "## MemoryStats(KB)\n";
        m_snapshotLog.append("Not aligned memory: " + std::to_string(fNotAlignedMemKB) + "\n");
        m_snapshotLog.append("Aligned memory: " + std::to_string(fAlignedMemKB) + "\n");
        m_snapshotLog.append("Total: " + std::to_string(fNotAlignedMemKB + fAlignedMemKB) + "\n");
    }

    std::string GetSnapshotLog()
    {
        return m_snapshotLog;
    }

    size_t MemAllocated()
    {
        size_t uSize = 0;
        for (const auto pair : m_normalPointers)
        {
            uSize += pair.second.uSize;
        }
        return uSize;
    }

    size_t AlignedMemAllocated()
    {
        size_t uSize = 0;
        for (const auto pair : m_memAlignedPointers)
        {
            uSize += pair.second.uSize;
        }
        return uSize;
    }

private:
    std::map<void*, PointerInfo> m_memAlignedPointers;
    std::map<void*, PointerInfo> m_normalPointers;

    std::string m_snapshotLog;
};
