#[derive(Debug)]
pub enum GluxError {
    /// **詞法分析錯誤**（如無效字元）
    LexerError(String),

    /// **語法分析錯誤**（如 `x := 5 +`）
    ParserError(String),

    /// **語義分析錯誤**（如變數未定義）
    SemanticError(String),

    /// **代碼生成錯誤**（如 LLVM 無法建立函數）
    CodegenError(String),

    /// **執行錯誤**（如函數運行時錯誤）
    RuntimeError(String),
}

impl std::fmt::Display for GluxError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            GluxError::LexerError(msg) => write!(f, "[Lexer Error] {}", msg),
            GluxError::ParserError(msg) => write!(f, "[Parser Error] {}", msg),
            GluxError::SemanticError(msg) => write!(f, "[Semantic Error] {}", msg),
            GluxError::CodegenError(msg) => write!(f, "[CodeGen Error] {}", msg),
            GluxError::RuntimeError(msg) => write!(f, "[Runtime Error] {}", msg),
        }
    }
}

impl std::error::Error for GluxError {}

/// **錯誤處理巨集**
///
/// ✅ **修正：現在可以支援 `format!()` 的變數插值**
///
/// 讓 `glux_error!(LexerError, "無效字元: {}", ch);` 正常運行
#[macro_export]
macro_rules! glux_error {
    ($variant:ident, $($arg:tt)*) => {
        Err(GluxError::$variant(format!($($arg)*)))
    };
}

// **讓其他模組可以使用 `glux_error!`**
pub use glux_error;
