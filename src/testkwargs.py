kwargs = {"blah": True}


def foo(args, **kwargs):
    kwargs["blah"] = 42


foo("args", bing=False, **kwargs)
print(kwargs)
