package main

import (
	"flag"
	"fmt"
	"os"

	"glux/internal/codegen"
	"glux/internal/lexer"
	"glux/internal/parser"
	"glux/internal/semantics"
)

func main() {
	// 解析命令列參數
	filePath := flag.String("file", "", "請指定 Glux 原始程式碼檔案")
	flag.Parse()

	if *filePath == "" {
		fmt.Println("錯誤：必須指定檔案路徑")
		os.Exit(1)
	}

	// 讀取原始程式碼
	source, err := os.ReadFile(*filePath)
	if err != nil {
		fmt.Printf("讀取檔案失敗: %v\n", err)
		os.Exit(1)
	}

	// 詞法分析：將原始程式碼轉成 token 列表
	tokens := lexer.Lex(string(source))

	// 語法分析：將 token 組合成抽象語法樹（AST）
	ast := parser.Parse(tokens)

	// 語意檢查與型別推導
	if err := semantics.Check(ast); err != nil {
		fmt.Printf("語意檢查錯誤: %v\n", err)
		os.Exit(1)
	}

	// 代碼生成：將 AST 轉換成 Go 程式碼
	goCode, err := codegen.Generate(ast)
	if err != nil {
		fmt.Printf("代碼生成錯誤: %v\n", err)
		os.Exit(1)
	}

	// 輸出生成的 Go 程式碼
	fmt.Println(goCode)
}
