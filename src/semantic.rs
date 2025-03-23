use crate::ast::ASTNode;
use crate::error::{GluxError, glux_error};
use std::collections::HashMap;

/// **語義錯誤類型**
#[derive(Debug)]
pub enum SemanticError {
    UndefinedVariable(String),
    TypeMismatch(String),
    DuplicateVariable(String),
    FunctionNotDefined(String),
}

impl std::fmt::Display for SemanticError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match self {
            SemanticError::UndefinedVariable(name) => write!(f, "Undefined variable: {}", name),
            SemanticError::TypeMismatch(msg) => write!(f, "Type mismatch: {}", msg),
            SemanticError::DuplicateVariable(name) => write!(f, "Duplicate variable: {}", name),
            SemanticError::FunctionNotDefined(name) => write!(f, "Function not defined: {}", name),
        }
    }
}

impl std::error::Error for SemanticError {}

/// **型別推導與檢查**
pub struct TypeChecker;

impl TypeChecker {
    /// **推導 AST 節點的型別**
    pub fn infer_type(
        node: &ASTNode,
        variables: &HashMap<String, String>,
    ) -> Result<String, SemanticError> {
        match node {
            ASTNode::Number(_) => Ok("int".to_string()),
            ASTNode::StringLiteral(_) => Ok("string".to_string()),
            ASTNode::Identifier(name) => variables
                .get(name)
                .cloned()
                .ok_or(SemanticError::UndefinedVariable(name.clone())),
            ASTNode::BinaryOp { op, left, right } => {
                let left_type = Self::infer_type(left, variables)?;
                let right_type = Self::infer_type(right, variables)?;
                if left_type == right_type {
                    Ok(left_type) // 如果左右型別相同，回傳該型別
                } else {
                    glux_error!(
                        TypeMismatch,
                        "Cannot apply '{}' between {} and {}",
                        op,
                        left_type,
                        right_type
                    )
                }
            }
            _ => glux_error!(TypeMismatch, "Unknown type inference for {:?}", node),
        }
    }
}

/// **語義分析器**
pub struct SemanticAnalyzer {
    variables: HashMap<String, String>, // 變數表（變數名稱 -> 型別）
    functions: HashMap<String, (usize, String)>, // 函式表（名稱 -> 參數數量, 回傳型別）
}

impl SemanticAnalyzer {
    /// **建立語義分析器**
    pub fn new() -> Self {
        Self {
            variables: HashMap::new(),
            functions: HashMap::new(),
        }
    }

    /// **執行語義分析**
    pub fn analyze(&mut self, ast: ASTNode) -> Result<ASTNode, SemanticError> {
        self.visit(&ast)?;
        Ok(ast)
    }

    /// **遞迴分析 AST**
    fn visit(&mut self, node: &ASTNode) -> Result<(), SemanticError> {
        match node {
            ASTNode::Number(_) | ASTNode::StringLiteral(_) => Ok(()), // 基本類型無需分析

            ASTNode::Identifier(name) => {
                if !self.variables.contains_key(name) {
                    return glux_error!(UndefinedVariable, "Variable '{}' is not defined", name);
                }
                Ok(())
            }

            ASTNode::BinaryOp { left, right, .. } => {
                self.visit(left)?;
                self.visit(right)?;
                TypeChecker::infer_type(node, &self.variables)?; // 檢查運算子型別
                Ok(())
            }

            ASTNode::VariableDeclaration { name, value } => {
                if self.variables.contains_key(name) {
                    return glux_error!(DuplicateVariable, "Variable '{}' already defined", name);
                }
                let inferred_type = TypeChecker::infer_type(value, &self.variables)?;
                self.variables.insert(name.clone(), inferred_type);
                self.visit(value)
            }

            ASTNode::Assignment { name, value } => {
                if !self.variables.contains_key(name) {
                    return glux_error!(UndefinedVariable, "Variable '{}' is not defined", name);
                }
                let expected_type = self.variables.get(name).unwrap();
                let assigned_type = TypeChecker::infer_type(value, &self.variables)?;
                if expected_type != &assigned_type {
                    return glux_error!(
                        TypeMismatch,
                        "Cannot assign {} to '{}', expected {}",
                        assigned_type,
                        name,
                        expected_type
                    );
                }
                self.visit(value)
            }

            ASTNode::FunctionDefinition { name, params, body } => {
                self.functions
                    .insert(name.clone(), (params.len(), "void".to_string()));
                let mut local_scope = SemanticAnalyzer::new();
                for param in params {
                    local_scope
                        .variables
                        .insert(param.clone(), "auto".to_string());
                }
                for stmt in body {
                    local_scope.visit(stmt)?;
                }
                Ok(())
            }

            ASTNode::FunctionCall { name, args } => {
                if let Some((param_count, _)) = self.functions.get(name) {
                    if *param_count != args.len() {
                        return glux_error!(
                            TypeMismatch,
                            "Function '{}' expects {} arguments, but got {}",
                            name,
                            param_count,
                            args.len()
                        );
                    }
                    for arg in args {
                        self.visit(arg)?;
                    }
                    Ok(())
                } else {
                    glux_error!(FunctionNotDefined, "Function '{}' is not defined", name)
                }
            }

            ASTNode::IfStatement {
                condition,
                then_branch,
                else_branch,
            } => {
                self.visit(condition)?;
                for stmt in then_branch {
                    self.visit(stmt)?;
                }
                if let Some(else_body) = else_branch {
                    for stmt in else_body {
                        self.visit(stmt)?;
                    }
                }
                Ok(())
            }

            ASTNode::WhileLoop { condition, body } => {
                self.visit(condition)?;
                for stmt in body {
                    self.visit(stmt)?;
                }
                Ok(())
            }

            ASTNode::ForLoop {
                iterator,
                range,
                body,
            } => {
                self.visit(range)?;
                self.variables.insert(iterator.clone(), "int".to_string());
                for stmt in body {
                    self.visit(stmt)?;
                }
                Ok(())
            }

            ASTNode::ReturnStatement { value } => {
                if let Some(val) = value {
                    self.visit(val)?;
                }
                Ok(())
            }

            ASTNode::BuiltinFunction { name, args } => {
                for arg in args {
                    self.visit(arg)?;
                }
                Ok(())
            }

            _ => glux_error!(TypeMismatch, "Unhandled AST node: {:?}", node),
        }
    }
}

/// **外部函數：執行語義分析**
pub fn analyze(ast: ASTNode) -> Result<ASTNode, SemanticError> {
    let mut analyzer = SemanticAnalyzer::new();
    analyzer.analyze(ast)
}
