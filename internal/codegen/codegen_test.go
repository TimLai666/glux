package codegen

import (
	"glux/internal/lexer"
	"glux/internal/parser"
	"strings"
	"testing"
)

func TestGenerateSimpleProgram(t *testing.T) {
	input := `
var x = 42
var y = "hello"
var z = true

fn add(a int, b int) int {
	return a + b
}

main {
	var result = add(x, 10)
	println(result)
	println(y)
}
`

	tokens := lexer.Lex(input)
	p := parser.New(tokens)
	program := p.ParseProgram()

	if len(p.Errors()) > 0 {
		t.Fatalf("parser has %d errors: %v", len(p.Errors()), p.Errors())
	}

	code, err := Generate(program)
	if err != nil {
		t.Fatalf("code generation failed: %s", err)
	}

	// 檢查生成的代碼是否包含預期內容
	expectedParts := []string{
		"package main",
		"import",
		"fmt",
		"var x = 42",
		"var y = \"hello\"",
		"var z = true",
		"func add(a int, b int) int {",
		"return a + b",
		"func main() {",
		"var result = add(x, 10)",
		"fmt.Println(result)",
		"fmt.Println(y)",
	}

	for _, part := range expectedParts {
		if !strings.Contains(code, part) {
			t.Errorf("generated code doesn't contain expected part: %s", part)
			t.Logf("Generated code:\n%s", code)
		}
	}
}

func TestGenerateStructAndMethod(t *testing.T) {
	input := `
struct Person {
	name string
	age int = 0
}

fn Person.greet() string {
	return "Hello, my name is " + this.name + "!"
}

main {
	var p = Person { name: "Alice", age: 30 }
	println(p.greet())
}
`

	tokens := lexer.Lex(input)
	p := parser.New(tokens)
	program := p.ParseProgram()

	if len(p.Errors()) > 0 {
		t.Fatalf("parser has %d errors: %v", len(p.Errors()), p.Errors())
	}

	code, err := Generate(program)
	if err != nil {
		t.Fatalf("code generation failed: %s", err)
	}

	// 檢查生成的代碼是否包含預期內容
	expectedParts := []string{
		"type Person struct {",
		"name string",
		"age int",
		"func (this Person) greet() string {",
		"return \"Hello, my name is \" + this.name + \"!\"",
		"func main() {",
		"var p = Person{name: \"Alice\", age: 30}",
		"fmt.Println(p.greet())",
	}

	for _, part := range expectedParts {
		if !strings.Contains(code, part) {
			t.Errorf("generated code doesn't contain expected part: %s", part)
			t.Logf("Generated code:\n%s", code)
		}
	}
}

func TestGenerateControlFlow(t *testing.T) {
	input := `
main {
	var x = 10
	
	if x > 5 {
		println("x is greater than 5")
	} else {
		println("x is not greater than 5")
	}
	
	var i = 0
	while i < 5 {
		println(i)
		i = i + 1
	}
	
	for value in range(5) {
		println(value)
	}
	
	var list = [1, 2, 3, 4, 5]
	for index, value in list {
		println(index, value)
	}
}
`

	tokens := lexer.Lex(input)
	p := parser.New(tokens)
	program := p.ParseProgram()

	if len(p.Errors()) > 0 {
		t.Fatalf("parser has %d errors: %v", len(p.Errors()), p.Errors())
	}

	code, err := Generate(program)
	if err != nil {
		t.Fatalf("code generation failed: %s", err)
	}

	// 檢查生成的代碼是否包含預期內容
	expectedParts := []string{
		"var x = 10",
		"if x > 5 {",
		"fmt.Println(\"x is greater than 5\")",
		"} else {",
		"fmt.Println(\"x is not greater than 5\")",
		"var i = 0",
		"for i < 5 {",
		"fmt.Println(i)",
		"i = i + 1",
		"for _, value := range",
		"fmt.Println(value)",
		"var list = []interface{}{1, 2, 3, 4, 5}",
		"for index, value := range list {",
		"fmt.Println(index, value)",
	}

	for _, part := range expectedParts {
		if !strings.Contains(code, part) {
			t.Errorf("generated code doesn't contain expected part: %s", part)
			t.Logf("Generated code:\n%s", code)
		}
	}
}

func TestGenerateComplexExpressions(t *testing.T) {
	input := `
main {
	var x = 10
	var y = 20
	
	// 測試三元運算符
	var max = x > y ? x : y
	println(max)
	
	// 測試列表和索引
	var list = [1, 2, 3, 4, 5]
	println(list[2])
	
	// 測試映射
	var map = { "a": 1, "b": 2, "c": 3 }
	println(map["b"])
	
	// 測試函數字面量
	var square = fn(n int) int { return n * n }
	println(square(5))
}
`

	tokens := lexer.Lex(input)
	p := parser.New(tokens)
	program := p.ParseProgram()

	if len(p.Errors()) > 0 {
		t.Fatalf("parser has %d errors: %v", len(p.Errors()), p.Errors())
	}

	code, err := Generate(program)
	if err != nil {
		t.Fatalf("code generation failed: %s", err)
	}

	// 檢查生成的代碼是否包含預期內容
	expectedParts := []string{
		"var x = 10",
		"var y = 20",
		"var _temp",
		"if x > y {",
		"_temp = x",
		"} else {",
		"_temp = y",
		"var max =",
		"var list = []interface{}{1, 2, 3, 4, 5}",
		"fmt.Println(list[2])",
		"var map = map[interface{}]interface{}{\"a\": 1, \"b\": 2, \"c\": 3}",
		"fmt.Println(map[\"b\"])",
		"var square = func(n int) int {",
		"return n * n",
		"fmt.Println(square(5))",
	}

	for _, part := range expectedParts {
		if !strings.Contains(code, part) {
			t.Errorf("generated code doesn't contain expected part: %s", part)
			t.Logf("Generated code:\n%s", code)
		}
	}
}

// 測試生成代碼的執行情況
func TestGenerateCompilableCode(t *testing.T) {
	// 這個測試需要在真實環境中運行，並使用 Go 編譯器編譯生成的代碼
	// 在單元測試中我們只檢查代碼結構是否正確

	input := `
fn fibonacci(n int) int {
	if n <= 1 {
		return n
	}
	return fibonacci(n-1) + fibonacci(n-2)
}

main {
	for i in range(10) {
		println(fibonacci(i))
	}
}
`

	tokens := lexer.Lex(input)
	p := parser.New(tokens)
	program := p.ParseProgram()

	if len(p.Errors()) > 0 {
		t.Fatalf("parser has %d errors: %v", len(p.Errors()), p.Errors())
	}

	code, err := Generate(program)
	if err != nil {
		t.Fatalf("code generation failed: %s", err)
	}

	// 檢查生成的代碼是否包含預期內容
	expectedParts := []string{
		"func fibonacci(n int) int {",
		"if n <= 1 {",
		"return n",
		"return fibonacci(n-1) + fibonacci(n-2)",
		"func main() {",
		"for _, i := range",
		"fmt.Println(fibonacci(i))",
	}

	for _, part := range expectedParts {
		if !strings.Contains(code, part) {
			t.Errorf("generated code doesn't contain expected part: %s", part)
			t.Logf("Generated code:\n%s", code)
		}
	}
}
