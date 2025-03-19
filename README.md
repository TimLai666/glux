# Glux 程式語言

Glux 是一個現代化的程式語言，專注於提供安全、高效和易用的程式設計體驗。

## 功能特點

- 靜態類型系統
- 自動類型推導
- 錯誤處理機制
- 併發程式設計支援
- 字串插值
- 連續比較運算
- 結構化程式設計
- 函數式程式設計特性

## 安裝

1. 確保已安裝 Python 3.8 或更高版本
2. 安裝依賴套件：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

### 基本使用

1. 編譯並執行程式：
   ```bash
   python main <檔案路徑> -j
   ```
   例如：
   ```bash
   python3 -m src.glux.main tests/examples/test_basic.glux -j
   ```

2. 只檢查語法和語義：
   ```bash
   python main <檔案路徑> -c
   ```

3. 生成 LLVM IR：
   ```bash
   python main <檔案路徑> -i
   ```

### 命令列選項

- `-j` 或 `--jit`：使用 JIT 模式直接執行 LLVM IR
- `-c` 或 `--check`：只進行語法和語義檢查
- `-i` 或 `--ir`：生成 LLVM IR 並保存到文件
- `-v` 或 `--verbose`：顯示詳細的編譯過程
- `-o` 或 `--output`：指定輸出文件路徑

## 語言特性

### 1. 基本語法

```glux
// 變數宣告
x := 10
y := "Hello"

// 常數宣告
const PI = 3.14159

// 函數定義
fn add(a: int, b: int) -> int {
    return a + b
}

// 條件語句
if x > 0 {
    println("正數")
} else {
    println("非正數")
}

// 循環
for i in range(10) {
    println(i)
}

// while 循環
while x > 0 {
    x -= 1
}
```

### 2. 字串插值

```glux
name := "Alice"
age := 30
greeting := `您好，${name}！您今年 ${age} 歲。`
```

### 3. 錯誤處理

```glux
fn divide(a: int, b: int) -> union<int, error> {
    if b == 0 {
        return error("除數不能為零")
    }
    return a / b
}

result := divide(10, 0)
if is_error(result) {
    println(`錯誤：${result}`)
} else {
    println(`結果：${result}`)
}
```

### 4. 併發程式設計

```glux
fn task1() {
    println("任務 1 開始")
    sleep(1)
    println("任務 1 結束")
}

fn task2() {
    println("任務 2 開始")
    sleep(1)
    println("任務 2 結束")
}

// 啟動併發任務
t1 := spawn task1()
t2 := spawn task2()

// 等待任務完成
await t1, t2
```

### 5. 連續比較運算

```glux
x := 5
if 0 < x < 10 {
    println("x 在 0 到 10 之間")
}
```

## 開發狀態

目前 Glux 編譯器仍在積極開發中，已實現的功能包括：

- [x] 詞法分析器
- [x] 語法分析器
- [x] 語義分析器
- [x] LLVM IR 代碼生成
- [x] JIT 執行
- [x] 基本類型系統
- [x] 錯誤處理機制
- [x] 字串插值
- [x] 連續比較運算
- [x] 併發程式設計基礎設施

正在開發的功能：

- [ ] 完整的標準庫
- [ ] 更多的優化
- [ ] 更好的錯誤訊息
- [ ] 更多的語言特性

## 貢獻

歡迎提交 Issue 和 Pull Request 來幫助改進 Glux 語言。

## 授權

本專案採用 MIT 授權條款。