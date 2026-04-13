from collections.abc import Iterable
from collections import deque

def clamp(iterable, index):
    """clamps an input index between 0 and len(iterable)-1"""
    if type(index) is not int:
        raise ValueError(f"Invalid type for index: expected <int>, got {type(index)}.")
    return min(max(0,index), len(iterable)-1)

def is_iterable(obj, include_string=False):
    "Returns True if obj is an iterable, optionally accepting strings (rejected by default)"
    is_string = isinstance(obj, (str, bytes, bytearray)) 
    if is_string:
        if include_string is True:
            if len(obj) == 1:return False # a single character is not iterable
            return True 
        else:
            return False
    return isinstance(obj, Iterable)

def deep_max(iterable, index=0, dtype=int):
    "Walks through iterable tree to find the highest value of type `dtype`, defaulting to <int>."
    if isinstance(dtype, tuple):
        raise ValueError("Argument <dtype> expected non-iterable, got tuple.")

    left = iterable[index]
    if is_iterable(left, include_string=False):
        left = deep_max(left)
    if index == len(iterable) - 1:
        return left
    
    right = iterable[index:]
    if is_iterable(right, include_string=False):
        right = deep_max(iterable, index+1)
    
    if not isinstance(left, dtype):
        return right if isinstance(right, dtype) else None
    if not isinstance(right, dtype):
        return left

    return max(left, right)

def deep_min(iterable, index=0, dtype=int):
    "Walks through iterable tree to find the lowest value of type `dtype`, defaulting to <int>."
    if isinstance(dtype, tuple) and len(dtype) > 1:
        raise ValueError("Argument <dtype> expected singular type, got tuple.")

    left = iterable[index]
    if is_iterable(left, include_string=False):
        left = deep_min(left)
    # ensure list length not exceeded
    if index == len(iterable) - 1:
        return left

    right = iterable[index:]
    if is_iterable(right, include_string=False):
        right = deep_min(iterable, index+1)

    if not isinstance(left, dtype):
        return right if isinstance(right, dtype) else None
    if not isinstance(right, dtype):
        return left

    return min(left, right)

def deep_dtype(iterable, target_type):
    if isinstance(iterable, dict):
        iterable = iterable.items()
    iterable = list(iterable)
    for index, item in enumerate(iterable):
        if is_iterable(item, include_string=False):
            iterable[index] = deep_dtype(item, target_type)
    return target_type(iterable)

def get_attributes(obj):
    attrs = {}

    # Case 1: normal objects with __dict__
    if hasattr(obj, "__dict__"):
        attrs.update(vars(obj))

    # Case 2: __slots__ objects
    if hasattr(obj, "__slots__"):
        slots = obj.__slots__
        if isinstance(slots, str):  # in case someone wrote __slots__ = "x"
            slots = (slots,)
        for attr in slots:
            if hasattr(obj, attr):
                attrs[attr] = getattr(obj, attr)

    return attrs

def BFS_index(iterable, target, start=0, end=None, *, exclude=None):
    "Walks through iterable tree (including dicts and strings if target is 1 char) to find the first index of target value using breadth-first search. "
    "Constrains search to start <= index <= end at the top level, excluding indexes in exclude list. Returns path with keys for dicts, indices for sequences."
    
    # If target is a single character, allow searching within strings
    include_string_in_search = isinstance(target, str) and len(target) == 1
    
    # Calculate end if not provided
    if end is None:
        try:
            end = len(iterable) - 1
        except TypeError:
            end = float('inf')
    
    # Validate start and end
    if start > end:
        raise ValueError(f"start ({start}) must be <= end ({end})")
    
    # Handle and validate exclude
    if exclude is None:
        exclude = set()
    else:
        if not isinstance(exclude, (list, tuple, set)):
            if isinstance(exclude, int):
                exclude = {exclude}
            else:
                raise TypeError(f"exclude must be a list, tuple, or set, got {type(exclude)}")
        else:
            exclude = set(exclude)
        for idx in exclude:
            if not isinstance(idx, int):
                raise TypeError(f"exclude must contain only integers, got {type(idx)}")
    
    queue = deque([(iterable, [], 0)])  # (current_iter, path, depth)
    
    while queue:
        current_iter, path, depth = queue.popleft()
        
        if isinstance(current_iter, dict):
            for key, value in current_iter.items():
                # Apply constraints only at depth 0 for integer keys
                if depth == 0 and isinstance(key, int) and not (start <= key <= end):
                    continue
                if depth == 0 and isinstance(key, int) and key in exclude:
                    continue
                
                if value == target:
                    return path + [key]
                # Recurse into non-string iterables, or multi-char strings if searching for 1 char
                should_recurse = (is_iterable(value, include_string=False) or 
                                 (include_string_in_search and isinstance(value, str) and len(value) > 1))
                if should_recurse:
                    queue.append((value, path + [key], depth + 1))
        else:
            for i, item in enumerate(current_iter):
                # Apply constraints only at depth 0
                if depth == 0 and not (start <= i <= end):
                    continue
                if depth == 0 and i in exclude:
                    continue
                
                if item == target:
                    return path + [i]
                # Recurse into non-string iterables, or multi-char strings if searching for 1 char
                should_recurse = (is_iterable(item, include_string=False) or 
                                 (include_string_in_search and isinstance(item, str) and len(item) > 1))
                if should_recurse:
                    queue.append((item, path + [i], depth + 1))
    
    raise ValueError(f"Value {target} not found in iterable.")

def DFS_index(iterable, target, start=0, end=None, *, exclude=None):
    "Walks through iterable tree (including dicts and strings if target is 1 char) to find the first index of target value using depth-first search. "
    "Constrains search to start <= index <= end at the top level, excluding indexes in exclude list. Returns path with keys for dicts, indices for sequences."
    
    # If target is a single character, allow searching within strings
    include_string_in_search = isinstance(target, str) and len(target) == 1
    
    # Calculate end if not provided
    if end is None:
        try:
            end = len(iterable) - 1
        except TypeError:
            end = float('inf')
    
    # Validate start and end
    if start > end:
        raise ValueError(f"start ({start}) must be <= end ({end})")
    
    # Handle and validate exclude
    if exclude is None:
        exclude = set()
    else:
        if not isinstance(exclude, (list, tuple, set)):
            if isinstance(exclude, int):
                exclude = {exclude}
            else:
                raise TypeError(f"exclude must be a list, tuple, or set, got {type(exclude)}")
        else:
            exclude = set(exclude)
        for idx in exclude:
            if not isinstance(idx, int):
                raise TypeError(f"exclude must contain only integers, got {type(idx)}")
    
    def _dfs_helper(current_iter, path, depth):
        if isinstance(current_iter, dict):
            for key, value in current_iter.items():
                # Apply constraints only at depth 0 for integer keys
                if depth == 0 and isinstance(key, int) and not (start <= key <= end):
                    continue
                if depth == 0 and isinstance(key, int) and key in exclude:
                    continue
                
                if value == target:
                    return path + [key]
                # Recurse into non-string iterables, or multi-char strings if searching for 1 char
                should_recurse = (is_iterable(value, include_string=False) or 
                                 (include_string_in_search and isinstance(value, str) and len(value) > 1))
                if should_recurse:
                    result = _dfs_helper(value, path + [key], depth + 1)
                    if result is not None:
                        return result
        else:
            for i, item in enumerate(current_iter):
                # Apply constraints only at depth 0
                if depth == 0 and not (start <= i <= end):
                    continue
                if depth == 0 and i in exclude:
                    continue
                
                if item == target:
                    return path + [i]
                # Recurse into non-string iterables, or multi-char strings if searching for 1 char
                should_recurse = (is_iterable(item, include_string=False) or 
                                 (include_string_in_search and isinstance(item, str) and len(item) > 1))
                if should_recurse:
                    result = _dfs_helper(item, path + [i], depth + 1)
                    if result is not None:
                        return result
        
        return None
    
    result = _dfs_helper(iterable, [], 0)
    if result is not None:
        return result
    
    raise ValueError(f"Value {target} not found in iterable.")

def deep_count(iterable, value, substring=False):
    "Return the number of times <value> is can be found across the entire iterable tree."
    def _dc_helper(iterable, value, substring=substring):
        total = 0
        for item in iterable:
            if is_iterable(item, include_string=substring):
                total += _dc_helper(item, value, substring)
            else:
                if item == value:
                    total += 1
        return total

    if not is_iterable(iterable, include_string=substring):
        raise ValueError(f"Object of type {type(iterable) is not iterable}")
    
    return _dc_helper(iterable, value, substring)

        
        
