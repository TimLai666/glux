use crate::keyword::for_handler::ForHandler;
use crate::keyword::if_handler::IfHandler;
use crate::keyword::keyword::KeywordHandler;
use crate::keyword::while_handler::WhileHandler;

// 暫時註釋掉未實現的處理器
// use crate::keyword::await_handler::AwaitHandler;
// use crate::keyword::match_handler::MatchHandler;
// use crate::keyword::return_handler::ReturnHandler;
// use crate::keyword::spawn_handler::SpawnHandler;

use std::collections::HashMap;

pub struct KeywordRegistry {
    handlers: HashMap<String, Box<dyn KeywordHandler>>,
}

impl KeywordRegistry {
    pub fn new() -> Self {
        // 現在可以使用 Box<dyn KeywordHandler> 因為我們修復了 trait
        let mut handlers: HashMap<String, Box<dyn KeywordHandler>> = HashMap::new();

        // 註冊處理器
        handlers.insert("if".to_string(), Box::new(IfHandler));
        handlers.insert("for".to_string(), Box::new(ForHandler));
        handlers.insert("while".to_string(), Box::new(WhileHandler));

        // 註釋掉未實現的處理器
        // handlers.insert("await".to_string(), Box::new(AwaitHandler));
        // handlers.insert("match".to_string(), Box::new(MatchHandler));
        // handlers.insert("return".to_string(), Box::new(ReturnHandler));
        // handlers.insert("spawn".to_string(), Box::new(SpawnHandler));

        Self { handlers }
    }

    pub fn get(&self, keyword: &str) -> Option<&Box<dyn KeywordHandler>> {
        self.handlers.get(keyword)
    }
}
