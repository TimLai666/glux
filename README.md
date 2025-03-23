# Glux 程式語言

Glux 是一門簡單、高效、省記憶體、支援併發、可編譯為二進制的靜態型別語言，擁有直覺的語法，結合了 Python、Go、Rust 的優勢。

## 環境設置

### 前置需求

- [Rust](https://www.rust-lang.org/) (cargo、rustc)
- C++ 編譯器 (如 Visual Studio、GCC 或 Clang)

### 編譯專案

Glux 已配置為自動下載並構建所需的 LLVM 套件，您無需手動安裝 LLVM。

```bash
# 使用 cargo 編譯專案
cargo build

# 或直接運行
cargo run
```

**注意：** 首次編譯時需要下載並構建 LLVM，這個過程可能需要 10-60 分鐘，取決於您的電腦性能。後續編譯將會明顯加快。

## 文件結構

詳細的專案架構可以參考 [專案架構](專案架構.md) 文件。

## 語言規範

Glux 語言設計規範可以在 [語言規範](語言規範.md) 文件中找到。

## 常見問題

### 編譯時間過長

首次編譯時，系統需要下載並構建 LLVM，這個過程可能需要 10-60 分鐘。後續編譯會變快，因為 LLVM 已經構建完成。

### 構建 LLVM 時的系統需求

- 最低 4GB 記憶體 (推薦 8GB 或以上)
- 約 2-3GB 的硬碟空間
- 多核心 CPU 可加速構建過程

### 構建失敗

如果自動構建 LLVM 失敗，可能的原因包括：

1. 記憶體不足
2. 缺少必要的構建工具
3. 網絡連接問題

嘗試解決方案：

1. 關閉其他佔用記憶體的應用程式
2. 確保已安裝 CMake 和 C++ 編譯器
3. 檢查網絡連接，嘗試使用 VPN 或代理

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

1. 編譯並執行程式 (使用JIT模式)：
   ```bash
   python main.py run <檔案路徑>
   ```
   例如：
   ```bash
   python main.py run examples/hello.glux
   ```

2. 編譯為可執行檔案：
   ```bash
   python main.py build -o <輸出檔案名> <檔案路徑>
   ```
   例如：
   ```bash
   python main.py build -o hello examples/hello.glux
   ```

3. 傳遞參數給程式：
   ```bash
   python main.py run <檔案路徑> -- <參數1> <參數2> ...
   ```

### 命令列選項

#### `run` 子命令
- `-v` 或 `--verbose`：顯示詳細的編譯過程
- `--args`：在 `--` 之後傳遞參數給程式

#### `build` 子命令
- `-o` 或 `--output`：指定輸出文件路徑
- `-v` 或 `--verbose`：顯示詳細的編譯過程

### 向後兼容性

為了保持向後兼容，仍然支持以下舊的命令形式：

```bash
python main.py <檔案路徑>           # 直接執行 (使用JIT模式)
python main.py -c -o <輸出檔案> <檔案路徑>  # 編譯為可執行檔案
```

但建議使用新的子命令形式，更加直觀。

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