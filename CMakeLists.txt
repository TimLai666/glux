cmake_minimum_required(VERSION 3.10)
project(glux)

# 尋找 LLVM 環境變數
set(LLVM_PREFIX_ENV $ENV{LLVM_SYS_160_PREFIX})
if(LLVM_PREFIX_ENV)
    message(STATUS "LLVM prefix from environment: ${LLVM_PREFIX_ENV}")
    # 設置 LLVM_DIR 讓 find_package 可以找到
    set(LLVM_DIR "${LLVM_PREFIX_ENV}/lib/cmake/llvm")
endif()

# 嘗試尋找 LLVM 套件
find_package(LLVM 16 QUIET)
if(NOT LLVM_FOUND)
    message(WARNING "LLVM 16 not found. Consider running download_llvm.py script first.")
endif()

# 設定編譯器標準
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# 將來如果需要可以在此添加其他依賴和編譯選項
