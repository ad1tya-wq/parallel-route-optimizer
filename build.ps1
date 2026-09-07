# Build ParallelRoute without CMake.
#
# The repo still ships CMakeLists.txt for portability, but CMake is an extra
# install on Windows and the project is header-only plus one translation unit,
# so a single compiler invocation is enough. This script finds a g++ with
# OpenMP (MSYS2 UCRT64/MINGW64, or one already on PATH) and links statically,
# so build\ParallelRoute.exe runs on a machine with no MSYS2 installed.
param([switch]$Debug, [switch]$NoNative)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$candidates = @(
  "C:\msys64\ucrt64\bin\g++.exe",
  "C:\msys64\mingw64\bin\g++.exe",
  "C:\mingw64\bin\g++.exe"
)
$gpp = $null
foreach ($c in $candidates) { if (Test-Path $c) { $gpp = $c; break } }
if (-not $gpp) {
  $onPath = Get-Command g++ -ErrorAction SilentlyContinue
  if ($onPath) { $gpp = $onPath.Source }
}
if (-not $gpp) {
  Write-Error "No g++ found. Install MSYS2 (https://www.msys2.org) then run:`n  pacman -S mingw-w64-ucrt-x86_64-gcc"
}
Write-Host "compiler : $gpp"
Write-Host ((& $gpp --version) | Select-Object -First 1)

$flags = @("-std=c++17", "-fopenmp", "-static", "-static-libgcc", "-static-libstdc++")
if ($Debug) { $flags += @("-O0", "-g", "-Wall", "-Wextra", "-fsanitize=undefined") }
else        { $flags += @("-O3", "-Wall", "-Wextra") }
if (-not $NoNative) { $flags += "-march=native" }

New-Item -ItemType Directory -Force -Path (Join-Path $root "build") | Out-Null
$out = Join-Path $root "build\ParallelRoute.exe"
Write-Host "flags    : $($flags -join ' ')"
& $gpp @flags -o $out (Join-Path $root "src\main.cpp")
if ($LASTEXITCODE -ne 0) { Write-Error "build failed" }
Write-Host "built    : $out"

# Correctness gate: the circle instance has a closed-form optimum, so a correct
# solver must reach a 0.00% gap. Refuse to call the build good otherwise.
Write-Host "`n-- self-test (circle50, known optimum) --"
& $out --mode island-dtam --engine opt --gen circle --n 50 --generations 400 --islands 4 --threads 4 --twoopt --validate
if ($LASTEXITCODE -ne 0) { Write-Error "self-test FAILED" }
Write-Host "`nOK. Next: python bench\run_study.py"
