use super::KeywordHandler;
use crate::ast::{ASTNode, AwaitNode};
use crate::error::GluxError;
use crate::lexer::Token;
use crate::parser::Parser;

/// Await 關鍵字處理器
pub struct AwaitHandler;

impl KeywordHandler for AwaitHandler {
    fn parse(&self, tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        // 消耗 "await" 關鍵字
        tokens.remove(0);

        // 解析等待的表達式
        let expression = Parser::parse_expression(tokens)?;

        Ok(ASTNode::Await(AwaitNode {
            future: Box::new(expression),
        }))
    }
}
