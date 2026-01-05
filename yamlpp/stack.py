"""
A minimal stack for holding for variables,
behaving as a dictionary




"""
from typing import Any, Dict, List, Optional
from collections.abc import MutableMapping


def _deep_merge(base: Dict[str, Any], incoming: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge, for dictionaries only

    All other types are replaced.
    """
    for k, v in incoming.items():
        if k in base:
            a = base[k]
            # dict vs dict → recurse
            if isinstance(a, MutableMapping) and isinstance(v, MutableMapping):
                base[k] = _deep_merge(dict(a), dict(v))
            else:
                # lists, scalars, or type mismatch → replace
                base[k] = v
        else:
            base[k] = v
    return base


class Stack(MutableMapping):
    """
    A stack of dictionaries representing a
    program's stack.
    Behaves like a dict (mapping protocol).
    """

    def __init__(self, initial:dict={}) -> None:
        "Can be initialized with a dictionary"
        self._stack: List[Dict[str, Any]] = [{}]
        self._cache: Optional[Dict[str, Any]] = None
        self._dirty: bool = True
        self.push(initial)

    def push(self, params: Dict[str, Any]) -> None:
        self._stack.append(params)
        self._dirty = True

    def pop(self) -> None:
        if len(self._stack) > 1:
            self._stack.pop()
            self._dirty = True
        else:
            raise RuntimeError("Cannot pop the base stack")

    def _merged(self) -> Dict[str, Any]:
        """
        Merge the frames (by default all the frames in the stack)
        """
        if self._dirty or self._cache is None:
            merged: Dict[str, Any] = {}
            for scope in self._stack:
                _deep_merge(merged, scope)
            self._cache = merged
            self._dirty = False
        return self._cache
    
    @property
    def capture(self):
        """
        Capture of the current dynamic environment (`self.stack`).

        Returns a snapshot of the flattened environment produced by
        `_merged()` at the moment of access.

        This method is general-purpose: it provides a point-in-time
        environment snapshot for any consumer of the Stack.

        In the specific case of the YAMLpp interpreter, this snapshot is
        to be stored inside a `.function` closure as its definition-time
        environment, and to be used later when the function is invoked
        via `.call`.
        """
        return self._merged()





    # --- Mapping protocol ---
    def __getitem__(self, key: str) -> Any:
        return self._merged()[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._stack[-1][key] = value
        self._dirty = True

    def __delitem__(self, key: str) -> None:
        # delete only from top scope
        if key in self._stack[-1]:
            del self._stack[-1][key]
            self._dirty = True
        else:
            raise KeyError(key)

    def __iter__(self):
        return iter(self._merged())

    def __len__(self) -> int:
        return len(self._merged())

    def __contains__(self, key: str) -> bool:
        return key in self._merged()

    def __repr__(self) -> str:
        return f"Stack({self._stack})"
    
    # --- Copy methods ---
    def copy(self) -> str:
        return self._merged().copy()

    def __copy__(self) -> str:
        return self.copy()
    


# class CassetteRecorder():
#     """
#     CassetteRecorder (implemented with two stacks)
#     """

#     def __init__(self, initial:dict={}) -> None:
#         self._left = Stack(initial)
#         self._right = Stack()

#     def record(self, params: Dict[str, Any]) -> None:
#         "Move one step and record a dictionary on the stack"
#         self._left.push(params)

#     @property
#     def current(self) -> Stack:
#         "The head of the cassette recorder"
#         return self._left
    
#     def back(self) -> None:
#         "Rewind one step"
#         try:
#             last = self._left.pop()
#         except IndexError:
#             raise StopIteration
#         self._right.push(last)

#     def forward(self) -> None:
#         "Forward one step"
#         try:
#             next = self._right.pop()
#         except IndexError:
#             raise StopIteration
#         self._left.push(next)

