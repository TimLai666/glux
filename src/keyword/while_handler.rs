use super::KeywordHandler;
use crate::ast::ASTNode;
use crate::error::{glux_error, GluxError};
use crate::lexer::Token;

/// **解析 `while` 語句**
pub struct WhileHandler;

// 實現 KeywordHandler 接口
impl KeywordHandler for WhileHandler {
    fn parse(&self, tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        tokens.remove(0); // 移除 `while`

        let condition = crate::parser::parse_expression(tokens)?;
        if let Some(Token::Symbol('{')) = tokens.first() {
            tokens.remove(0);
        } else {
            // 修正格式字符串
            return glux_error!(ParserError, "Expected '{{' after while condition");
        }

        let mut body = Vec::new();
        while let Some(token) = tokens.first() {
            if let Token::Symbol('}') = token {
                tokens.remove(0);
                break;
            }
            body.push(crate::parser::parse_statement(tokens)?);
        }

        Ok(ASTNode::WhileLoop {
            condition: Box::new(condition),
            body,
        })
    }
}
