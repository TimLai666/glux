use super::KeywordHandler;
use crate::ast::ASTNode;
use crate::error::{glux_error, GluxError};
use crate::lexer::Token;

/// **解析 `if` 語句**
pub struct IfHandler;

// 實現 KeywordHandler 接口
impl KeywordHandler for IfHandler {
    fn parse(&self, tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        tokens.remove(0); // 移除 `if`

        let condition = crate::parser::parse_expression(tokens)?;
        if let Some(Token::Symbol('{')) = tokens.first() {
            tokens.remove(0);
        } else {
            // 修正格式字符串
            return glux_error!(ParserError, "Expected '{{' after if condition");
        }

        let mut then_branch = Vec::new();
        while let Some(token) = tokens.first() {
            if let Token::Symbol('}') = token {
                tokens.remove(0);
                break;
            }
            then_branch.push(crate::parser::parse_statement(tokens)?);
        }

        let else_branch = if let Some(Token::Keyword(kw)) = tokens.first() {
            if kw == "else" {
                tokens.remove(0);
                if let Some(Token::Symbol('{')) = tokens.first() {
                    tokens.remove(0);
                } else {
                    // 修正格式字符串
                    return glux_error!(ParserError, "Expected '{{' after else");
                }

                let mut else_body = Vec::new();
                while let Some(token) = tokens.first() {
                    if let Token::Symbol('}') = token {
                        tokens.remove(0);
                        break;
                    }
                    else_body.push(crate::parser::parse_statement(tokens)?);
                }
                Some(else_body)
            } else {
                None
            }
        } else {
            None
        };

        Ok(ASTNode::IfStatement {
            condition: Box::new(condition),
            then_branch,
            else_branch,
        })
    }
}
