try:
    from .algorithms import *
    from .utils import *
except ImportError:
    from algorithms import *
    from utils import *
import dis
import types

class iu_lambda:
    def __init__(self, key=None, *, formula=None, index_path=None, vars_=None, total_vars_loaded=None):
        if key is not None:
            formula, index_path, variables, total_vars_loaded = iu_lambda.from_lambda(key)
        elif any(arg is None for arg in (formula, index_path, variables, total_vars_loaded)):
            raise ValueError("Invalid arguments for custom iu_lambda")
        self._for_eval = f"lambda {','.join(variables)}: {formula}"
        self.formula = formula
        self.index_path = tuple(index_path)
        self.vars_ = vars_
        self.total_vars_loaded = total_vars_loaded
        self._key = eval(self._for_eval) # not just `key` to ensure no errors
        
    def __repr__(self):
        return f"iu_lambda(key={self._for_eval})"

    def __str__(self):
        return f"<class iu_lambda({self._for_eval}) at {hex(id(self))}>"

    def __call__(self, *args, **kwargs):
        return self._key(*args, **kwargs)
    
    @property
    def key(self):
        """Returns the actual callable lambda function"""
        return self._key

    def from_lambda(key, verbose=True):
        instructions = list(dis.get_instructions(key))
        if verbose: print([instr.opname for instr in instructions])
        RETURN = instructions[-1].opname
        if RETURN.endswith("CONST"):
            return str(RETURN.argval)
        elif RETURN.endswith("VALUE"):
            if verbose: print("Start loop!!")
            i=0
            STACK = []
            LOADED_GLOBALS_STACK = []
            index_path = []
            TOTAL_VARS_LOADED = 0
            VAR_NAMES = []
            for instr in instructions:
                if verbose: print(f"\nInstruction {i}: {instr.opname}"); i+= 1
                
                match instr.opname:
                    case "RESUME":
                        continue
                    case "COPY_FREE_VARS":
                        continue
                    case "LOAD_CONST":
                        STACK.append(str(instr.argval))
                        if verbose: print(f"Loaded {instr.argval} to STACK")
                    case "LOAD_FAST":
                        var = instr.argval
                        STACK.append(str(var))
                        if var not in VAR_NAMES:
                            VAR_NAMES.append(str(var))
                        TOTAL_VARS_LOADED += 1
                        if verbose: print(f"Loaded {var} to STACK")
                    case "LOAD_DEREF":
                        STACK.append(f"deref_{instr.argval}")
                        TOTAL_VARS_LOADED += 1
                    case "UNARY_INVERT":
                        STACK[-1] = "~"+STACK[-1]
                    case "UNARY_NEGATIVE":
                        STACK[-1] = "-"+STACK[-1]
                    case "UNARY_NOT":
                        STACK[-1] = "not "+STACK[-1]
                    case "BINARY_SUBSCR":
                        STACK[-2] = f"{STACK[-2]}[{STACK[-1]}]"
                        index_path.append(STACK.pop(-1))
                    case "COMPARE_OP":
                        arg = instr.arg
                        cmp_ops = ('<', '<=', '==', '!=', '>', '>=', 'in', 'not in', 'is', 'is not', 'exception match', 'BAD')
                        
                        if arg < len(cmp_ops):
                            op = cmp_ops[arg]
                        elif arg == 2:
                            op = '<'
                        elif arg == 42:
                            op = '<='
                        elif arg == 72:
                            op = '=='
                        elif arg == 103:
                            op = '!='
                        elif arg == 132:
                            op = '>'
                        elif arg == 172:
                            op = '>='
                        else:
                            op = 'UNKNOWN'
                        
                        STACK[-2] = f"({STACK[-2]} {op} {STACK[-1]})"
                        STACK.pop(-1)
                    case "POP_TOP":
                        STACK.pop()
                    case "DUP_TOP":
                        STACK.append(STACK[-1])
                    case "ROT_TWO":
                        STACK[-1], STACK[-2] = STACK[-2], STACK[-1]
                    case "LOAD_GLOBAL":
                        LOADED_GLOBALS_STACK.append(instr.argval)
                        if verbose: print(f"loaded global variable '{str(instr.argval)}'")
                    case "CALL":
                        num_args = instr.arg if hasattr(instr, 'arg') else 0
                        if num_args == 0:
                            func = STACK.pop(-1)
                            STACK.append(f"{func}()")
                        else:
                            args = [STACK.pop(-1) for _ in range(num_args)]
                            args.reverse()
                            func = STACK.pop(-1)
                            STACK.append(f"{func}({', '.join(args)})")
                        if verbose: print(f"retrieved call with {num_args} args")
                    case "CALL_FUNCTION":
                        last_global = LOADED_GLOBALS_STACK.pop(-1)
                        STACK[-1] = f"{last_global}({STACK[-1]})"
                        if verbose: print(f"retrieved last loaded global '{last_global}'")
                    case "LOAD_ATTR":
                        STACK[-1] += "." + str(instr.argval)
                    case "RETURN_VALUE":
                        return (STACK[-1], index_path, VAR_NAMES, TOTAL_VARS_LOADED)
                    case "MAKE_FUNCTION":
                        flags = instr.arg
                        defaults = None
                        kw_defaults = None
                        annotations = None
                        closure = None
                        if flags & 0x08:
                            closure = STACK.pop(-1)
                        if flags & 0x04:
                            annotations = STACK.pop(-1)
                        if flags & 0x02:
                            kw_defaults = STACK.pop(-1)
                        if flags & 0x01:
                            defaults = STACK.pop(-1)
                        code = STACK.pop(-1)
                        STACK.append(f"function({code})")
                    case "MAKE_CELL":
                        if verbose: print(f"Create cell for {instr.argval}")
                    case "LOAD_CLOSURE":
                        STACK.append(f"closure_{instr.argval}")
                    case "BUILD_CLASS":
                        bases = [STACK.pop(-1)]
                        metaclass = STACK.pop(-1)
                        name = STACK.pop(-1)
                        STACK.append(f"class {name}({', '.join(bases)}): ...")
                    case "LOAD_BUILD_CLASS":
                        LOADED_GLOBALS_STACK.append("__build_class__")
                    case "IMPORT_NAME":
                        level = STACK.pop(-1)
                        fromlist = STACK.pop(-1)
                        module = instr.argval
                        if level == 0:
                            STACK.append(f"import {module}")
                        else:
                            STACK.append(f"from {module} import {fromlist}")
                    case "IMPORT_FROM":
                        module = STACK[-1]
                        name = instr.argval
                        STACK.append(f"{module}.{name}")
                    case "IMPORT_STAR":
                        module = STACK.pop(-1)
                        STACK.append(f"from {module} import *")
                    case "RAISE_VARARGS":
                        argc = instr.arg
                        if argc == 0:
                            STACK.append("raise")
                        elif argc == 1:
                            exc = STACK.pop(-1)
                            STACK.append(f"raise {exc}")
                        elif argc == 2:
                            cause = STACK.pop(-1)
                            exc = STACK.pop(-1)
                            STACK.append(f"raise {exc} from {cause}")
                    case "RERAISE":
                        STACK.append("raise")
                    case "END_FINALLY":
                        if verbose: print("End finally block")
                    case "BEFORE_WITH":
                        obj = STACK[-1]
                        STACK.append(f"__enter__({obj})")
                    case "MATCH_CLASS":
                        n = instr.arg
                        attrs = [STACK.pop(-1) for _ in range(n)]
                        cls = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        STACK.append(f"match {obj} as {cls}({', '.join(attrs)})")
                    case "MATCH_SEQUENCE":
                        if verbose: print(f"Match sequence pattern, offset {instr.arg}")
                    case "MATCH_MAPPING":
                        if verbose: print(f"Match mapping pattern, offset {instr.arg}")
                    case "MATCH_KEYS":
                        n = instr.arg
                        keys = [STACK.pop(-1) for _ in range(n)]
                        STACK.append(f"match_keys({', '.join(keys)})")
                    case "MATCH_EXC_CHECK":
                        if verbose: print(f"Match exception check, offset {instr.arg}")
                    case "LIST_APPEND":
                        val = STACK.pop(-1)
                        idx = instr.arg
                        if verbose: print(f"Append {val} to list at depth {idx}")
                    case "SET_ADD":
                        val = STACK.pop(-1)
                        idx = instr.arg
                        if verbose: print(f"Add {val} to set at depth {idx}")
                    case "MAP_ADD":
                        val = STACK.pop(-1)
                        key = STACK.pop(-1)
                        idx = instr.arg
                        if verbose: print(f"Add {key}: {val} to map at depth {idx}")
                    case "LIST_EXTEND":
                        val = STACK.pop(-1)
                        idx = instr.arg
                        if verbose: print(f"Extend list at depth {idx} with {val}")
                    case "SET_UPDATE":
                        val = STACK.pop(-1)
                        idx = instr.arg
                        if verbose: print(f"Update set at depth {idx} with {val}")
                    case "DICT_UPDATE":
                        val = STACK.pop(-1)
                        idx = instr.arg
                        if verbose: print(f"Update dict at depth {idx} with {val}")
                    case "DICT_MERGE":
                        val = STACK.pop(-1)
                        if verbose: print(f"Merge dict {val}")
                    case "LIST_TO_TUPLE":
                        STACK[-1] = f"tuple({STACK[-1]})"
                    case "SETUP_ANNOTATIONS":
                        if verbose: print("Setup annotations")
                    case "LOAD_ASSERTION_ERROR":
                        LOADED_GLOBALS_STACK.append("AssertionError")
                    case "CALL_FUNCTION_VAR":
                        argc = instr.arg
                        varargs = STACK.pop(-1)
                        args = [STACK.pop(-1) for _ in range(argc)]
                        args.reverse()
                        func = STACK.pop(-1)
                        STACK.append(f"{func}({', '.join(args)}, *{varargs})")
                    case "CALL_FUNCTION_VAR_KW":
                        argc = instr.arg
                        kwargs = STACK.pop(-1)
                        varargs = STACK.pop(-1)
                        args = [STACK.pop(-1) for _ in range(argc)]
                        args.reverse()
                        func = STACK.pop(-1)
                        STACK.append(f"{func}({', '.join(args)}, *{varargs}, **{kwargs})")
                    case "LOAD_SUPER":
                        cell = STACK.pop(-1)
                        self = STACK.pop(-1)
                        STACK.append(f"super({cell}, {self})")
                    case "LOAD_ATTR_METHOD":
                        STACK[-1] += "." + str(instr.argval)
                    case "STORE_ATTR_FAST":
                        value = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        STACK.append(f"({obj}.{instr.argval} = {value})")
                    case "DELETE_ATTR":
                        obj = STACK.pop(-1)
                        if verbose: print(f"Delete {obj}.{instr.argval}")
                    case "BINARY_MATRIX_MULTIPLY":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} @ {right}"
                    case "ASSERT_NOT_NONE":
                        val = STACK[-1]
                        if verbose: print(f"Assert {val} is not None")
                    case "LOAD_LOCALS":
                        STACK.append("locals()")
                    case "LOAD_FROM_DICT_OR_GLOBALS":
                        name = instr.argval
                        STACK.append(f"get_from_dict_or_globals({name})")
                    case "UNPACK_SEQUENCE":
                        n = instr.arg
                        seq = STACK.pop(-1)
                        STACK.append(f"unpack({seq}, {n})")
                    case "UNPACK_EX":
                        low = instr.arg & 0xFF
                        high = (instr.arg >> 8) & 0xFF
                        seq = STACK.pop(-1)
                        STACK.append(f"unpack({seq}, {low}, {high})")
                    case "LOAD_ATTR_SLOT":
                        STACK[-1] += "." + str(instr.argval)
                    case "BINARY_SLICE":
                        end = STACK.pop(-1)
                        start = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        STACK.append(f"{obj}[{start}:{end}]")
                    case "JUMP_IF_EXCEPTION_MATCH":
                        if verbose: print(f"Jump if exception match, offset {instr.arg}")
                    case "GET_AITER":
                        STACK[-1] = f"aiter({STACK[-1]})"
                    case "GET_ANEXT":
                        STACK[-1] = f"anext({STACK[-1]})"
                    case "BEFORE_ASYNC_WITH":
                        obj = STACK[-1]
                        STACK.append(f"__aenter__({obj})")
                    case "SETUP_ASYNC_WITH_EXCEPT":
                        if verbose: print(f"Setup async with except, offset {instr.arg}")
                    case "SEND":
                        val = STACK.pop(-1)
                        gen = STACK.pop(-1)
                        STACK.append(f"{gen}.send({val})")
                    case "NOP":
                        continue
                    case "LOAD_CLASSDEREF":
                        STACK.append(f"classderef_{instr.argval}")
                        TOTAL_VARS_LOADED += 1
                    case "UNARY_POSITIVE":
                        STACK[-1] = "+" + STACK[-1]
                    case "GET_ITER":
                        STACK[-1] = f"iter({STACK[-1]})"
                    case "GET_AWAITABLE":
                        STACK[-1] = f"await {STACK[-1]}"
                    case "LOAD_METHOD":
                        STACK[-1] += "." + str(instr.argval)
                    case "DUP_TOP_TWO":
                        STACK.extend(STACK[-2:])
                    case "ROT_THREE":
                        val = STACK.pop(-1)
                        STACK.insert(-2, val)
                    case "ROT_FOUR":
                        val = STACK.pop(-1)
                        STACK.insert(-3, val)
                    case "STORE_SUBSCR":
                        value = STACK.pop(-1)
                        index = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        STACK.append(f"({obj}[{index}] = {value})")
                    case "IS_OP":
                        op = "is not" if instr.arg else "is"
                        STACK[-2] = f"({STACK[-2]} {op} {STACK[-1]})"
                        STACK.pop(-1)
                    case "CONTAINS_OP":
                        op = "not in" if instr.arg else "in"
                        STACK[-2] = f"({STACK[-2]} {op} {STACK[-1]})"
                        STACK.pop(-1)
                    case "CALL_FUNCTION_KW":
                        num_args = instr.argval
                        kwnames = STACK.pop(-1)
                        args = [STACK.pop(-1) for _ in range(num_args)]
                        args.reverse()
                        func = STACK.pop(-1)
                        STACK.append(f"{func}({', '.join(args)}, {kwnames})")
                    case "CALL_FUNCTION_EX":
                        flags = instr.arg
                        if flags & 0x02:
                            kwargs = STACK.pop(-1)
                        if flags & 0x01:
                            args = STACK.pop(-1)
                        func = STACK.pop(-1)
                        call_str = f"{func}("
                        if flags & 0x01:
                            call_str += f"*{args}"
                        if (flags & 0x01) and (flags & 0x02):
                            call_str += ", "
                        if flags & 0x02:
                            call_str += f"**{kwargs}"
                        call_str += ")"
                        STACK.append(call_str)
                    case "CALL_METHOD":
                        num_args = instr.argval
                        args = [STACK.pop(-1) for _ in range(num_args)]
                        args.reverse()
                        method = STACK.pop(-1)
                        STACK.append(f"{method}({', '.join(args)})")
                    case "YIELD_VALUE":
                        STACK[-1] = f"yield {STACK[-1]}"
                    case "YIELD_FROM":
                        STACK[-1] = f"yield from {STACK[-1]}"
                    case "BUILD_LIST_UNPACK":
                        n = instr.argval
                        items = [STACK.pop(-1) for _ in range(n)]
                        items.reverse()
                        result = "[" + ", ".join([f"*{item}" for item in items]) + "]"
                        STACK.append(result)
                    case "BUILD_TUPLE_UNPACK":
                        n = instr.argval
                        items = [STACK.pop(-1) for _ in range(n)]
                        items.reverse()
                        result = "(" + ", ".join([f"*{item}" for item in items]) + ")"
                        STACK.append(result)
                    case "BUILD_TUPLE_UNPACK_WITH_CALL":
                        n = instr.argval
                        items = [STACK.pop(-1) for _ in range(n)]
                        items.reverse()
                        result = "(" + ", ".join([f"*{item}" for item in items]) + ")"
                        STACK.append(result)
                    case "BUILD_SET_UNPACK":
                        n = instr.argval
                        items = [STACK.pop(-1) for _ in range(n)]
                        items.reverse()
                        result = "{" + ", ".join([f"*{item}" for item in items]) + "}"
                        STACK.append(result)
                    case "BUILD_MAP_UNPACK":
                        n = instr.argval
                        items = [STACK.pop(-1) for _ in range(n)]
                        items.reverse()
                        result = "{" + ", ".join([f"**{item}" for item in items]) + "}"
                        STACK.append(result)
                    case "BUILD_MAP_UNPACK_WITH_CALL":
                        n = instr.argval
                        items = [STACK.pop(-1) for _ in range(n)]
                        items.reverse()
                        result = "{" + ", ".join([f"**{item}" for item in items]) + "}"
                        STACK.append(result)
                    case "BUILD_CONST_KEY_MAP":
                        n = instr.argval
                        keys = STACK.pop(-1)
                        values = [STACK.pop(-1) for _ in range(n)]
                        values.reverse()
                        result = "{" + ", ".join([f"{k}: {v}" for k, v in zip(keys, values)]) + "}"
                        STACK.append(result)
                    case "POP_JUMP_IF_FALSE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is false to offset {instr.arg}")
                    case "POP_JUMP_IF_TRUE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is true to offset {instr.arg}")
                    case "JUMP_IF_FALSE_OR_POP":
                        cond = STACK[-1]
                        if verbose: print(f"Jump if {cond} is false to offset {instr.arg}, else pop")
                    case "JUMP_IF_TRUE_OR_POP":
                        cond = STACK[-1]
                        if verbose: print(f"Jump if {cond} is true to offset {instr.arg}, else pop")
                    case "JUMP_ABSOLUTE":
                        if verbose: print(f"Jump to offset {instr.arg}")
                    case "JUMP_FORWARD":
                        if verbose: print(f"Jump forward {instr.arg}")
                    case "FOR_ITER":
                        iterator = STACK[-1]
                        if verbose: print(f"FOR_ITER: {iterator}, jump to offset {instr.arg} if exhausted")
                    case "SETUP_LOOP":
                        if verbose: print(f"Setup loop, exception target offset {instr.arg}")
                    case "SETUP_EXCEPT":
                        if verbose: print(f"Setup exception handler, target offset {instr.arg}")
                    case "SETUP_FINALLY":
                        if verbose: print(f"Setup finally block, target offset {instr.arg}")
                    case "SETUP_WITH":
                        if verbose: print(f"Setup with statement, target offset {instr.arg}")
                    case "POP_BLOCK":
                        if verbose: print("Pop exception block")
                    case "POP_EXCEPT":
                        STACK.pop()
                        if verbose: print("Pop exception")
                    case "WITH_CLEANUP_START":
                        if verbose: print("Start with cleanup")
                    case "WITH_CLEANUP_FINISH":
                        STACK.pop()
                        if verbose: print("Finish with cleanup")
                    case "SETUP_ASYNC_WITH":
                        if verbose: print(f"Setup async with, target offset {instr.arg}")
                    case "BUILD_SLICE":
                        if instr.arg == 3:
                            step = STACK.pop(-1)
                            stop = STACK.pop(-1)
                            start = STACK.pop(-1)
                            STACK.append(f"{start}:{stop}:{step}")
                        else:
                            stop = STACK.pop(-1)
                            start = STACK.pop(-1)
                            STACK.append(f"{start}:{stop}")
                    case "EXTENDED_ARG":
                        if verbose: print("Extended arg instruction")
                    case "STORE_FAST":
                        value = STACK.pop(-1)
                        var_name = instr.argval
                        if verbose: print(f"Store {value} to {var_name}")
                    case "STORE_GLOBAL":
                        value = STACK.pop(-1)
                        if verbose: print(f"Store {value} to global {instr.argval}")
                    case "STORE_DEREF":
                        value = STACK.pop(-1)
                        if verbose: print(f"Store {value} to deref {instr.argval}")
                    case "STORE_ATTR":
                        value = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        STACK.append(f"({obj}.{instr.argval} = {value})")
                    case "DELETE_FAST":
                        if verbose: print(f"Delete {instr.argval}")
                    case "DELETE_GLOBAL":
                        if verbose: print(f"Delete global {instr.argval}")
                    case "DELETE_DEREF":
                        if verbose: print(f"Delete deref {instr.argval}")
                    case "FORMAT_VALUE":
                        if instr.arg & 0x04:
                            spec = STACK.pop(-1)
                            value = STACK.pop(-1)
                            STACK.append(f"f\"{{{value}:{spec}}}\"")
                        else:
                            value = STACK.pop(-1)
                            STACK.append(f"f\"{{{value}}}\"")
                    case "BUILD_STRING":
                        n = instr.argval
                        parts = [STACK.pop(-1) for _ in range(n)]
                        parts.reverse()
                        STACK.append("f\"" + "".join(parts) + "\"")
                    case "INPLACE_ADD":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} += {right}"
                    case "INPLACE_SUBTRACT":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} -= {right}"
                    case "INPLACE_MULTIPLY":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} *= {right}"
                    case "INPLACE_TRUE_DIVIDE":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} /= {right}"
                    case "INPLACE_FLOOR_DIVIDE":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} //= {right}"
                    case "INPLACE_MODULO":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} %= {right}"
                    case "INPLACE_POWER":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} **= {right}"
                    case "INPLACE_LSHIFT":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} <<= {right}"
                    case "INPLACE_RSHIFT":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} >>= {right}"
                    case "INPLACE_AND":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} &= {right}"
                    case "INPLACE_OR":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} |= {right}"
                    case "INPLACE_XOR":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} ^= {right}"
                    case "INPLACE_MATRIX_MULTIPLY":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} @= {right}"
                    case "MATCH_OR":
                        left = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} | {left}"
                    case "COMPARE_OP_ADAPTIVE":
                        arg = instr.arg
                        cmp_ops = ('<', '<=', '==', '!=', '>', '>=', 'in', 'not in', 'is', 'is not', 'exception match', 'BAD')
                        
                        if arg < len(cmp_ops):
                            op = cmp_ops[arg]
                        elif arg == 2:
                            op = '<'
                        elif arg == 42:
                            op = '<='
                        elif arg == 72:
                            op = '=='
                        elif arg == 103:
                            op = '!='
                        elif arg == 132:
                            op = '>'
                        elif arg == 172:
                            op = '>='
                        else:
                            op = 'UNKNOWN'
                        
                        STACK[-2] = f"({STACK[-2]} {op} {STACK[-1]})"
                        STACK.pop(-1)
                    case "UNARY_OP":
                        opcode = instr.arg
                        ops_unary = {16: '+', 18: '-', 20: '~', 19: 'not '}
                        op = ops_unary.get(opcode, '?')
                        STACK[-1] = f"{op}{STACK[-1]}"
                    case "RESUME_QUICK":
                        continue
                    case "GET_LOOP_ITER":
                        STACK[-1] = f"iter({STACK[-1]})"
                    case "GET_YIELD_FROM_ITER":
                        STACK[-1] = f"yield from {STACK[-1]}"
                    case "INSTRUMENTED_YIELD":
                        STACK[-1] = f"yield {STACK[-1]}"
                    case "INSTRUMENTED_YIELD_VALUE":
                        STACK[-1] = f"yield {STACK[-1]}"
                    case "INSTRUMENTED_RESUME":
                        continue
                    case "INSTRUMENTED_RETURN_VALUE":
                        return (STACK[-1], index_path, VAR_NAMES, TOTAL_VARS_LOADED)
                    case "INSTRUMENTED_CALL_FUNCTION_EX":
                        flags = instr.arg
                        if flags & 0x02:
                            kwargs = STACK.pop(-1)
                        if flags & 0x01:
                            args = STACK.pop(-1)
                        func = STACK.pop(-1)
                        call_str = f"{func}("
                        if flags & 0x01:
                            call_str += f"*{args}"
                        if (flags & 0x01) and (flags & 0x02):
                            call_str += ", "
                        if flags & 0x02:
                            call_str += f"**{kwargs}"
                        call_str += ")"
                        STACK.append(call_str)
                    case "INSTRUMENTED_FOR_ITER":
                        iterator = STACK[-1]
                        if verbose: print(f"FOR_ITER: {iterator}, jump to offset {instr.arg} if exhausted")
                    case "INSTRUMENTED_JUMP_FORWARD":
                        if verbose: print(f"Jump forward {instr.arg}")
                    case "INSTRUMENTED_JUMP_BACKWARD":
                        if verbose: print(f"Jump backward {instr.arg}")
                    case "INSTRUMENTED_POP_JUMP_IF_FALSE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is false to offset {instr.arg}")
                    case "INSTRUMENTED_POP_JUMP_IF_TRUE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is true to offset {instr.arg}")
                    case "INSTRUMENTED_POP_JUMP_IF_NONE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is None to offset {instr.arg}")
                    case "INSTRUMENTED_POP_JUMP_IF_NOT_NONE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is not None to offset {instr.arg}")
                    case "COPY":
                        n = instr.arg
                        STACK.append(STACK[-n])
                    case "SWAP":
                        n = instr.arg
                        STACK[-1], STACK[-n] = STACK[-n], STACK[-1]
                    case "CACHE":
                        continue
                    case "ADAPTIVE_BINARY_ADD":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} + {right}"
                    case "ADAPTIVE_BINARY_SUBTRACT":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} - {right}"
                    case "ADAPTIVE_BINARY_MULTIPLY":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} * {right}"
                    case "ADAPTIVE_BINARY_TRUE_DIVIDE":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} / {right}"
                    case "ADAPTIVE_BINARY_FLOOR_DIVIDE":
                        right = STACK.pop(-1)
                        STACK[-1] = f"{STACK[-1]} // {right}"
                    case "ADAPTIVE_BINARY_SUBSCR":
                        STACK[-2] = f"{STACK[-2]}[{STACK[-1]}]"
                        index_path.append(STACK.pop(-1))
                    case "ADAPTIVE_STORE_SUBSCR":
                        value = STACK.pop(-1)
                        index = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        STACK.append(f"({obj}[{index}] = {value})")
                    case "DELETE_SUBSCR":
                        index = STACK.pop(-1)
                        obj = STACK.pop(-1)
                        if verbose: print(f"Delete {obj}[{index}]")
                    case "TO_BOOL":
                        val = STACK[-1]
                        STACK[-1] = f"bool({val})"
                    case "LOAD_FAST_LOAD_FAST":
                        var1_idx = instr.arg & 0xFF
                        var2_idx = (instr.arg >> 8) & 0xFF
                        code = instr.co_code if hasattr(instr, 'co_code') else None
                        
                        if hasattr(instr, 'code') and hasattr(instr.code, 'co_varnames'):
                            var_names = instr.code.co_varnames
                            var1 = var_names[var1_idx] if var1_idx < len(var_names) else str(var1_idx)
                            var2 = var_names[var2_idx] if var2_idx < len(var_names) else str(var2_idx)
                        else:
                            var1 = f"var{var1_idx}"
                            var2 = f"var{var2_idx}"
                        
                        STACK.append(var1)
                        STACK.append(var2)
                        if var1 not in VAR_NAMES:
                            VAR_NAMES.append(var1)
                        if var2 not in VAR_NAMES:
                            VAR_NAMES.append(var2)
                        TOTAL_VARS_LOADED += 2
                    case "LOAD_FROM_DICT_OR_VARS":
                        name = instr.argval
                        STACK.append(f"get_from_dict_or_vars({name})")
                    case "CALL_INTRINSIC_1":
                        func_id = instr.arg
                        val = STACK.pop(-1)
                        intrinsics = {0: "INTRINSIC_PRINT", 1: "INTRINSIC_IMPORT_STAR", 2: "INTRINSIC_STOPITERATION_ERROR"}
                        intrinsic = intrinsics.get(func_id, f"intrinsic_{func_id}")
                        STACK.append(f"{intrinsic}({val})")
                    case "CALL_INTRINSIC_2":
                        func_id = instr.arg
                        val2 = STACK.pop(-1)
                        val1 = STACK.pop(-1)
                        STACK.append(f"intrinsic_{func_id}({val1}, {val2})")
                    case "JUMP_BACKWARD":
                        if verbose: print(f"Jump backward {instr.arg}")
                    case "JUMP_BACKWARD_NO_INTERRUPT":
                        if verbose: print(f"Jump backward no interrupt {instr.arg}")
                    case "POP_JUMP_IF_NONE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is None to offset {instr.arg}")
                    case "POP_JUMP_IF_NOT_NONE":
                        cond = STACK.pop(-1)
                        if verbose: print(f"Jump if {cond} is not None to offset {instr.arg}")
                    case _:
                        if instr.opname.startswith("BINARY_"):
                            #strip off "BINARY_"
                            opname = instr.opname[7:]
                            # For Python 3.11+, BINARY_OP uses instr.arg (not instr.argval)
                            # Map arg to operator
                            ops_3_11 = {0: '+', 1: '&', 2: '//', 3: '<<', 4: '@', 5: '*', 6: '%', 7: '|', 8: '**', 9: '>>', 10: '-', 11: '/', 12: '^'}
                            
                            if opname == "OP":
                                symbol_code = ops_3_11.get(instr.arg, '?')
                            else:
                                # Older Python style - map opname to operator
                                opnames = ("ADD", "AND", "FLOOR_DIVIDE", "LSHIFT", "MATRIX_MULTIPLY", "MULTIPLY", "MODULO", "OR", "POWER", "RSHIFT", "SUBTRACT", "TRUE_DIVIDE", "XOR")
                                operators = ('+', '&', '//', '<<', '@', '*', '%', '|', '**', '>>', '-', '/', '^')
                                ops = dict(zip(opnames,operators))
                                symbol_code = ops.get(opname, '?')
                                if symbol_code == '?':
                                     raise ValueError(f"Unable to find binary operation {instr.opname}")

                            right = STACK.pop(-1)
                            if verbose: print(f"Operation completed: {STACK[-1]}{symbol_code}{right}")
                            STACK[-1] = STACK[-1] + symbol_code + right

                        elif instr.opname.startswith("BUILD_"):
                            if instr.opname.endswith("_EXTEND"):
                                raise ValueError("HOLY SHIT _EXTEND IS STILL REAL FUUUUUUUUUUUU-")
                            arrays_names = ["LIST", "TUPLE", "SET", "MAP"]
                            arrays_symbols = ["[]", "()", "{}", "{}"]
                            arr_data = dict(zip(arrays_names, arrays_symbols))
                            
                            name = instr.opname[6:]
                            left, right = arr_data.get(name)

                            n = instr.argval
                            if verbose: print(f"Constructing {name} of {n} element(s): {', '.join(STACK[-n:])}")
                            new_iterable = ""
                            for _ in range(n):
                                if name == "MAP":
                                    key, val = STACK.pop(-2), STACK.pop(-1)
                                    string = f"{key}: {val}, "
                                else:
                                    string = f"{STACK.pop(-1)}, "
                                new_iterable = string + new_iterable

                            new_iterable = left + new_iterable[:-2] + right # remove the final ', '
                            STACK.append(new_iterable)
                        
                        else:
                            if verbose: print(f"ERROR!! unexpected opname '{instr.opname}'")

                if verbose: print(" ".join(STACK))
        else:
            raise ValueError(f"ERROR!! Unexpected return code '{instr.opname}'")
    
    def from_string(self):
        pass
    
    def analyse(key):
        """Deconstruct a lambda into its main components and print a chronological table"""
        instructions = list(dis.get_instructions(key))
        for instr in instructions:
            print(f"{(instr.opname+'  ('+str(instr.opcode)+')'):30}| arg={str(instr.arg):7} argval={instr.argval}\n")


################################################################################################################################


class iu_list(list):
    def __init__(self, iterable, replace_all=False):
        self._apply_key = False
        if replace_all:
            iterable = deep_replace(iterable, iu_list)
        self.is_reversed = False
        self._key = iu_lambda(lambda x:x)
        self.sorted = self.is_sorted()
        self.hash_history = set()
        self.current_hash = self.last_saved_hash = None
        super().__init__(iterable)

    def __repr__(self):
        return f"iu_list({super().__repr__()})"

    def __setitem__(self,index,value):
        self.current_hash = None
        if self._apply_key:
            pass
        super().__setitem__(index,value)
        if self.sorted:
            self.sorted = self.is_sorted(index)

    def __getitem__(self, index):
        item = super().__getitem__(index)
        if self._apply_key is True:
            item = self._key.key(item)
        return item

    def Type(self):
        return type(self)

    def reverse(self):
        self.current_hash = None
        super().reverse()
        self.is_reversed = not self.is_reversed
        return self

    def append(self,x):
        self.current_hash = None
        super().append(x)
        self.sorted = self.is_sorted(-1)

    def extend(self, iterable):
        self.current_hash = None
        pre_extend_length = len(self)
        super().extend(iterable)
        for i in range(len(iterable)):
            if not self.is_sorted(pre_extend_length + i):
                self.sorted = False
                break
        
    def insert(self, index, x):
        self.current_hash = None
        super().insert(index, x)
        self.sorted = self.is_sorted(index)

    def sort(self, *, reverse=None, key=None):
        
        # check if list already sorted
        if self.sorted and iu_lambda(key).formula==self._key.formula:
            # list is sorted so simply check reverse
            if reverse:
                self.reverse()
                self.current_hash = None
            print("bypassed!!")
            return self


        self.current_hash = None
        if not callable(key):
            key = self._key.key
        if reverse is not None:
            self.is_reversed = reverse
        super().sort(key=key, reverse=self.is_reversed)
        self.sorted = True
        return self

    @property
    def len(self):
        return super().__len__()

    def clamped(self, index):
        return self[clamp(self,index)]

    def is_sorted(self, i=..., *, reverse=None, key=None):
        return is_sorted(self, i, reverse=reverse, key=key)

    def merge_sort(self, *, reverse=False, key=lambda x:x, visual=True):
        # check bytecode of keys to check for similarity & bypass
        if self.sorted and iu_lambda(key).formula==self._key.formula:
            if reverse:
                self.reverse()
                self.current_hash = None
            print("bypassed!!")
            return self

        if not callable(key):
            key = self._key.key
        else:
            self._key = iu_lambda(key)

        if reverse is not None:
            self.is_reversed = reverse
        reverse = -1 if self.is_reversed else 1
        
        iterable = merge_sort(self, reverse=reverse, key=key, visual=visual)
        self.sorted = True
        return self

    def binary_search(self, target, *, reverse=None, key=None, override_sorted=False):
        return binary_search(self, target, reverse=reverse, key=key, override_sorted=override_sorted)

    def __hash__(self): 
        self.current_hash = hash(tuple(self))
        return self.current_hash
    
    def clear_hashes(self):
        self.hash_history.clear()

    def save_current_hash(self):
        if self.current_hash is None:
            hash(self)
        self.last_saved_hash = self.current_hash
        self.hash_history.add(current_hash)

    def set_key(self, key):
        self._key.key = iu_key(key)

    def activate_key(self):
        self._apply_key = True
    
    def deactivate_key(self):
        self._apply_key = False

    @property
    def with_key_applied(self):
        return iu_list([self._key.key(item) for item in self])

    def deep_max(self, *, iterable=None, index=0):
        if iterable is None:
            iterable = self
        left = iterable[index]
        if is_iterable(left, exclude_string=True):
            left = deep_max(left)
        if index == len(iterable) - 1:
            return left
        right = deep_max(iterable, index+1)
        return max(left, right)

    def deep_min(self, *, iterable=None, index=0):
        if iterable is None:
            iterable = self
        left = iterable[index]
        if is_iterable(left, exclude_string=True):
            left = deep_min(left)
        if index == len(iterable) - 1:
            return left
        right = deep_min(iterable, index+1)
        return min(left, right)
