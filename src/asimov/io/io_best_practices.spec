# asimov.io Best Practices

## Echo Commands in F-strings

When using echo commands (like `{f6}`, `{bell}`, `{curpos:1,1}`) inside f-strings, you must escape the curly braces:

```python
# Correct - f-string with echo command
echo(f"{{f6}}Some text")

# Incorrect - will cause "f6 is not defined" error
echo(f"{f6}Some text")
```

**Rule:** If you see an error like `"f6" is not defined`, check if the code is inside an f-string and escape the braces with double `{{` and `}}`.

### Common Echo Commands to Escape

| Command | F-string写法 |
|---------|-------------|
| `{f6}` | `{{f6}}` |
| `{bell}` | `{{bell}}` |
| `{curpos:1,1}` | `{{curpos:1,1}}` |
| `{yellow}` | `{{yellow}}` |

## Completer Class

When subclassing `Completer`, override the `get_matches` method:

```python
class MyCompleter(Completer):
    def get_matches(self, prefix, **kwargs):
        # Your logic here
        return ["match1", "match2"]
```

Pass to inputstring:
```python
inputstring("Prompt: ", completer=MyCompleter())
```

Or pass a function:
```python
def my_func(prefix, **kwargs):
    return ["match1", "match2"]

inputstring("Prompt: ", completer=Completer(my_func))
```

## Module Development

### detect() must NEVER draw on the frame

The detect phase is for detection/processing only. All visual rendering must happen in draw().

**Why:**
- Clean separation of concerns
- Modules can run in different threads without frame corruption
- Frame is not mutated during detection phase

**Correct:**
```python
def detect(frame, context, **kwargs):
    # Detection only - no drawing
    hands = detector.findHands(frame)
    context["HANDS"] = hands

def draw(frame, context, **kwargs):
    hands = context.get("HANDS", [])
    for hand in hands:
        # Drawing only
        cv2.circle(frame, ...)
    return frame
```

**Incorrect:**
```python
def detect(frame, context, **kwargs):
    hands = detector.findHands(frame)
    cv2.circle(frame, ...)  # DON'T do this!
    context["HANDS"] = hands
```
