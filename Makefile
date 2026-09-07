# Non-CMake build for Linux/macOS/MSYS. See build.ps1 for the Windows helper.
CXX      ?= g++
CXXFLAGS ?= -std=c++17 -O3 -march=native -Wall -Wextra -fopenmp
LDFLAGS  ?=
BIN      := build/ParallelRoute
SRC      := src/main.cpp
HDRS     := $(wildcard src/*.hpp)

.PHONY: all test clean study
all: $(BIN)

$(BIN): $(SRC) $(HDRS)
	@mkdir -p build
	$(CXX) $(CXXFLAGS) -o $@ $(SRC) $(LDFLAGS)

# Differential tests: the optimised engine must reproduce the frozen baseline.
test: $(BIN)
	@mkdir -p build
	$(CXX) -std=c++17 -O2 -o build/test_equiv tests/test_equiv.cpp
	$(CXX) -std=c++17 -O2 -fopenmp -o build/test_island_equiv tests/test_island_equiv.cpp
	$(CXX) -std=c++17 -O2 -o build/test_diversity tests/test_diversity.cpp
	$(CXX) -std=c++17 -O2 -o build/test_twoopt_fast tests/test_twoopt_fast.cpp
	./build/test_equiv
	./build/test_island_equiv
	./build/test_diversity
	./build/test_twoopt_fast
	./$(BIN) --mode island-dtam --engine opt --gen circle --n 50 --generations 400 \
	         --islands 4 --threads 4 --twoopt --validate

study: $(BIN)
	python bench/run_study.py
	python bench/analyze_study.py

clean:
	rm -rf build
