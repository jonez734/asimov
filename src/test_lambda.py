import inspect

FRUITS = ["apple", "banana", "cherry", "date", "elderberry"]

# The lambda from the demo
func = lambda p, **kwargs: [f for f in FRUITS if f.startswith(p.lower())] if p else []

# Test introspection logic
sig = inspect.signature(func)
print(f"Signature: {sig}")
has_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())
print(f"Has kwargs: {has_kwargs}")

# Test calling
try:
    res = func("a", curpos=1)
    print(f"Result for 'a': {res}")
except Exception as e:
    print(f"Error calling func: {e}")

# Test empty
res = func("", curpos=0)
print(f"Result for '': {res}")
