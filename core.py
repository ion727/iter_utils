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
                        cmp_ops = ['<', '<=', '==', '!=', '>', '>=', 'in', 'not in', 'is', 'is not', 'exception match', 'BAD']
                        op = cmp_ops[instr.arg] if instr.arg < len(cmp_ops) else 'UNKNOWN'
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
                        last_global = LOADED_GLOBALS_STACK.pop(-1)
                        STACK[-1] = f"{last_global}({STACK[1]})"
                        if verbose: print(f"retrieved last loaded global '{last_global}'")
                    case "CALL_FUNCTION":
                        last_global = LOADED_GLOBALS_STACK.pop(-1)
                        STACK[-1] = f"{last_global}({STACK[-1]})"
                        if verbose: print(f"retrieved last loaded global '{last_global}'")
                    case "LOAD_ATTR":
                        STACK[-1] += "." + str(instr.argval)
                    case "RETURN_VALUE":
                        return (STACK[-1], index_path, VAR_NAMES, TOTAL_VARS_LOADED)
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
        if self.track_sorted and self.sorted:
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
            self._key.key = key

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