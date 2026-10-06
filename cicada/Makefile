# Cicada — Liber Primus / Gematria Primus toolkit.
CXX      ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra
SRC := src/gematria.cpp src/transforms.cpp src/score.cpp src/search.cpp src/cicada_main.cpp
OBJ := $(SRC:.cpp=.o)

cicada: $(OBJ)
	$(CXX) $(CXXFLAGS) -o $@ $(OBJ)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c -o $@ $<

test: cicada
	./cicada selftest

clean:
	rm -f $(OBJ) cicada

.PHONY: clean test
