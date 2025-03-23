use super::KeywordHandler;
use crate::ast::{ASTNode, SpawnNode};
use crate::error::GluxError;
use crate::lexer::Token;
use crate::parser::Parser;

/// Spawn 關鍵字處理器
pub struct SpawnHandler;

impl KeywordHandler for SpawnHandler {
    fn parse(&self, tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        // 消耗 "spawn" 關鍵字
        tokens.remove(0);

        // 解析要執行的函數表達式
        let function_expr = Parser::parse_expression(tokens)?;

        Ok(ASTNode::Spawn(SpawnNode {
            function: Box::new(function_expr),
        }))
    }
}
