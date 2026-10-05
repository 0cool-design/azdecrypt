# AZdecrypt GPU port — build file.
#   make         CPU-only tools (g++ + zlib): commands `score`, `solve`
#   make gpu     GPU-enabled binary (nvcc): adds `gsolve`
# Both produce ./azgpu (the GPU build is a superset).

CXX      ?= g++
CXXFLAGS ?= -O3 -march=native -std=c++17 -Wall -Wextra -fopenmp
LDFLAGS  ?= -lz -fopenmp

NVCC      ?= nvcc
# RTX 40-series (Ada) = sm_89. Adjust -arch for other GPUs.
NVARCH    ?= sm_89
NVCCFLAGS ?= -O3 -std=c++17 -arch=$(NVARCH) -DUSE_CUDA \
             -Xcompiler "-O3 -march=native -fopenmp"

CPU_SRC := src/ngram.cpp src/cipher.cpp src/solver.cpp src/main.cpp
CPU_OBJ := $(CPU_SRC:.cpp=.o)

azgpu: $(CPU_OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $(CPU_OBJ) $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

# GPU build: compile everything through nvcc so host + device link cleanly.
gpu:
	$(NVCC) $(NVCCFLAGS) -o azgpu $(CPU_SRC) src/solver_gpu.cu -lz

clean:
	rm -f $(CPU_OBJ) azgpu

.PHONY: clean gpu
