use super::KeywordHandler;
use crate::ast::{ASTNode, ReturnNode};
use crate::error::GluxError;
use crate::lexer::Token;
use crate::parser::Parser;

/// Return 關鍵字處理器
pub struct ReturnHandler;

impl KeywordHandler for ReturnHandler {
    fn parse(&self, tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        // 消耗 "return" 關鍵字
        tokens.remove(0);

        // 如果後面沒有表達式，則為空返回
        if tokens.is_empty() || tokens[0].value == ";" {
            return Ok(ASTNode::Return(ReturnNode { expression: None }));
        }

        // 解析返回表達式
        let expression = Parser::parse_expression(tokens)?;

        Ok(ASTNode::Return(ReturnNode {
            expression: Some(Box::new(expression)),
        }))
    }
}
