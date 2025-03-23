"""
二進制代碼生成器模組
負責將AST轉換為可執行的二進制文件
"""

import os
import subprocess
import tempfile
import logging
import platform
import ctypes
import sys
from typing import List, Optional, Any, Dict, Tuple
from pathlib import Path

from ..parser import ast_nodes
from .code_generator import CodeGenerator

# 嘗試導入 LLVM Python 綁定
try:
    import llvmlite.binding as llvm
    LLVMLITE_AVAILABLE = True
except ImportError:
    LLVMLITE_AVAILABLE = False


class BinaryEmitter:
    """用於將 AST 轉換為可執行二進制文件的類"""
    
    def __init__(self, ast, output_path: str):
        """
        初始化 BinaryEmitter
        
        Args:
            ast: 抽象語法樹
            output_path: 輸出文件路徑
        """
        self.ast = ast
        self.output_path = output_path
        self.errors = []
        self.logger = logging.getLogger("BinaryEmitter")
        
        # 檢查輸出路徑
        self._prepare_output_path()
    
    def _prepare_output_path(self):
        """準備輸出路徑"""
        # 創建輸出目錄
        output_dir = os.path.dirname(self.output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                self.errors.append(f"無法創建輸出目錄 {output_dir}: {str(e)}")
                self.logger.error(f"無法創建輸出目錄 {output_dir}: {str(e)}")
        
        # 如果未指定擴展名，根據平台添加擴展名
        if not os.path.splitext(self.output_path)[1]:
            if platform.system() == 'Windows':
                self.output_path += '.exe'
    
    def check_and_install_llvm(self):
        """檢查LLVM並嘗試自動安裝"""
        
        def is_cmd_available(cmd):
            """檢查命令是否可用"""
            try:
                subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                return True
            except:
                return False
        
        # 檢查LLVM是否已安裝
        if is_cmd_available("llc"):
            return True
            
        self.logger.info("LLVM未安裝，正在嘗試自動安裝...")
        print("\n[自動安裝] 正在嘗試安裝LLVM工具鏈...\n")
        
        import platform
        system = platform.system()
        success = False
        
        if system == "Darwin":  # macOS
            # 檢查可用的包管理器
            if is_cmd_available("brew"):
                try:
                    print("使用Homebrew安裝LLVM...")
                    subprocess.run(["brew", "install", "llvm"], check=True)
                    print("添加LLVM到PATH...")
                    llvm_path = subprocess.run(["brew", "--prefix", "llvm"], 
                                             stdout=subprocess.PIPE, text=True).stdout.strip() + "/bin"
                    os.environ["PATH"] = llvm_path + os.pathsep + os.environ["PATH"]
                    success = is_cmd_available("llc")
                except:
                    success = False
            
            if not success and is_cmd_available("port"):
                try:
                    print("使用MacPorts安裝LLVM...")
                    subprocess.run(["sudo", "port", "install", "llvm"], check=True)
                    success = is_cmd_available("llc")
                except:
                    success = False
                    
        elif system == "Linux":
            # 檢測Linux發行版和包管理器
            package_managers = {
                "apt-get": "sudo apt-get update && sudo apt-get install -y llvm",
                "apt": "sudo apt update && sudo apt install -y llvm",
                "dnf": "sudo dnf install -y llvm",
                "yum": "sudo yum install -y llvm",
                "pacman": "sudo pacman -S --noconfirm llvm"
            }
            
            for pm, cmd in package_managers.items():
                if is_cmd_available(pm):
                    try:
                        print(f"使用{pm}安裝LLVM...")
                        subprocess.run(cmd, shell=True, check=True)
                        success = is_cmd_available("llc")
                        if success:
                            break
                    except:
                        pass
                        
        elif system == "Windows":
            try:
                # 檢查chocolatey
                if is_cmd_available("choco"):
                    print("使用Chocolatey安裝LLVM...")
                    subprocess.run(["choco", "install", "llvm", "-y"], check=True)
                    success = is_cmd_available("llc")
                # 檢查scoop
                elif is_cmd_available("scoop"):
                    print("使用Scoop安裝LLVM...")
                    subprocess.run(["scoop", "install", "llvm"], check=True)
                    success = is_cmd_available("llc")
            except:
                success = False
        
        # 安裝結果報告        
        if success:
            print("\n[成功] LLVM已成功安裝!\n")
            return True
        else:
            print("\n[失敗] 自動安裝LLVM失敗，請手動安裝。")
            # 提供手動安裝指導
            if system == "Darwin":
                print("macOS手動安裝指令: brew install llvm")
            elif system == "Linux":
                print("Linux手動安裝指令: 使用您的包管理器安裝llvm包")
            elif system == "Windows":
                print("Windows: 請從 https://github.com/llvm/llvm-project/releases 下載安裝")
            
            print("\n安裝後請重新運行編譯器\n")
            return False
    
    def emit(self) -> Optional[str]:
        """
        生成二進制可執行文件
        
        Returns:
            生成的二進制文件路徑，如果失敗則返回None
        """
        if self.errors:
            return None
        
        try:
            # 生成 LLVM IR
            from ..codegen.code_generator import LLVMCodeGenerator
            self.logger.info("開始生成 LLVM IR...")
            code_generator = LLVMCodeGenerator(options=None)
            llvm_ir = code_generator.generate(self.ast)
            
            # 保存 LLVM IR 到臨時文件
            with tempfile.NamedTemporaryFile(suffix='.ll', delete=False) as temp_file:
                ir_file = temp_file.name
                temp_file.write(llvm_ir.encode('utf-8'))
            
            # 使用 LLVM 工具鏈將 LLVM IR 編譯為二進制文件
            self.logger.info(f"開始編譯 LLVM IR 為二進制文件...")
            binary_file = self._compile_llvm_ir(ir_file)
            
            # 清理臨時文件
            try:
                os.unlink(ir_file)
            except:
                pass
            
            if not binary_file:
                self.logger.error("編譯 LLVM IR 為二進制文件失敗")
                return None
            
            self.logger.info(f"成功生成二進制文件: {binary_file}")
            return binary_file
            
        except Exception as e:
            self.errors.append(f"生成二進制文件時發生錯誤: {str(e)}")
            self.logger.error(f"生成二進制文件時發生錯誤: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _compile_llvm_ir(self, ir_file: str) -> Optional[str]:
        """
        將 LLVM IR 編譯為二進制文件
        
        Args:
            ir_file: LLVM IR 文件路徑
        
        Returns:
            生成的二進制文件路徑，如果失敗則返回None
        """
        try:
            # 檢查是否有 LLVM 工具鏈
            llc_cmd = self._find_command('llc')
            if not llc_cmd:
                self.logger.warning("找不到 LLVM 的 llc 命令，嘗試自動安裝LLVM...")
                if self.check_and_install_llvm():
                    llc_cmd = self._find_command('llc')
                else:
                    self.errors.append("找不到 LLVM 的 llc 命令，無法生成機器碼")
                    self.logger.error("找不到 LLVM 的 llc 命令，無法生成機器碼")
                    return None
            
            # 檢查是否有編譯器
            if platform.system() == 'Windows':
                cc_cmd = self._find_command('clang')
                if not cc_cmd:
                    cc_cmd = self._find_command('cl')
            else:
                cc_cmd = self._find_command('clang')
                if not cc_cmd:
                    cc_cmd = self._find_command('gcc')
            
            if not cc_cmd:
                # 嘗試安裝編譯器
                self.logger.warning("找不到 C 編譯器，嘗試自動安裝...")
                if platform.system() == 'Darwin' and self._find_command('brew'):
                    subprocess.run(["brew", "install", "gcc"], check=True)
                    cc_cmd = self._find_command('gcc')
                elif platform.system() == 'Linux':
                    # 檢測Linux發行版
                    package_managers = {
                        "apt-get": "sudo apt-get install -y gcc",
                        "apt": "sudo apt install -y gcc",
                        "dnf": "sudo dnf install -y gcc",
                        "yum": "sudo yum install -y gcc",
                        "pacman": "sudo pacman -S --noconfirm gcc"
                    }
                    for pm, cmd in package_managers.items():
                        if self._find_command(pm):
                            subprocess.run(cmd, shell=True, check=True)
                            cc_cmd = self._find_command('gcc')
                            if cc_cmd:
                                break
            
            if not cc_cmd:
                self.errors.append("找不到 C 編譯器 (clang/gcc)，無法生成可執行文件")
                self.logger.error("找不到 C 編譯器 (clang/gcc)，無法生成可執行文件")
                return None
            
            # 創建臨時目錄
            with tempfile.TemporaryDirectory() as temp_dir:
                # 設置文件路徑
                obj_file = os.path.join(temp_dir, 'output.o')
                asm_file = os.path.join(temp_dir, 'output.s')
                
                # 生成匯編代碼
                self.logger.info(f"使用 llc 生成匯編代碼...")
                llc_process = subprocess.run(
                    [llc_cmd, '-filetype=asm', '-relocation-model=pic', ir_file, '-o', asm_file],
                    capture_output=True,
                    text=True
                )
                
                if llc_process.returncode != 0:
                    self.errors.append(f"使用 llc 生成匯編代碼失敗: {llc_process.stderr}")
                    self.logger.error(f"使用 llc 生成匯編代碼失敗: {llc_process.stderr}")
                    return None
                
                # 生成目標文件
                if platform.system() == 'Windows' and cc_cmd.endswith('cl'):
                    # 使用 MSVC 編譯
                    cc_process = subprocess.run(
                        [cc_cmd, '/c', asm_file, '/Fo' + obj_file],
                        capture_output=True,
                        text=True
                    )
                else:
                    # 使用 GCC/Clang 編譯
                    cc_process = subprocess.run(
                        [cc_cmd, '-c', asm_file, '-o', obj_file],
                        capture_output=True,
                        text=True
                    )
                
                if cc_process.returncode != 0 or not os.path.exists(obj_file):
                    self.errors.append(f"編譯匯編代碼失敗: {cc_process.stderr}")
                    self.logger.error(f"編譯匯編代碼失敗: {cc_process.stderr}")
                    return None
                
                # 生成最終可執行文件
                if platform.system() == 'Windows' and cc_cmd.endswith('cl'):
                    # 使用 MSVC 鏈接
                    link_process = subprocess.run(
                        [cc_cmd, obj_file, '/Fe' + self.output_path],
                        capture_output=True,
                        text=True
                    )
                else:
                    # 使用 GCC/Clang 鏈接
                    link_process = subprocess.run(
                        [cc_cmd, obj_file, '-o', self.output_path],
                        capture_output=True,
                        text=True
                    )
                
                if link_process.returncode != 0 or not os.path.exists(self.output_path):
                    self.errors.append(f"鏈接目標文件失敗: {link_process.stderr}")
                    self.logger.error(f"鏈接目標文件失敗: {link_process.stderr}")
                    return None
            
            # 設置可執行權限
            if platform.system() != 'Windows':
                os.chmod(self.output_path, 0o755)
            
            return self.output_path
            
        except Exception as e:
            self.errors.append(f"編譯 LLVM IR 為二進制文件時發生錯誤: {str(e)}")
            self.logger.error(f"編譯 LLVM IR 為二進制文件時發生錯誤: {str(e)}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return None
    
    def _find_command(self, cmd: str) -> Optional[str]:
        """
        查找命令的完整路徑
        
        Args:
            cmd: 命令名稱
        
        Returns:
            命令的完整路徑，如果找不到則返回None
        """
        if platform.system() == 'Windows':
            cmd = cmd + '.exe'
        
        # 查找環境變量中的命令
        for path in os.environ.get('PATH', '').split(os.pathsep):
            cmd_path = os.path.join(path, cmd)
            if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
                return cmd_path
        
        # 查找默認位置
        default_paths = []
        if platform.system() == 'Windows':
            program_files = os.environ.get('ProgramFiles', 'C:\\Program Files')
            default_paths.extend([
                os.path.join(program_files, 'LLVM', 'bin'),
                os.path.join(program_files, 'Microsoft Visual Studio', 'VC', 'bin')
            ])
        else:
            default_paths.extend([
                '/usr/bin',
                '/usr/local/bin',
                '/opt/local/bin',
                '/opt/homebrew/bin'
            ])
        
        for path in default_paths:
            cmd_path = os.path.join(path, cmd)
            if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
                return cmd_path
        
        return None 