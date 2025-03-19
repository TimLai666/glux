"""
類型系統測試
測試 Glux 類型系統是否符合語言規範
"""

import unittest
from llvmlite import ir
from src.glux.type_system.type_defs import GluxType, TypeKind, NumericType
from src.glux.type_system.type_generator import TypeGenerator


class TestTypeSystem(unittest.TestCase):
    """
    類型系統測試類
    """
    
    def setUp(self):
        """測試前準備"""
        self.module = ir.Module(name="test_module")
        self.type_gen = TypeGenerator(self.module)
    
    def test_primitive_types(self):
        """測試基本類型"""
        # 測試整數類型
        self.assertEqual(self.type_gen.int8_type.name, "int8")
        self.assertEqual(self.type_gen.int8_type.kind, TypeKind.PRIMITIVE)
        self.assertEqual(self.type_gen.int8_type.numeric_type, NumericType.INT8)
        self.assertTrue(self.type_gen.int8_type.is_signed)
        
        # 測試無符號整數類型
        self.assertEqual(self.type_gen.uint32_type.name, "uint32")
        self.assertEqual(self.type_gen.uint32_type.kind, TypeKind.PRIMITIVE)
        self.assertEqual(self.type_gen.uint32_type.numeric_type, NumericType.UINT32)
        self.assertFalse(self.type_gen.uint32_type.is_signed)
        
        # 測試浮點類型
        self.assertEqual(self.type_gen.float32_type.name, "float32")
        self.assertEqual(self.type_gen.float32_type.kind, TypeKind.PRIMITIVE)
        self.assertEqual(self.type_gen.float32_type.numeric_type, NumericType.FLOAT32)
        
        # 測試布爾類型
        self.assertEqual(self.type_gen.bool_type.name, "bool")
        self.assertEqual(self.type_gen.bool_type.kind, TypeKind.PRIMITIVE)
        
        # 測試字符類型
        self.assertEqual(self.type_gen.char_type.name, "char")
        self.assertEqual(self.type_gen.char_type.kind, TypeKind.PRIMITIVE)
        
        # 測試字符串類型
        self.assertEqual(self.type_gen.string_type.name, "string")
        self.assertEqual(self.type_gen.string_type.kind, TypeKind.POINTER)
        self.assertEqual(self.type_gen.string_type.element_type, self.type_gen.char_type)
    
    def test_pointer_type(self):
        """測試指針類型"""
        int_ptr_type = self.type_gen.create_pointer_type(self.type_gen.int32_type)
        self.assertEqual(int_ptr_type.name, "*int32")
        self.assertEqual(int_ptr_type.kind, TypeKind.POINTER)
        self.assertEqual(int_ptr_type.element_type, self.type_gen.int32_type)
        
        # 測試多級指針
        int_ptr_ptr_type = self.type_gen.create_pointer_type(int_ptr_type)
        self.assertEqual(int_ptr_ptr_type.name, "**int32")
        self.assertEqual(int_ptr_ptr_type.kind, TypeKind.POINTER)
        self.assertEqual(int_ptr_ptr_type.element_type, int_ptr_type)
    
    def test_array_type(self):
        """測試數組類型"""
        int_array_type = self.type_gen.create_array_type(self.type_gen.int32_type, 10)
        self.assertEqual(int_array_type.name, "[10]int32")
        self.assertEqual(int_array_type.kind, TypeKind.ARRAY)
        self.assertEqual(int_array_type.element_type, self.type_gen.int32_type)
        self.assertEqual(int_array_type.size, 10)
    
    def test_tuple_type(self):
        """測試元組類型"""
        tuple_type = self.type_gen.create_tuple_type([
            self.type_gen.int32_type,
            self.type_gen.float64_type,
            self.type_gen.string_type
        ])
        self.assertEqual(tuple_type.name, "(int32, float64, string)")
        self.assertEqual(tuple_type.kind, TypeKind.TUPLE)
        self.assertEqual(len(tuple_type.element_types), 3)
        self.assertEqual(tuple_type.element_types[0], self.type_gen.int32_type)
        self.assertEqual(tuple_type.element_types[1], self.type_gen.float64_type)
        self.assertEqual(tuple_type.element_types[2], self.type_gen.string_type)
    
    def test_list_type(self):
        """測試列表類型"""
        list_type = self.type_gen.create_list_type(self.type_gen.int32_type)
        self.assertEqual(list_type.name, "list<int32>")
        self.assertEqual(list_type.kind, TypeKind.LIST)
        self.assertEqual(list_type.element_type, self.type_gen.int32_type)
    
    def test_map_type(self):
        """測試映射類型"""
        map_type = self.type_gen.create_map_type(self.type_gen.string_type, self.type_gen.int32_type)
        self.assertEqual(map_type.name, "map<string, int32>")
        self.assertEqual(map_type.kind, TypeKind.MAP)
        self.assertEqual(map_type.key_type, self.type_gen.string_type)
        self.assertEqual(map_type.value_type, self.type_gen.int32_type)
    
    def test_struct_type(self):
        """測試結構體類型"""
        struct_type = self.type_gen.create_struct_type(
            "Person",
            [self.type_gen.string_type, self.type_gen.int32_type],
            ["name", "age"]
        )
        self.assertEqual(struct_type.name, "Person")
        self.assertEqual(struct_type.kind, TypeKind.STRUCT)
        self.assertEqual(len(struct_type.field_types), 2)
        self.assertEqual(struct_type.field_types[0], self.type_gen.string_type)
        self.assertEqual(struct_type.field_types[1], self.type_gen.int32_type)
        self.assertEqual(struct_type.field_names, ["name", "age"])
    
    def test_union_type(self):
        """測試聯合類型"""
        union_type = self.type_gen.create_union_type([
            self.type_gen.int32_type,
            self.type_gen.string_type,
            self.type_gen.error_type
        ])
        self.assertEqual(union_type.name, "int32 | string | error")
        self.assertEqual(union_type.kind, TypeKind.UNION)
        self.assertEqual(len(union_type.union_types), 3)
        self.assertEqual(union_type.union_types[0], self.type_gen.int32_type)
        self.assertEqual(union_type.union_types[1], self.type_gen.string_type)
        self.assertEqual(union_type.union_types[2], self.type_gen.error_type)
    
    def test_function_type(self):
        """測試函數類型"""
        func_type = self.type_gen.create_function_type(
            self.type_gen.int32_type,
            [self.type_gen.string_type, self.type_gen.int32_type],
            ["name", "age"]
        )
        self.assertEqual(func_type.name, "fn(string, int32) -> int32")
        self.assertEqual(func_type.kind, TypeKind.FUNCTION)
        self.assertEqual(func_type.return_type, self.type_gen.int32_type)
        self.assertEqual(len(func_type.param_types), 2)
        self.assertEqual(func_type.param_types[0], self.type_gen.string_type)
        self.assertEqual(func_type.param_types[1], self.type_gen.int32_type)
        self.assertEqual(func_type.param_names, ["name", "age"])
    
    def test_interface_type(self):
        """測試接口類型"""
        # 創建方法類型
        greet_func = self.type_gen.create_function_type(
            self.type_gen.string_type,
            [self.type_gen.string_type],
            ["name"]
        )
        
        get_age_func = self.type_gen.create_function_type(
            self.type_gen.int32_type,
            [],
            []
        )
        
        # 創建接口類型
        interface_type = self.type_gen.create_interface_type(
            "Greeter",
            {
                "greet": greet_func,
                "getAge": get_age_func
            }
        )
        
        self.assertEqual(interface_type.name, "Greeter")
        self.assertEqual(interface_type.kind, TypeKind.INTERFACE)
        self.assertEqual(len(interface_type.methods), 2)
        self.assertEqual(interface_type.methods["greet"], greet_func)
        self.assertEqual(interface_type.methods["getAge"], get_age_func)
    
    def test_optional_type(self):
        """測試可選類型"""
        opt_type = self.type_gen.create_optional_type(self.type_gen.int32_type)
        self.assertEqual(opt_type.name, "?int32")
        self.assertEqual(opt_type.kind, TypeKind.OPTIONAL)
        self.assertEqual(opt_type.element_type, self.type_gen.int32_type)
    
    def test_numeric_type_deduction(self):
        """測試數值類型推導"""
        # 整數類型推導
        self.assertEqual(self.type_gen.deduce_numeric_type(10).numeric_type, NumericType.INT8)
        self.assertEqual(self.type_gen.deduce_numeric_type(200).numeric_type, NumericType.INT16)
        self.assertEqual(self.type_gen.deduce_numeric_type(70000).numeric_type, NumericType.INT32)
        self.assertEqual(self.type_gen.deduce_numeric_type(10000000000).numeric_type, NumericType.INT64)
        
        # 浮點類型推導
        self.assertEqual(self.type_gen.deduce_numeric_type(3.14).numeric_type, NumericType.FLOAT32)
        self.assertEqual(self.type_gen.deduce_numeric_type(1e100).numeric_type, NumericType.FLOAT64)
    
    def test_widest_numeric_type(self):
        """測試獲取較寬數值類型"""
        # 測試同類型
        self.assertEqual(
            self.type_gen.get_widest_numeric_type(self.type_gen.int8_type, self.type_gen.int16_type),
            self.type_gen.int16_type
        )
        
        # 測試整數和浮點
        self.assertEqual(
            self.type_gen.get_widest_numeric_type(self.type_gen.int32_type, self.type_gen.float32_type),
            self.type_gen.float32_type
        )
        
        # 測試有符號和無符號
        self.assertEqual(
            self.type_gen.get_widest_numeric_type(self.type_gen.uint16_type, self.type_gen.int32_type),
            self.type_gen.int32_type
        )
    
    def test_type_conversion(self):
        """測試類型轉換"""
        # 相同類型
        self.assertTrue(self.type_gen.can_convert(self.type_gen.int32_type, self.type_gen.int32_type))
        
        # null 到指針或可選類型
        self.assertTrue(self.type_gen.can_convert(
            self.type_gen.null_type,
            self.type_gen.create_pointer_type(self.type_gen.int32_type)
        ))
        self.assertTrue(self.type_gen.can_convert(
            self.type_gen.null_type,
            self.type_gen.create_optional_type(self.type_gen.string_type)
        ))
        
        # 整數到浮點
        self.assertTrue(self.type_gen.can_convert(self.type_gen.int32_type, self.type_gen.float64_type))
        
        # 小寬度到大寬度
        self.assertTrue(self.type_gen.can_convert(self.type_gen.int8_type, self.type_gen.int16_type))
        self.assertTrue(self.type_gen.can_convert(self.type_gen.uint8_type, self.type_gen.uint16_type))
        self.assertTrue(self.type_gen.can_convert(self.type_gen.float32_type, self.type_gen.float64_type))
        
        # 任意類型到 any
        self.assertTrue(self.type_gen.can_convert(self.type_gen.int32_type, self.type_gen.any_type))
        self.assertTrue(self.type_gen.can_convert(self.type_gen.string_type, self.type_gen.any_type))
        
        # 普通類型到可選類型
        self.assertTrue(self.type_gen.can_convert(
            self.type_gen.int32_type,
            self.type_gen.create_optional_type(self.type_gen.int32_type)
        ))
        
        # 不允許的轉換
        self.assertFalse(self.type_gen.can_convert(self.type_gen.int32_type, self.type_gen.string_type))
        self.assertFalse(self.type_gen.can_convert(
            self.type_gen.float32_type,
            self.type_gen.create_optional_type(self.type_gen.int32_type)
        ))


if __name__ == "__main__":
    unittest.main() 