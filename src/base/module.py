import sys
import argparse
import importlib
import inspect
from typing import Callable, Union, Any
from types import ModuleType
from dataclasses import dataclass

from asimov import io


@dataclass
class SignatureError:
    func_name: str
    expected: str
    found: str
    reason: str | None = None

    def __str__(self):
        msg = (
            f"{self.func_name}() signature mismatch{{f6}}"
            f"Expected:{{f6}}  {self.expected}{{f6}}"
            f"Found:{{f6}}  {self.found}"
        )
        if self.reason:
            msg += f"{{f6}}Reason:{{f6}}  {self.reason}"
        return msg


# --- Utility Functions ---


# @since 20251221
def get(module_input: Union[str, ModuleType], args: Any = None) -> ModuleType:
    """
    Utility to resolve a module reference.
    If input is a string, it loads the module via load().
    If it's already a module object, it returns it.
    """
    if isinstance(module_input, ModuleType):
        return module_input

    if isinstance(module_input, str):
        return load(args, module_input)

    raise ValueError(
        f"Expected module name (str) or module object, got {type(module_input)=}"
    )


# @since 20230510
def load(args: Any, modulepath: str) -> ModuleType:
    """
    Loads a module from a string path.
    Preserves BC and handles conditional reloading in debug mode.
    """
    debug = getattr(args, "debug", False) if args else False

    if modulepath in sys.modules and debug:
        pass
    ###        io.echo(f"{modulepath=} is in sys.modules. reloading.", level="debug")
    ###        importlib.reload(sys.modules[modulepath])

    try:
        m = importlib.import_module(modulepath)
        return m
    except Exception:
        # Integrated echo_traceback for import failures
        io.echo_traceback(f"module {modulepath=} not importable")
        raise


# --- Logic and Validation ---


def _check_params(
    func_name: str, params: dict, required: list, optional_kwargs: bool = False
):
    """Internal helper to verify function signatures."""
    for p in required:
        if p not in params:
            io.echo(f"missing '{p}' from {func_name}()", level="error")
            return False
    if not optional_kwargs and "kw" not in params and "kwargs" not in params:
        io.echo(f"missing 'keyword args' in {func_name}()", level="error")
        return False
    return True


def _check_func_return(func_ann, stub_ann):
    # Stub doesn't care → accept anything
    if stub_ann is inspect._empty:
        return True

    # Function didn't annotate → reject
    if func_ann is inspect._empty:
        return False

    # Exact match
    if func_ann == stub_ann:
        return True

    # Handle Optional[T] == Union[T, None]
    from typing import get_origin, get_args, Union

    def normalize(ann):
        origin = get_origin(ann)
        if origin is Union:
            return set(get_args(ann))
        return {ann}

    return normalize(func_ann) == normalize(stub_ann)


def _format_signature(func, name=None):
    sig = inspect.signature(func)
    fname = name or func.__name__
    return f"{fname}{sig}"


def _kind_compatible(func_kind, stub_kind):
    if stub_kind is inspect.Parameter.POSITIONAL_ONLY:
        return func_kind is inspect.Parameter.POSITIONAL_ONLY

    if stub_kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    ):
        return func_kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )

    return func_kind == stub_kind


def _check_func_signature(
    func, stub, *, name=None, allow_extra=True, enforce_return=True
):
    sig_func = inspect.signature(func)
    sig_stub = inspect.signature(stub)

    f_params = list(sig_func.parameters.values())
    s_params = list(sig_stub.parameters.values())

    f_name = name or func.__name__

    def fail(reason=None):
        return SignatureError(
            func_name=f_name,
            expected=f"{f_name}{sig_stub}",
            found=f"{f_name}{sig_func}",
            reason=reason,
        )

    if len(f_params) < len(s_params):
        return False

    for i, s in enumerate(s_params):
        f = f_params[i]

        if f.name != s.name:
            return fail(f"parameter {i + 1} should be '{s.name}'")

        if not _kind_compatible(f.kind, s.kind):
            return fail(f"'{s.name}' must be positional-only")

        if s.default is inspect._empty and f.default is not inspect._empty:
            return fail(f"'{s.name}' must not have a default")

    if not allow_extra and len(f_params) != len(s_params):
        return fail("too many parameters")

    if enforce_return:
        if not _check_func_return(
            sig_func.return_annotation, sig_stub.return_annotation
        ):
            return fail("return type mismatch")

    return True


# @since 20220826
def check(
    args: argparse.Namespace, mod_ref: Union[str, ModuleType], **kwargs
) -> bool | None:
    """
    Validates module interface and functional access.
    """
    silent = kwargs.get("silent", True)
    op = kwargs.pop("op", "run")

    m = get(mod_ref, args)

    # 1. Interface Check
    for func_name in ["init", "access", "buildargs", "main"]:
        if not hasattr(m, func_name):
            if not silent:
                io.echo(f"no {func_name} function", level="error")
            return False
        if not callable(getattr(m, func_name)):
            if not silent:
                io.echo(f"{func_name} is not callable", level="error")
            return False

    # 2. Signature verification
    if not _check_func_signature(m.init, _stub_init):
        io.echo("init() signature invalid", level="error")
        return False

    if not _check_func_signature(m.buildargs, _stub_buildargs):
        io.echo("buildargs() signature invalid", level="error")
        return False

    if not _check_func_signature(m.main, _stub_main):
        io.echo("main() signature invalid", level="error")
        return False

    if not _check_func_signature(m.access, _stub_access):
        if not silent:
            io.echo(
                "access() signature mismatch{f6:2}"
                f"Expected:{{f6}}  {_format_signature(_stub_access, 'access')}{{f6:2}}"
                f"Found:{{f6}}  {_format_signature(m.access)}",
                level="error",
            )
        return False

    # 3. Functional Access Check
    try:
        if m.access(args, op, **kwargs) is not True:
            if not silent:
                io.echo(f"access check failed for op: {op}", level="error")
            return False
    except Exception:
        if not silent:
            # Integrated echo_traceback for access function crashes
            io.echo_traceback("call to access function failed. traceback:")
        return False

    return True


# @since 20230510
def runcallback(
    args: argparse.Namespace,
    callback: Union[Callable, str],
    optional: bool = False,
    **kwargs,
):
    """
    Executes a callback. Supports 'module.func' strings OR direct callables for BC.
    """
    if callback is None:
        return None

    if callable(callback):
        try:
            return callback(args, **kwargs)
        except Exception:
            io.echo_traceback(
                f"runcallback: callable {getattr(callback, '__name__', 'anon')} failed"
            )
            return None

    parts = callback.split(".")
    modpath = ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
    fname = parts[-1] if len(parts) > 1 else "main"

    try:
        m = load(args, modpath)
        func = getattr(m, fname)
        if callable(func):
            return func(args, **kwargs)
    except Exception:
        if not optional:
            io.echo_traceback(f"runcallback: string-path {callback} failed")
        return None


# @since 20220727
def run(args: argparse.Namespace, mod_ref: Union[str, ModuleType], **kwargs):
    """
    Main lifecycle: check (with access) -> init -> buildargs -> main.
    """
    m = get(mod_ref, args)

    if check(args, m, **kwargs) is False:
        return False

    try:
        runcallback(args, m.init, **kwargs)

        argv = kwargs.get("argv", [])
        prgargparser = runcallback(args, m.buildargs, **kwargs)
        if prgargparser:
            try:
                prgargparser.parse_args([a.strip() for a in argv[1:]])
            except (SystemExit, argparse.ArgumentError):
                return False

        return runcallback(args, m.main, **kwargs)
    except Exception:
        # Integrated echo_traceback for module lifecycle crashes
        io.echo(
            f"CRITICAL: Module '{getattr(m, '__name__', 'unknown')}' crashed.",
            level="critical",
        )
        if getattr(args, "debug", False):
            io.echo_traceback()
        return False


runmodule = run


# @since 20260106
def check_func(
    mod_ref: Union[str, ModuleType],
    func_name: str,
    required_signature: Callable,
    *,
    allow_extra: bool = True,
    enforce_return: bool = True,
    silent: bool = False,
) -> bool:
    """
    Validate that a module function matches a required signature.

    This uses the same compatibility rules as module.check():
    - positional-only enforcement
    - default value rules
    - optional extra parameters
    - Optional[T] / Union[T, None] return compatibility

    Returns True on success, False on failure.
    """
    try:
        module = get(mod_ref)
    except Exception:
        if not silent:
            io.echo_traceback("validate_function: failed to resolve module")
        return False

    if not hasattr(module, func_name):
        if not silent:
            io.echo(f"validate_function: '{func_name}' not found", level="error")
        return False

    func = getattr(module, func_name)
    if not callable(func):
        if not silent:
            io.echo(f"validate_function: '{func_name}' is not callable", level="error")
        return False

    result = _check_func_signature(
        func,
        required_signature,
        name=func_name,
        allow_extra=allow_extra,
        enforce_return=enforce_return,
    )

    if result is not True:
        # result is a SignatureError
        if not silent:
            io.echo(str(result), level="error")
        return False

    return True


# @since 20260106
def validate_function(*args, **kwargs) -> bool:
    """
    Backward-compatible alias for check_function().
    Prefer check_func() for new code.
    """
    return check_func(*args, **kwargs)


def _stub_access(args: argparse.Namespace, op: str, /, **kwargs: dict) -> bool | None:
    pass


def _stub_init(args: argparse.Namespace, /, **kwargs: dict) -> bool | None:
    pass


def _stub_buildargs(
    args: argparse.Namespace, **kwargs: dict
) -> argparse.ArgumentParser | None:
    pass


def _stub_main(args: argparse.Namespace, /, **kwargs: dict) -> bool | None:
    pass


def _stub_version(args: argparse.Namespace, /, **kwargs: dict) -> str:
    pass
