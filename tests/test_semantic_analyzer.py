"""
語義分析器測試腳本
"""

import os
import sys
import unittest

# 將項目根目錄添加到路徑中
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.glux.analysis.semantic_analyzer import SemanticAnalyzer
from src.glux.parser.parser import Parser
from src.glux.lexer.lexer import Lexer


class TestSemanticAnalyzer(unittest.TestCase):
    """語義分析器測試類"""
    
    def setUp(self):
        """設置測試環境"""
        self.lexer = Lexer()
        self.parser = Parser()
        self.analyzer = SemanticAnalyzer()
    
    def test_basic_program(self):
        """測試基本程序"""
        code = """
        fn main() -> void {
            let x: int = 10;
            let y: int = 20;
            let z: int = x + y;
            print(z);
        }
        """
        tokens = self.lexer.tokenize(code)
        ast = self.parser.parse(tokens)
        result = self.analyzer.analyze(ast)
        
        self.assertTrue(result)
        self.assertEqual(len(self.analyzer.get_errors()), 0)
    
    def test_type_error(self):
        """測試類型錯誤"""
        code = """
        fn main() -> void {
            let x: int = "hello";  // 類型錯誤
            print(x);
        }
        """
        tokens = self.lexer.tokenize(code)
        ast = self.parser.parse(tokens)
        result = self.analyzer.analyze(ast)
        
        self.assertFalse(result)
        self.assertGreater(len(self.analyzer.get_errors()), 0)
    
    def test_undefined_variable(self):
        """測試未定義變數"""
        code = """
        fn main() -> void {
            print(x);  // 未定義的變數
        }
        """
        tokens = self.lexer.tokenize(code)
        ast = self.parser.parse(tokens)
        result = self.analyzer.analyze(ast)
        
        self.assertFalse(result)
        self.assertGreater(len(self.analyzer.get_errors()), 0)
    
    def test_function_return(self):
        """測試函數返回值"""
        code = """
        fn add(a: int, b: int) -> int {
            return a + b;
        }
        
        fn main() -> void {
            let result: int = add(5, 10);
            print(result);
        }
        """
        tokens = self.lexer.tokenize(code)
        ast = self.parser.parse(tokens)
        result = self.analyzer.analyze(ast)
        
        self.assertTrue(result)
        self.assertEqual(len(self.analyzer.get_errors()), 0)
    
    def test_missing_return(self):
        """測試缺少返回值"""
        code = """
        fn add(a: int, b: int) -> int {
            let c: int = a + b;
            // 缺少返回語句
        }
        
        fn main() -> void {
            let result: int = add(5, 10);
            print(result);
        }
        """
        tokens = self.lexer.tokenize(code)
        ast = self.parser.parse(tokens)
        result = self.analyzer.analyze(ast)
        
        self.assertFalse(result)
        self.assertGreater(len(self.analyzer.get_errors()), 0)
    
    def test_control_flow(self):
        """測試控制流"""
        code = """
        fn abs(x: int) -> int {
            if (x < 0) {
                return -x;
            } else {
                return x;
            }
        }
        
        fn main() -> void {
            let a: int = abs(-10);
            let b: int = abs(5);
            print(a);
            print(b);
        }
        """
        tokens = self.lexer.tokenize(code)
        ast = self.parser.parse(tokens)
        result = self.analyzer.analyze(ast)
        
        self.assertTrue(result)
        self.assertEqual(len(self.analyzer.get_errors()), 0)


if __name__ == '__main__':
    unittest.main() 