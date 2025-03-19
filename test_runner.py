#!/usr/bin/env python3
"""
Glux 語言範例自動測試腳本
用於自動執行範例檔案並檢查其語法和語義是否正確
"""

import os
import subprocess
import sys
import glob
from pathlib import Path
from typing import List, Tuple, Dict
import re
import time
import signal

# 顏色輸出定義
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def print_header(text: str) -> None:
    """打印標題"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}===== {text} ====={Colors.END}\n")

def print_success(text: str) -> None:
    """打印成功訊息"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_warning(text: str) -> None:
    """打印警告訊息"""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_error(text: str) -> None:
    """打印錯誤訊息"""
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def find_examples() -> List[str]:
    """查找所有範例文件"""
    example_dir = Path("tests/examples")
    return sorted(glob.glob(str(example_dir / "*.glux")))

def run_check(file_path: str) -> Tuple[bool, List[str], List[str]]:
    """
    檢查文件的語法和語義
    
    Args:
        file_path: 文件路徑
        
    Returns:
        (成功與否, 錯誤列表, 警告列表)
    """
    cmd = ["python3", "-m", "src.glux.main", "check", file_path]
    try:
        # 添加 30 秒超時限制
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        # 調試輸出
        print(f"標準輸出: {result.stdout}")
        print(f"錯誤輸出: {result.stderr}")
        
        # 匹配錯誤和警告
        errors = re.findall(r"ERROR.*?語法錯誤: (.*?)$|ERROR.*?語義錯誤: (.*?)$", result.stderr, re.MULTILINE)
        warnings = re.findall(r"WARNING.*?警告: (.*?)$", result.stderr, re.MULTILINE)
        
        # 清理錯誤匹配
        cleaned_errors = []
        for err in errors:
            # 每個匹配都是一個元組，取非空的那個
            err_msg = next((e for e in err if e), "")
            if err_msg:
                cleaned_errors.append(err_msg)
        
        return result.returncode == 0, cleaned_errors, warnings
    except subprocess.TimeoutExpired:
        print(f"錯誤輸出: 檢查超時（超過30秒），可能存在無限循環或效能問題")
        return False, ["檢查超時，中止執行"], []

def run_execute(file_path: str) -> Tuple[bool, str]:
    """
    編譯並執行文件
    
    Args:
        file_path: 文件路徑
        
    Returns:
        (成功與否, 輸出)
    """
    cmd = ["python3", "-m", "src.glux.main", "run", file_path, "-v", "-j"]
    try:
        # 添加 30 秒超時限制
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "執行超時（超過30秒），可能存在無限循環或效能問題"

def detect_language_issues(file_path: str, content: str = None) -> List[str]:
    """
    檢測不符合語言規範的問題
    
    Args:
        file_path: 文件路徑
        content: 文件內容 (如果為 None 則讀取文件)
        
    Returns:
        問題列表
    """
    if content is None:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    
    issues = []
    
    # 檢查不符合規範的問題
    # 例如：使用不支持的語法、錯誤的字串插值使用等
    
    # 注意：Glux 語言分號是可選的，不再檢查分號缺失
    
    # 檢查不正確的字串插值使用
    if re.search(r'".*\${.*}"', content):
        issues.append("雙引號字串中使用了 ${} 插值，應該使用反引號 `` 字串")
    
    # 檢查不符合命名規範的變數名
    if re.search(r'\b[A-Z][a-z0-9]*[a-z0-9_][A-Za-z0-9]*\b', content):
        issues.append("變數命名可能不符合規範，Glux 使用 snake_case 命名法")
    
    return issues

def auto_fix_issues(file_path: str) -> Tuple[bool, List[str]]:
    """
    自動修復檔案中的問題
    
    Args:
        file_path: 文件路徑
        
    Returns:
        (是否修改, 修改列表)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    fixes = []
    modified = False
    
    # 注意：不再自動添加分號，因為分號是可選的
    
    # 修復字串插值語法
    new_content = re.sub(r'"(.*?)\${(.*?)}"', r'`\1${\2}`', content)
    if new_content != content:
        fixes.append("修復字串插值語法，將雙引號改為反引號")
        content = new_content
        modified = True
    
    # 如果有修改，寫回文件
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    return modified, fixes

def main():
    """主函數"""
    # 設置整個測試的最大執行時間（10分鐘）
    max_execution_time = 600  # 秒
    
    # 定義超時處理函數
    def timeout_handler(signum, frame):
        print_error(f"\n整體測試超時！已經執行超過 {max_execution_time} 秒")
        sys.exit(2)
    
    # 設置超時信號處理
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(max_execution_time)
    
    start_time = time.time()
    print_header("Glux 語言範例自動測試")
    
    examples = find_examples()
    print(f"找到 {len(examples)} 個範例文件")
    
    results = {
        "passed": [],
        "warnings": [],
        "failed": [],
        "fixed": []
    }
    
    for example in examples:
        # 檢查每個測試的耗時
        example_start_time = time.time()
        print(f"\n處理範例: {os.path.basename(example)}")
        
        # 檢查語言規範問題
        issues = detect_language_issues(example)
        if issues:
            print_warning(f"發現可能不符合語言規範的問題:")
            for issue in issues:
                print(f"  - {issue}")
            
            # 嘗試自動修復
            fixed, fixes = auto_fix_issues(example)
            if fixed:
                print_success(f"自動修復了以下問題:")
                for fix in fixes:
                    print(f"  - {fix}")
                results["fixed"].append(example)
        
        # 檢查語法和語義
        success, errors, warnings = run_check(example)
        
        if not success:
            print_error("檢查失敗:")
            for error in errors:
                print(f"  - {error}")
            results["failed"].append(example)
            continue
        
        if warnings:
            print_warning("有警告:")
            for warning in warnings:
                print(f"  - {warning}")
            results["warnings"].append(example)
        else:
            print_success("檢查通過，無警告")
        
        # 執行範例
        exec_success, output = run_execute(example)
        
        if exec_success:
            print_success("執行成功")
            results["passed"].append(example)
        else:
            print_error("執行失敗")
            print("輸出:")
            print(output)
            if example not in results["failed"]:
                results["failed"].append(example)
        
        # 報告每個測試的耗時
        example_time = time.time() - example_start_time
        print(f"測試耗時: {example_time:.2f} 秒")
    
    # 取消超時信號
    signal.alarm(0)
    
    # 打印總結
    total_time = time.time() - start_time
    print_header("測試總結")
    print(f"總共測試了 {len(examples)} 個範例，總耗時: {total_time:.2f} 秒")
    print(f"通過: {len(results['passed'])}")
    print(f"有警告: {len(results['warnings'])}")
    print(f"失敗: {len(results['failed'])}")
    print(f"自動修復: {len(results['fixed'])}")
    
    if results["failed"]:
        print_error("以下範例檢查失敗:")
        for example in results["failed"]:
            print(f"  - {os.path.basename(example)}")
    
    if results["fixed"]:
        print_success("以下範例被自動修復:")
        for example in results["fixed"]:
            print(f"  - {os.path.basename(example)}")
    
    # 返回適當的結束碼
    return 0 if not results["failed"] else 1

if __name__ == "__main__":
    sys.exit(main()) 