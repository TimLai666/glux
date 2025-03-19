#!/usr/bin/env python3
from src.glux.parser.parser import Parser
from src.glux.lexer.lexer import Lexer
import sys

def print_ast_node(node, indent=0):
    """遞迴打印AST節點及其屬性"""
    prefix = "  " * indent
    node_type = type(node).__name__
    
    # 打印節點類型
    print(f"{prefix}+ {node_type}")
    
    # 打印節點屬性
    for attr_name, attr_value in vars(node).items():
        if attr_name.startswith("_"):
            continue  # 跳過私有屬性
            
        if isinstance(attr_value, list):
            print(f"{prefix}  {attr_name}: [列表，{len(attr_value)}項]")
            for i, item in enumerate(attr_value):
                print(f"{prefix}    [{i}]:")
                if hasattr(item, "__dict__"):
                    print_ast_node(item, indent + 3)
                else:
                    print(f"{prefix}      {item}")
        elif hasattr(attr_value, "__dict__"):
            print(f"{prefix}  {attr_name}:")
            print_ast_node(attr_value, indent + 2)
        else:
            print(f"{prefix}  {attr_name}: {attr_value}")

def print_ast(file_path):
    """打印指定文件的 AST"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        print(f"===== 解析文件: {file_path} =====")
        lexer = Lexer(content, file_path)
        tokens = lexer.tokenize()
        print(f"詞法分析完成，總共 {len(tokens)} 個標記")
        
        parser = Parser(tokens)
        ast = parser.parse()
        
        print(f"\n===== AST 詳細結構 =====")
        print_ast_node(ast)
        
        return True
    except Exception as e:
        print(f"解析錯誤：{e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        file_path = "tests/examples/test_conditional.glux"
    
    print_ast(file_path) 