use crate::error::{GluxError, glux_error};

#[derive(Debug, PartialEq, Clone)]
pub enum Token {
    Keyword(String),
    Identifier(String),
    Number(String),
    StringLiteral(String),
    Operator(String),
    Symbol(char),
    EOF,
}

pub struct Lexer {
    input: Vec<char>,
    pos: usize,
}

impl Lexer {
    pub fn new(input: &str) -> Self {
        Self {
            input: input.chars().collect(),
            pos: 0,
        }
    }

    fn current_char(&self) -> Option<char> {
        self.input.get(self.pos).copied()
    }

    fn advance(&mut self) {
        self.pos += 1;
    }

    fn peek(&self) -> Option<char> {
        self.input.get(self.pos + 1).copied()
    }

    fn skip_whitespace(&mut self) {
        while let Some(ch) = self.current_char() {
            if ch.is_whitespace() {
                self.advance();
            } else {
                break;
            }
        }
    }

    fn read_identifier(&mut self) -> String {
        let mut ident = String::new();
        while let Some(ch) = self.current_char() {
            if ch.is_alphanumeric() || ch == '_' {
                ident.push(ch);
                self.advance();
            } else {
                break;
            }
        }
        ident
    }

    fn read_number(&mut self) -> String {
        let mut number = String::new();
        while let Some(ch) = self.current_char() {
            if ch.is_numeric() || ch == '_' || ch == '.' {
                number.push(ch);
                self.advance();
            } else {
                break;
            }
        }
        number
    }

    fn read_string(&mut self) -> Result<String, GluxError> {
        let mut string_val = String::new();
        self.advance(); // 跳過開頭的 `"`

        while let Some(ch) = self.current_char() {
            if ch == '"' {
                self.advance();
                return Ok(string_val);
            }
            string_val.push(ch);
            self.advance();
        }

        glux_error!(LexerError, "未終結的字串")
    }

    fn read_operator(&mut self) -> Token {
        let op = self.current_char().unwrap();
        let mut op_str = op.to_string();
        self.advance();

        // 支援雙字符運算子（如 `==`, `!=`, `<=`, `>=`, `:=`）
        if let Some(next) = self.current_char() {
            let double_op = format!("{}{}", op, next);
            if ["==", "!=", "<=", ">=", ":="].contains(&double_op.as_str()) {
                self.advance();
                return Token::Operator(double_op);
            }
        }

        Token::Operator(op_str)
    }

    pub fn next_token(&mut self) -> Result<Token, GluxError> {
        self.skip_whitespace();

        if let Some(ch) = self.current_char() {
            if ch.is_alphabetic() || ch == '_' {
                let ident = self.read_identifier();
                return Ok(if is_keyword(&ident) {
                    Token::Keyword(ident)
                } else {
                    Token::Identifier(ident)
                });
            }

            if ch.is_numeric() {
                return Ok(Token::Number(self.read_number()));
            }

            if ch == '"' {
                return Ok(Token::StringLiteral(self.read_string()?));
            }

            if "+-*/%<>=!&|^~".contains(ch) {
                return Ok(self.read_operator());
            }

            if ";,(){}[]".contains(ch) {
                self.advance();
                return Ok(Token::Symbol(ch));
            }

            glux_error!(LexerError, "無效字元: '{}'", ch)
        }

        Ok(Token::EOF)
    }
}

pub fn tokenize(source: &str) -> Result<Vec<Token>, GluxError> {
    let mut lexer = Lexer::new(source);
    let mut tokens = Vec::new();

    loop {
        let token = lexer.next_token()?;
        tokens.push(token.clone());
        if token == Token::EOF {
            break;
        }
    }

    Ok(tokens)
}

fn is_keyword(ident: &str) -> bool {
    matches!(
        ident,
        "and"
            | "await"
            | "const"
            | "else"
            | "extends"
            | "false"
            | "fn"
            | "for"
            | "from"
            | "if"
            | "import"
            | "in"
            | "interface"
            | "main"
            | "not"
            | "or"
            | "return"
            | "spawn"
            | "struct"
            | "true"
            | "unsafe"
            | "while"
            | "override"
    )
}
