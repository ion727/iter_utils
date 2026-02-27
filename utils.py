import dis
from collections.abc import Iterable

def clamp(iterable, index):
    """clamps an input index between 0 and len(iterable)-1"""
    if type(index) is not int:
        raise ValueError(f"Invalid type for index: expected <int>, got {type(index)}.")
    return min(max(0,index), len(iterable)-1)

def is_iterable(obj, include_string=False):
    "Returns True if obj is an iterable, optionally accepting strings (rejected by default)"
    is_string = isinstance(obj, (str, bytes, bytearray)) 
    return (isinstance(obj, Iterable) and (not is_string or include_string))

def deep_max(iterable, index=0, dtype=int):
    "Walks through iterable tree to find the highest value of type `dtype`, defaulting to <int>."
    if isinstance(dtype, tuple):
        raise ValueError("Argument <dtype> expected singular type, got tuple.")

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

def deep_replace(iterable, target_type):
    if isinstance(iterable, dict):
        iterable = iterable.items()
    iterable = list(iterable)
    for index, item in enumerate(iterable):
        if is_iterable(item, include_string=False):
            iterable[index] = deep_replace(item, target_type)
    return target_type(iterable)
