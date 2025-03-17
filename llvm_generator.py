from llvmlite import ir, binding
from parser import Assign, BinaryOp, Number, Variable, FunctionCall, UnaryOp

class LLVMGenerator:
    def __init__(self):
        self.module = ir.Module(name="glux_module")
        self.module.triple = binding.get_default_triple()
        self.builder = None
        self.symbols = {}

    def generate(self, ast):
        """遍歷 AST 並產生 LLVM IR"""
        main_type = ir.FunctionType(ir.IntType(32), [])
        main_func = ir.Function(self.module, main_type, name="main")
        block = main_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)

        for node in ast:
            self.gen_node(node)

        self.builder.ret(ir.Constant(ir.IntType(32), 0))  # return 0;
        return self.module

    def gen_node(self, node):
        if isinstance(node, Assign):
            value = self.gen_node(node.value)
            ptr = self.builder.alloca(value.type, name=node.name)  # 分配變數
            self.builder.store(value, ptr)  # 存入變數
            self.symbols[node.name] = ptr  # 儲存變數指標
            return ptr  # **確保變數指標被存入**

        elif isinstance(node, BinaryOp):
            left = self.gen_node(node.left)
            right = self.gen_node(node.right)

            if node.op == "+":
                return self.builder.add(left, right, name="addtmp")
            elif node.op == "-":
                return self.builder.sub(left, right, name="subtmp")
            elif node.op == "*":
                return self.builder.mul(left, right, name="multmp")
            elif node.op == "/":
                return self.builder.sdiv(left, right, name="divtmp")
            elif node.op == "&&":
                left_bool = self.builder.icmp_signed("!=", left, ir.Constant(ir.IntType(32), 0), name="bool_left")
                right_bool = self.builder.icmp_signed("!=", right, ir.Constant(ir.IntType(32), 0), name="bool_right")
                return self.builder.and_(left_bool, right_bool, name="andtmp")
            elif node.op == "||":
                left_bool = self.builder.icmp_signed("!=", left, ir.Constant(ir.IntType(32), 0), name="bool_left")
                right_bool = self.builder.icmp_signed("!=", right, ir.Constant(ir.IntType(32), 0), name="bool_right")
                return self.builder.or_(left_bool, right_bool, name="ortmp")

        elif isinstance(node, UnaryOp):
            operand = self.gen_node(node.operand)
            if node.op == "!":
                return self.builder.icmp_signed("==", operand, ir.Constant(ir.IntType(32), 0), name="nottmp")

        elif isinstance(node, Variable):
            return self.builder.load(self.symbols[node.name], name=f"load_{node.name}")

        elif isinstance(node, Number):
            return ir.Constant(ir.IntType(32), node.value)
        elif isinstance(node, FunctionCall):
            if node.name == "print":
                print_values = [self.gen_node(arg) for arg in node.args]
                self.create_print(*print_values)  # **支援多個變數輸出**
        elif isinstance(node, UnaryOp):
            operand = self.gen_node(node.operand)
            if node.op == "!":
                return self.builder.icmp_signed("==", operand, ir.Constant(ir.IntType(32), 0), name="nottmp")
            elif node.op == "-":
                return self.builder.neg(operand, name="negtmp")  # **處理負數**

    def create_print(self, *args):
        """建立 `printf` 呼叫來輸出數字"""
        printf_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
        printf_func = ir.Function(self.module, printf_type, name="printf")
        printf_func.linkage = "external"

        # 建立格式化字串
        format_str = "%d " * len(args) + "\n\0"
        format_str_type = ir.ArrayType(ir.IntType(8), len(format_str))
        global_format_str = ir.GlobalVariable(self.module, format_str_type, name="format_str")
        global_format_str.linkage = "internal"
        global_format_str.global_constant = True
        global_format_str.initializer = ir.Constant(format_str_type, bytearray(format_str, "utf8"))

        format_ptr = self.builder.gep(global_format_str, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), 0)])

        # **確保 `i1` 轉換為 `i32`**
        values = [
            self.builder.zext(self.builder.load(self.symbols[arg.name], name=f"load_{arg.name}"), ir.IntType(32))
            if isinstance(arg, Variable) and arg.name in self.symbols and self.symbols[arg.name].type.pointee == ir.IntType(1)
            else self.builder.load(self.symbols[arg.name], name=f"load_{arg.name}") if isinstance(arg, Variable) else arg
            for arg in args
        ]
        
        self.builder.call(printf_func, [format_ptr, *values])  # **傳入所有變數**

