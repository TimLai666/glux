"""
Glux 類型系統使用示例
展示如何使用 TypeSystem 進行類型管理
"""

from .type_system import TypeSystem
from .type_defs import TypeKind, GluxType
from llvmlite import ir


def register_custom_types():
    """註冊自定義類型示例"""
    # 註冊結構體類型
    person_fields = [
        ir.IntType(32),              # age
        ir.IntType(8).as_pointer(),  # name
        ir.DoubleType()              # height
    ]
    field_names = ["age", "name", "height"]
    person_type = TypeSystem.register_struct_type("Person", person_fields, field_names)
    print(f"註冊結構體類型 Person: {person_type}")

    # 註冊枚舉類型
    color_members = {
        "RED": 0,
        "GREEN": 1,
        "BLUE": 2,
        "YELLOW": 3
    }
    color_type = TypeSystem.register_enum_type("Color", color_members)
    print(f"註冊枚舉類型 Color: {color_type}")

    # 註冊聯合類型
    union_fields = [
        ("i", ir.IntType(32)),
        ("f", ir.FloatType()),
        ("c", ir.IntType(8))
    ]
    number_type = TypeSystem.register_union_type("Number", union_fields)
    print(f"註冊聯合類型 Number: {number_type}")

    # 註冊函數類型
    fn_return = ir.IntType(32)
    fn_params = [ir.IntType(32), ir.FloatType()]
    fn_type = TypeSystem.register_function_type("calc_func", fn_return, fn_params)
    print(f"註冊函數類型 calc_func: {fn_type}")


def demonstrate_type_parsing():
    """展示類型解析功能"""
    types_to_parse = [
        "i32",               # 基本類型
        "i32*",              # 指針類型
        "i32[10]",           # 數組類型
        "(i32, f32)",        # 元組類型
        "Option<i32>",       # 泛型類型
        "Result<i32, f32>",  # 泛型類型
    ]

    for type_name in types_to_parse:
        llvm_type = TypeSystem.get_llvm_type(type_name)
        glux_type = TypeSystem.get_type(type_name)
        print(f"\n解析類型 '{type_name}':")
        print(f"  LLVM 類型: {llvm_type}")
        print(f"  類型種類: {glux_type.kind}")


def demonstrate_type_compatibility():
    """展示類型相容性檢查功能"""
    compatibility_checks = [
        ("i32", "i64"),     # 整數相容性
        ("f32", "f64"),     # 浮點相容性
        ("i32", "f32"),     # 整數到浮點相容性
        ("i8", "u8"),       # 有符號和無符號相容性
        ("i32*", "void*"),  # 指針相容性
        ("void*", "i32*"),  # void* 相容性
        ("i32[10]", "i32[5]"),  # 數組相容性 (不相容)
        ("i32", "Option<i32>"),  # Option 相容性
    ]

    for source, target in compatibility_checks:
        compatible = TypeSystem.is_type_compatible(source, target)
        print(f"'{source}' 相容於 '{target}': {compatible}")


def demonstrate_common_type():
    """展示共同類型推導功能"""
    type_pairs = [
        ("i32", "i64"),
        ("i8", "u16"),
        ("f32", "i32"),
        ("i32*", "void*"),
        ("i32", "f64"),
        ("i32", "Option<i32>"),
    ]

    for type1, type2 in type_pairs:
        common = TypeSystem.get_common_type(type1, type2)
        print(f"'{type1}' 和 '{type2}' 的共同類型: {common}")


def main():
    """主函數"""
    print("===== Glux 類型系統示例 =====")
    
    # 註冊自定義類型
    print("\n== 註冊自定義類型 ==")
    register_custom_types()
    
    # 示範類型解析
    print("\n== 類型解析示例 ==")
    demonstrate_type_parsing()
    
    # 示範類型相容性檢查
    print("\n== 類型相容性檢查 ==")
    demonstrate_type_compatibility()
    
    # 示範共同類型推導
    print("\n== 共同類型推導 ==")
    demonstrate_common_type()


if __name__ == "__main__":
    main() 