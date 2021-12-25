import ast
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

from jinja2 import Environment
from pydantic import BaseModel, root_validator
from pydantic.fields import Field
from rich import traceback
from rich.console import Console

from ._rich import Confirm, Prompt

traceback.install(show_locals=False)


def to_sentence_case(snake_str):
    c0, *c1 = snake_str.split("_")
    return f'{c0.title()} {" ".join(c1)}'


def render_context(string: str, context: dict) -> str:
    template = Environment().from_string(string.replace(r"${{", r"{{"))
    return template.render(context)


class Whenable(BaseModel):
    name: str
    when: Optional[str] = None

    @root_validator
    def if2when(cls, values):
        # change 'if' to 'when' ... if should be allowed in yaml, etc...
        # but is a reserved python keyword
        if "if" in values:
            values["when"] = values.pop("if")
        return values

    def should_execute(self, context: dict) -> bool:
        if self.when is None:
            return True
        try:
            expr = render_context(self.when, context)
        except Exception as e:
            err = (
                f"Failed to parse expression {self.when!r} in step {self.name!r}!\n"
                f"Context: {context}"
            )
            raise type(e)(f"{err}.\n{e}")
        if self.when and not expr:
            err = (
                f"Expression {self.when!r} in step {self.name!r} yielded no result!\n"
                f"Context: {context}"
            )
            raise ValueError(err)
        try:
            return ast.literal_eval(expr)
        except SyntaxError as e:
            raise SyntaxError(f"{e}: repr({expr}), in {self.name}")


class Step(Whenable):
    default: Union[str, int, bool, None] = None
    prompt_text: Optional[str] = None
    choices: Optional[List[str]] = None

    @root_validator(pre=True)
    def _validate_root(cls, values: dict) -> dict:
        # convenience for providing a single {name: value} where `name` is `name`,
        # and `value` is `default`... and if `default` is a list, it populates options
        if isinstance(values, dict) and len(values) == 1:
            [(name, default)] = list(values.items())
            choices = None
            if isinstance(default, (list, tuple)) and default:
                choices = default
                default = default[0]
            values = {"name": name, "default": default, "choices": choices}

        # make sure default is one of choices, if choices is provided
        if (
            values.get("default")
            and values.get("choices")
            and values["default"] not in values["choices"]
        ):
            raise ValueError(f"{values['default']} is not one of {values['choices']}")
        return values

    def prompt(self, context: dict, path=None) -> Any:
        prompt = (self.prompt_text or to_sentence_case(self.name)).strip()
        Console().rule(style="#333333")
        default = render_context(str(self.default), context)
        d_lower = default.lower()
        if d_lower in ("y", "1", "yes", "true", "n", "0", "no", "false"):
            return Confirm.ask(prompt, default=d_lower in ("y", "1", "yes", "true"))

        choices = self.choices
        if choices:
            choices = [render_context(c, context) for c in choices]
        return Prompt.ask(
            prompt, choices=choices, default=default, show_digits=bool(choices)
        )

    execute = prompt


def _update_context(context: dict, path: Tuple[str, ...], value: Any):
    key, *rest = path
    subdict = context
    while rest:
        subdict = subdict.setdefault(key, {})
        key, *rest = rest
    subdict[key] = value


class SubRoutine(Whenable):
    steps: List[Union["SubRoutine", Step]]

    def execute(
        self, _context: dict = None, path: Tuple[str, ...] = ("steps",)
    ) -> dict:
        context = _context or {}
        for step in self.steps:
            _path = (*path, step.name)
            res = step.execute(context, _path) if step.should_execute(context) else None
            if res is not context:
                _update_context(context, _path, res)
        return context


SubRoutine.update_forward_refs()


class Workflow(SubRoutine):
    header: Optional[str] = None
    depends: List[str] = Field(default_factory=list)

    def execute(self) -> dict:  # type: ignore
        Console().print()
        Console().print(self.header, style="green")
        return super().execute(None, path=("steps",))

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "Workflow":
        path = Path(path)
        if path.suffix in (".yaml", ".yml"):
            import yaml

            with open(path) as f:
                data = yaml.safe_load(f)
        elif path.suffix == ".json":
            import json

            with open(path) as f:
                data = json.load(f)
        else:
            raise ValueError("unrecognized extension", path.suffix)
        assert data, f"No data retrieved from {path}"
        return cls(**data)
