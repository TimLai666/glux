package main

import (
	"fmt"
	"log"
	"os"

	"glux/internal/codegen"
	"glux/internal/lexer"
	"glux/internal/parser"
	"glux/internal/semantics"

	cli "github.com/urfave/cli/v2"
)

func main() {
	app := &cli.App{
		Name:  "gluxc",
		Usage: "Compile Glux source code into Go code",
		Flags: []cli.Flag{
			&cli.StringFlag{
				Name:    "file",
				Aliases: []string{"f"},
				Usage:   "Glux source file to compile",
			},
		},
		Action: func(c *cli.Context) error {
			filePath := c.String("file")
			if filePath == "" {
				return fmt.Errorf("please specify a Glux source file using --file or -f flag")
			}

			source, err := os.ReadFile(filePath)
			if err != nil {
				return fmt.Errorf("failed to read file: %v", err)
			}

			// 詞法分析：將原始程式碼轉成 token 列表
			tokens := lexer.Lex(string(source))

			// 語法分析：將 token 組合成抽象語法樹（AST）
			ast := parser.Parse(tokens)

			// 語意檢查與型別推導
			if err := semantics.Check(ast); err != nil {
				return fmt.Errorf("semantic error: %v", err)
			}

			// 代碼生成：將 AST 轉換成 Go 程式碼
			goCode, err := codegen.Generate(ast)
			if err != nil {
				return fmt.Errorf("code generation error: %v", err)
			}

			// 輸出生成的 Go 程式碼
			fmt.Println(goCode)
			return nil
		},
	}

	if err := app.Run(os.Args); err != nil {
		log.Fatal(err)
	}
}
