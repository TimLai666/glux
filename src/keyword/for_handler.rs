use super::KeywordHandler;
use crate::ast::ASTNode;
use crate::error::{GluxError, glux_error};
use crate::lexer::Token;

/// **解析 `for` 語句**
pub struct ForHandler;

impl KeywordHandler for ForHandler {
    fn parse(tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        tokens.remove(0); // 移除 `for`

        let iterator = if let Some(Token::Identifier(name)) = tokens.first() {
            tokens.remove(0);
            name.clone()
        } else {
            return glux_error!(ParserError, "Expected iterator name after 'for'");
        };

        if let Some(Token::Keyword(kw)) = tokens.first() {
            if kw == "in" {
                tokens.remove(0);
            } else {
                return glux_error!(ParserError, "Expected 'in' after for iterator");
            }
        }

        let range = crate::parser::parse_expression(tokens)?;

        if let Some(Token::Symbol('{')) = tokens.first() {
            tokens.remove(0);
        } else {
            return glux_error!(ParserError, "Expected '{' after for loop range");
        }

        let mut body = Vec::new();
        while let Some(token) = tokens.first() {
            if let Token::Symbol('}') = token {
                tokens.remove(0);
                break;
            }
            body.push(crate::parser::parse_statement(tokens)?);
        }

        Ok(ASTNode::ForLoop {
            iterator,
            range: Box::new(range),
            body,
        })
    }
}
