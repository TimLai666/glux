use cranelift::codegen::ir;
use cranelift::prelude::*;
use cranelift_jit::{JITBuilder, JITModule};
use cranelift_module::{DataContext, FuncId, Linkage, Module};
use cranelift_native;
use std::collections::HashMap;

/// 代碼生成上下文，管理 Cranelift 編譯環境
pub struct CodeGen {
    /// Cranelift JIT 編譯模組
    module: JITModule,
    /// 函數建構器上下文
    builder_ctx: FunctionBuilderContext,
    /// 常數資料儲存
    #[allow(dead_code)]
    data_ctx: DataContext,
    /// 函數到 ID 的映射
    function_ids: HashMap<String, FuncId>,
}

impl CodeGen {
    /// 創建一個新的代碼生成上下文
    pub fn new() -> Self {
        // 創建 JIT 構建器
        let mut flag_builder = settings::builder();
        flag_builder.set("use_colocated_libcalls", "false").unwrap();
        flag_builder.set("is_pic", "false").unwrap();
        let isa_builder = cranelift_native::builder().unwrap_or_else(|msg| {
            panic!("主機平台不支援: {}", msg);
        });
        let isa = isa_builder
            .finish(settings::Flags::new(flag_builder))
            .unwrap();
        let builder = JITBuilder::with_isa(isa, cranelift_module::default_libcall_names());

        // 創建 JIT 模組
        let module = JITModule::new(builder);

        Self {
            module,
            builder_ctx: FunctionBuilderContext::new(),
            data_ctx: DataContext::new(),
            function_ids: HashMap::new(),
        }
    }

    /// 編譯函數
    pub fn compile_function(
        &mut self,
        name: &str,
        params: &[Type],
        return_type: Type,
        build_func: impl FnOnce(&mut FunctionBuilder),
    ) -> Result<*const u8, String> {
        // 創建函數簽名
        let mut sig = self.module.make_signature();
        for &param in params {
            sig.params.push(AbiParam::new(param));
        }
        // 檢查是否有返回值
        if return_type != types::INVALID {
            sig.returns.push(AbiParam::new(return_type));
        }

        // 聲明函數
        let func_id = self
            .module
            .declare_function(name, Linkage::Export, &sig)
            .map_err(|e| format!("無法宣告函數: {}", e))?;
        self.function_ids.insert(name.to_string(), func_id);

        // 創建新函數 - 使用 prelude 中的 Function
        let mut func = ir::Function::new();

        // 構建函數內容
        {
            let mut builder = FunctionBuilder::new(&mut func, &mut self.builder_ctx);
            build_func(&mut builder);
        }

        // 定義函數主體 - 修正 Context 使用方式
        let mut ctx = self.module.make_context();
        ctx.func = func; // 將函數設置為 context 的一部分

        self.module
            .define_function(func_id, &mut ctx) // 使用 context 而非 function
            .map_err(|e| format!("無法定義函數: {}", e))?;
        self.module.clear_context(&mut ctx); // 清理 context

        // 完成編譯
        self.module
            .finalize_definitions()
            .map_err(|e| format!("無法完成定義: {}", e))?;

        // 獲取編譯後的函數指針
        let code = self.module.get_finalized_function(func_id);
        Ok(code)
    }

    /// 獲取編譯後的函數
    pub fn get_function<T>(&self, name: &str) -> Option<unsafe extern "C" fn() -> T> {
        self.function_ids.get(name).map(|&id| {
            let ptr = self.module.get_finalized_function(id);
            unsafe { std::mem::transmute(ptr) }
        })
    }
}

/// 示例：簡單算術表達式的代碼生成
pub fn generate_arithmetic_example() -> Result<i32, String> {
    let mut codegen = CodeGen::new();

    // 編譯一個簡單函數: fn calc() -> i32 { return 40 + 2; }
    let code_ptr = codegen.compile_function("calc", &[], types::I32, |builder| {
        let entry = builder.create_block();
        builder.append_block_params_for_function_params(entry);
        builder.switch_to_block(entry);

        let forty = builder.ins().iconst(types::I32, 40);
        let two = builder.ins().iconst(types::I32, 2);
        let result = builder.ins().iadd(forty, two);

        builder.ins().return_(&[result]);
        builder.seal_all_blocks();
    })?;

    // 執行編譯後的函數
    let calc_fn: unsafe extern "C" fn() -> i32 = unsafe { std::mem::transmute(code_ptr) };
    let result = unsafe { calc_fn() };

    Ok(result)
}
