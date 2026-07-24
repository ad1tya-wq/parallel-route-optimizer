cmake_minimum_required(VERSION 3.16)
project(ParallelRoute CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# --- OpenMP discovery ---------------------------------------------------------
# On macOS, Apple clang ships without an OpenMP runtime; Homebrew's libomp is
# "keg-only" so CMake can't find it automatically. Hint FindOpenMP explicitly.
# On Linux (GCC/Clang) and Windows (MSVC /openmp, MinGW -fopenmp) it just works.
if(APPLE)
  execute_process(COMMAND brew --prefix libomp
    OUTPUT_VARIABLE LIBOMP_PREFIX OUTPUT_STRIP_TRAILING_WHITESPACE ERROR_QUIET)
  if(LIBOMP_PREFIX)
    set(OpenMP_CXX_FLAGS "-Xpreprocessor -fopenmp -I${LIBOMP_PREFIX}/include")
    set(OpenMP_CXX_LIB_NAMES "omp")
    set(OpenMP_omp_LIBRARY "${LIBOMP_PREFIX}/lib/libomp.dylib")
  endif()
endif()

find_package(OpenMP REQUIRED)

add_executable(ParallelRoute src/main.cpp)
target_link_libraries(ParallelRoute PRIVATE OpenMP::OpenMP_CXX)

# --- Optimisation flags -------------------------------------------------------
if(MSVC)
  target_compile_options(ParallelRoute PRIVATE /O2 /EHsc)
else()
  target_compile_options(ParallelRoute PRIVATE -O3)
  include(CheckCXXCompilerFlag)
  check_cxx_compiler_flag("-march=native" HAS_MARCH_NATIVE)
  if(HAS_MARCH_NATIVE)
    target_compile_options(ParallelRoute PRIVATE -march=native)
  endif()
endif()
