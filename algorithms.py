from inspect import getsource
try:
    from .utils import *
except ImportError:
    from utils import *

class SearchObject:
    def __init__(self, iterable=None, target=None, found=None, occurences=0, floor=None, ceil=None, sorted=None, reverse=None, key=None):
        self.iterable = iterable
        self.target = target
        self.found = found
        self.occurences = occurences
        self.floor = floor
        self.ceil = ceil
        self.sorted = sorted
        self.reverse = reverse
        self.key = key
    def __repr__(self):
        return f""" \
SearchObject(iterable={self.iterable},
             target={self.target}, 
             found={self.found}, 
             occurences={self.occurences}, 
             floor={self.floor}, 
             ceil={self.ceil}, 
             sorted={self.sorted}, 
             reverse={self.reverse}, 
             key={getsource(self.key)[27:]})"""


def is_sorted(iterable, i=..., *, is_reversed=None, key=None):
    if not callable(key):
        key = iterable._key if hasattr(iterable, '_key') else lambda x:x

    # check surrounding the index (i) to ensure they are still sorted
    if is_reversed is None:
        is_reversed = iterable.is_reversed if hasattr(iterable, 'is_reversed') else False
    is_reversed = -1 if is_reversed else 1
    rkey = lambda x: is_reversed*key(x)
    
    if i is not ...:
        if type(i) is not int:
            raise ValueError(f"Error: argument `i`: expected <int>, got {type(i)}")
        if i < 0:
            if i < -len(iterable):
                raise ValueError(f"Error: cannot accept negative index {i} exceeding list length {len(iterable)}")
            i = len(iterable) + i
        # key(...)*is_reversed first applies the key to retrieve the desired item, then flips the equality (or not) based on `is_reversed`` (-1 or 1)
        return rkey(clamp(iterable, i-1)) <= rkey(iterable[i]) <= rkey(clamp(iterable, i+1))
    else:
        for index in range(len(iterable)-1):
            if rkey(iterable[index]) > rkey(iterable[index+1]):
                return False
        return True

def merge_sort(iterable, *, reverse=False, key=lambda x:x, visual=False):
    size = len(iterable)
    
    if type(reverse) is bool:
        reverse = -1 if reverse else 1

    if size <= 1:
        return iterable
    right= merge_sort(iterable[size//2:], key=key, reverse=reverse, visual=visual)
    left = merge_sort(iterable[:size//2], key=key, reverse=reverse, visual=visual)
    left_ptr = right_ptr = 0
    for i in range(size):
        if right_ptr == (size - size//2) or (left_ptr != size//2 and key(left[left_ptr])*reverse < key(right[right_ptr])*reverse):
            iterable[i] = left[left_ptr]
            left_ptr += 1
        else:
            iterable[i] = right[right_ptr]
            right_ptr += 1

    return iterable

def binary_search(iterable, target, *, reverse=None, key=None, override_sorted=False):
    """
    Searches for a specific item in a sorted list, returning first & last occurence indexes
    OUTPUTS:
    SearchObject -- successful search lead to either a match or a range of indexes
    -1 -- ERROR: list is not sorted. Can be overriden with `override_sorted=True`
    """
    size = len(iterable)
    if size == 0:
        return SearchObject(iterable=iterable, 
                            target=target, 
                            found=False, 
                            sorted=not override_sorted, 
                            reverse=iterable.is_reversed)
    
    found = False
    occurences = 0

    # check whether the list is sorted in reverse or not
    if reverse is not None:
        iterable.is_reversed = reverse
    rev = -1 if iterable.is_reversed else 1

    # retrieve the sorting key
    if not callable(key):
        key = iterable._key
    rkey = lambda x: rev*key(x)

    # return error if list is not sorted
    if not ((iterable.track_sorted and iterable.sorted) or override_sorted==True):
        return -1

    rtarget = target*rev

    if size == 1:
        ritem = rkey(iterable[0])
        if rtarget == ritem:
            lwr_bound = upr_bound = 0
            found = True
            occurences = 1
        elif rtarget < ritem:
            upr_bound = 0
        else:
            lwr_bound = 0
    else:
        lwr_bound = 0
        upr_bound = size-1
        while upr_bound - lwr_bound > 1:
            ptr = (lwr_bound + upr_bound) // 2
            rval = rkey(iterable[ptr])
            if rval < rtarget:
                lwr_bound = ptr
            elif rval > rtarget:
                upr_bound = ptr
            else:
                # find the lowest occurrence
                while ptr-1 >= 0 and iterable[ptr-1] == iterable[ptr]:
                    ptr -= 1
                lwr_bound = ptr

                # find the highest occurrence
                while ptr+1 < size and iterable[ptr+1] == iterable[ptr]:
                    ptr += 1
                upr_bound = ptr

                found = True
                occurences = upr_bound - lwr_bound + 1
                break
    return SearchObject(iterable=iterable,
                        target=target, 
                        found=found, 
                        occurences=occurences, 
                        floor=lwr_bound, 
                        ceil=upr_bound, 
                        sorted=not override_sorted, 
                        reverse=iterable.is_reversed,
                        key=key)
