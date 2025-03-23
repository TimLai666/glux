use super::KeywordHandler;
use crate::ast::{ASTNode, MatchCase, MatchNode};
use crate::error::GluxError;
use crate::lexer::Token;
use crate::parser::Parser;

/// Match 關鍵字處理器
pub struct MatchHandler;

impl KeywordHandler for MatchHandler {
    fn parse(&self, tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError> {
        // 消耗 "match" 關鍵字
        tokens.remove(0);

        // 解析要匹配的表達式
        let condition = Parser::parse_expression(tokens)?;

        // 預期有 { 開始匹配塊
        if tokens.is_empty() || tokens[0].value != "{" {
            return Err(GluxError::ParserError(
                "Expected '{' after match expression".to_string(),
            ));
        }
        tokens.remove(0); // 消耗 {

        // 解析匹配情況
        let mut cases = Vec::new();
        while !tokens.is_empty() && tokens[0].value != "}" {
            // 解析模式
            let pattern = Parser::parse_expression(tokens)?;

            // 預期有 => 分隔符
            if tokens.is_empty() || tokens[0].value != "=>" {
                return Err(GluxError::ParserError(
                    "Expected '=>' after match pattern".to_string(),
                ));
            }
            tokens.remove(0); // 消耗 =>

            // 解析處理表達式
            let body = Parser::parse_block_or_expression(tokens)?;

            cases.push(MatchCase {
                pattern: Box::new(pattern),
                body: Box::new(body),
            });

            // 如果下個 token 是 ,，則消耗它
            if !tokens.is_empty() && tokens[0].value == "," {
                tokens.remove(0);
            }
        }

        // 預期有 } 結束匹配塊
        if tokens.is_empty() || tokens[0].value != "}" {
            return Err(GluxError::ParserError(
                "Expected '}' to close match block".to_string(),
            ));
        }
        tokens.remove(0); // 消耗 }

        Ok(ASTNode::Match(MatchNode {
            condition: Box::new(condition),
            cases,
        }))
    }
}
