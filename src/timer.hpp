#pragma once

#ifdef _OPENMP
#include <omp.h>
#else
#include <chrono>
#endif

// -----------------------------------------------------------------------------
// wall_time(): monotonic wall-clock seconds.
//
// When compiled with OpenMP we use omp_get_wtime(), which is the recommended
// portable high-resolution wall clock for timing parallel regions. Without
// OpenMP we fall back to std::chrono::steady_clock so the serial build still
// times correctly.
// -----------------------------------------------------------------------------
inline double wall_time() {
#ifdef _OPENMP
    return omp_get_wtime();
#else
    using namespace std::chrono;
    return duration<double>(steady_clock::now().time_since_epoch()).count();
#endif
}
