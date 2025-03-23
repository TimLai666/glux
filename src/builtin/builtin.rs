use inkwell::{
    builder::Builder,
    context::Context,
    module::Module,
    types::BasicTypeEnum,
    values::{FunctionValue, PointerValue},
};
use std::collections::HashMap;

/// **內建函式管理器**
pub struct BuiltinManager<'ctx> {
    functions: HashMap<String, FunctionValue<'ctx>>,
}

impl<'ctx> BuiltinManager<'ctx> {
    /// **建立內建函式管理器**
    pub fn new() -> Self {
        Self {
            functions: HashMap::new(),
        }
    }

    /// **將所有內建函式註冊到 LLVM Module**
    pub fn register_builtins(&mut self, context: &'ctx Context, module: &Module<'ctx>) {
        self.register_print(context, module);
        self.register_exit(context, module);
    }

    /// **註冊 `print(str)` 內建函式**
    fn register_print(&mut self, context: &'ctx Context, module: &Module<'ctx>) {
        let i8_ptr_type = context.i8_type().ptr_type(inkwell::AddressSpace::Generic);
        let fn_type = context.void_type().fn_type(&[i8_ptr_type.into()], true);
        let function = module.add_function("print", fn_type, None);
        self.functions.insert("print".to_string(), function);
    }

    /// **註冊 `exit(code)` 內建函式**
    fn register_exit(&mut self, context: &'ctx Context, module: &Module<'ctx>) {
        let i32_type = context.i32_type();
        let fn_type = context.void_type().fn_type(&[i32_type.into()], false);
        let function = module.add_function("exit", fn_type, None);
        self.functions.insert("exit".to_string(), function);
    }

    /// **取得內建函式**
    pub fn get_function(&self, name: &str) -> Option<FunctionValue<'ctx>> {
        self.functions.get(name).cloned()
    }

    /// **調用內建函式**
    pub fn call_builtin(
        &self,
        name: &str,
        args: &[BasicTypeEnum<'ctx>],
        builder: &Builder<'ctx>,
    ) -> Result<PointerValue<'ctx>, String> {
        if let Some(function) = self.get_function(name) {
            let call_site = builder.build_call(function, args, "call_builtin");
            call_site
                .try_as_basic_value()
                .left()
                .ok_or_else(|| format!("Builtin function '{}' did not return a value", name))
                .map(|val| val.into_pointer_value())
        } else {
            Err(format!("Builtin function '{}' not found", name))
        }
    }
}
