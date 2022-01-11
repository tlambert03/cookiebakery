import enum
import os
import subprocess
import tempfile
import warnings
from contextlib import contextmanager, nullcontext
from typing import (
    Generator,
    MutableMapping,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from virtualenv import cli_run

_Unset = enum.Enum("_Unset", "UNSET")
UNSET = _Unset.UNSET


class Var(NamedTuple):
    name: str
    default: str = ""


SubstitutionT = Tuple[Union[str, Var], ...]
ValueT = Union[str, _Unset, SubstitutionT]
PatchesT = Tuple[Tuple[str, ValueT], ...]


def format_env(parts: SubstitutionT, env: MutableMapping[str, str]) -> str:
    return "".join(
        env.get(part.name, part.default) if isinstance(part, Var) else part
        for part in parts
    )


@contextmanager
def envcontext(
    patch: PatchesT,
    _env: Optional[MutableMapping[str, str]] = None,
) -> Generator[None, None, None]:
    """In this context, `os.environ` is modified according to `patch`.

    `patch` is an iterable of 2-tuples (key, value):
        `key`: string
        `value`:
            - string: `environ[key] == value` inside the context.
            - UNSET: `key not in environ` inside the context.
            - template: A template is a tuple of strings and Var which will be
              replaced with the previous environment
    """
    env = os.environ if _env is None else _env
    before = dict(env)

    for k, v in patch:
        if v is UNSET:
            env.pop(k, None)
        elif isinstance(v, tuple):
            env[k] = format_env(v, before)
        else:
            env[k] = v

    try:
        yield
    finally:
        env.clear()
        env.update(before)


def get_env_patch(venv: str) -> PatchesT:
    # On windows there's a different directory for the virtualenv
    bin_part = "Scripts" if os.name == "nt" else "bin"
    bin_dir = os.path.join(venv, bin_part)

    return (
        ("PIP_DISABLE_PIP_VERSION_CHECK", "1"),
        ("PYTHONHOME", UNSET),
        ("VIRTUAL_ENV", venv),
        ("PATH", (bin_dir, os.pathsep, Var("PATH"))),
    )


@contextmanager
def in_env(
    envdir: Optional[str] = None,
    requirements: Sequence[str] = (),
    verbose=False,
) -> Generator[None, None, None]:

    dir_ctx = nullcontext(envdir) if envdir else tempfile.TemporaryDirectory()

    with dir_ctx as _envdir:
        args = [_envdir] + (["--verbose"] if verbose else [])
        with cli_run(args), envcontext(get_env_patch(_envdir)):
            if requirements:
                cmd = ["pip", "install"] + list(requirements)
                if not verbose:
                    cmd += ["-q"]
                subprocess.run(cmd)
            yield
