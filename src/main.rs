// 移除未使用的導入
// use std::env;
// use std::fs;
// use std::process;

// 引入各個模組
mod ast;
mod builtin;
mod codegen;
mod error;
mod keyword;
mod lexer;
mod parser;
mod semantic;

fn main() {
    println!("GLux 編譯器 (使用 Cranelift 後端)");

    // 測試代碼生成
    match codegen::generate_arithmetic_example() {
        Ok(result) => println!("代碼生成測試 - 計算結果: {}", result),
        Err(e) => eprintln!("代碼生成錯誤: {}", e),
    }
}
