CXX ?= g++
CXXFLAGS ?= -std=c++17 -O3 -fPIC -Wall -Wextra
INCLUDES = -Iinclude
SRCS = src/log_analyzer.cpp src/metrics_analyzer.cpp src/correlator.cpp src/c_api.cpp

ifeq ($(OS),Windows_NT)
    TARGET = ../app/lib/aiops_core.dll
    LDFLAGS = -shared -static-libgcc -static-libstdc++
else
    UNAME_S := $(shell uname -s)
    ifeq ($(UNAME_S),Darwin)
        TARGET = ../app/lib/libaiops_core.dylib
        LDFLAGS = -dynamiclib
    else
        TARGET = ../app/lib/libaiops_core.so
        LDFLAGS = -shared
    endif
endif

all: $(TARGET)

$(TARGET): $(SRCS)
	@mkdir -p ../app/lib
	$(CXX) $(CXXFLAGS) $(INCLUDES) $(SRCS) $(LDFLAGS) -o $(TARGET)
	@echo "Built $(TARGET) successfully."

clean:
	rm -f $(TARGET) ../app/lib/*.dll ../app/lib/*.so ../app/lib/*.dylib
