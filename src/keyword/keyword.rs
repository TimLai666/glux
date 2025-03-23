use crate::ast::ASTNode;
use crate::error::GluxError;
use crate::lexer::Token;

/// **關鍵字處理 Trait**
pub trait KeywordHandler {
    /// 解析關鍵字
    fn parse(tokens: &mut Vec<Token>) -> Result<ASTNode, GluxError>;
}
