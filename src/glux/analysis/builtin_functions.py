# 添加或更新內建函數定義
BUILTIN_FUNCTIONS = {
    # 現有的內建函數
    # ...
    
    # 強制類型轉換函數
    "string": {
        "return_type": "string",
        "params": [{"name": "value", "type": "any"}],
        "description": "將任何類型轉換為字符串"
    },
    "int": {
        "return_type": "int",
        "params": [{"name": "value", "type": "any"}],
        "description": "將值轉換為整數類型"
    },
    "float": {
        "return_type": "float",
        "params": [{"name": "value", "type": "any"}],
        "description": "將值轉換為浮點數類型"
    },
    "bool": {
        "return_type": "bool",
        "params": [{"name": "value", "type": "any"}],
        "description": "將值轉換為布爾類型"
    },
    
    # 其他內建函數
    "len": {
        "return_type": "int",
        "params": [{"name": "collection", "type": "any"}],
        "description": "返回集合的長度"
    },
    "copy": {
        "return_type": "any",
        "params": [{"name": "value", "type": "any"}],
        "description": "返回值的深拷貝"
    },
    "sleep": {
        "return_type": "void",
        "params": [{"name": "seconds", "type": "float"}],
        "description": "暫停執行指定的秒數"
    },
    "error": {
        "return_type": "error",
        "params": [{"name": "message", "type": "string"}],
        "description": "創建一個錯誤物件"
    },
    "is_error": {
        "return_type": "bool",
        "params": [{"name": "value", "type": "any"}],
        "description": "檢查值是否為錯誤"
    }
} 