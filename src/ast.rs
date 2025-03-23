#[derive(Debug, Clone)]
pub enum ASTNode {
    // 數值與標識符
    Number(String),
    StringLiteral(String),
    Identifier(String),

    // 二元運算
    BinaryOp {
        op: String,
        left: Box<ASTNode>,
        right: Box<ASTNode>,
    },

    // 變數宣告
    VariableDeclaration {
        name: String,
        value: Box<ASTNode>,
    },

    // 賦值語句
    Assignment {
        name: String,
        value: Box<ASTNode>,
    },

    // 函式定義
    FunctionDefinition {
        name: String,
        params: Vec<String>,
        body: Vec<ASTNode>,
    },

    // 函式呼叫
    FunctionCall {
        name: String,
        args: Vec<ASTNode>,
    },

    // if-else 語句
    IfStatement {
        condition: Box<ASTNode>,
        then_branch: Vec<ASTNode>,
        else_branch: Option<Vec<ASTNode>>,
    },

    // while 迴圈
    WhileLoop {
        condition: Box<ASTNode>,
        body: Vec<ASTNode>,
    },

    // for 迴圈
    ForLoop {
        iterator: String,
        range: Box<ASTNode>,
        body: Vec<ASTNode>,
    },

    // return 語句
    ReturnStatement {
        value: Option<Box<ASTNode>>,
    },

    // 內建函式
    BuiltinFunction {
        name: String,
        args: Vec<ASTNode>,
    },
}
