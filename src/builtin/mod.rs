// 確保 `builtin.rs` 被載入
pub mod builtin;

// 讓外部可以直接使用 `BuiltinManager`
pub use builtin::*;
