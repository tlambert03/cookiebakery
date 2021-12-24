import ast
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from jinja2 import Environment
from pydantic import BaseModel, root_validator
from pydantic.fields import Field

from ._rich import Confirm, Prompt

if TYPE_CHECKING:
    from typing import Protocol

    class Whenable(Protocol):
        when: Optional[str]


def render_context(string: str, context: dict) -> str:
    template = Environment().from_string(string.replace(r"${{", r"{{"))
    return template.render(context)


def should_execute(obj: "Whenable", context: dict) -> bool:
    if obj.when is None:
        return True
    return ast.literal_eval(render_context(obj.when, context))


class Step(BaseModel):
    key: str
    default: Union[str, int, bool, None] = None
    prompt_text: Optional[str] = None
    choices: Optional[List[str]] = None
    response: Optional[str] = None
    when: Optional[str] = None

    @root_validator(pre=True)
    def _validate_root(cls, values: dict) -> dict:
        # convenience for providing a single {key: value} where `key` is `key`,
        # and `value` is `default`... and if `default` is a list, it populates options
        if isinstance(values, dict) and len(values) == 1:
            [(key, default)] = list(values.items())
            choices = None
            if isinstance(default, (list, tuple)) and default:
                choices = default
                default = default[0]
            values = {"key": key, "default": default, "choices": choices}

        # make sure default is one of choices, if choices is provided
        if (
            values.get("default")
            and values.get("choices")
            and values["default"] not in values["choices"]
        ):
            raise ValueError(f"{values['default']} is not one of {values['choices']}")

        # change 'if' to 'when' ... if should be allowed in yaml, etc...
        # but is a reserved python keyword
        if "if" in values:
            values["when"] = values.pop("if")

        return values

    def prompt(self, context: dict) -> Any:
        prompt = self.prompt_text or self.key
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


# similar to job
class Phase(BaseModel):
    steps: List[Step]
    name: Optional[str] = None
    when: Optional[str] = None

    def execute(self, context: dict) -> dict:
        context["steps"] = {}
        for step in self.steps:
            if should_execute(step, context):
                context["steps"][step.key] = step.prompt(context)
        return context


class Workflow(BaseModel):
    name: Optional[str] = None
    depends: List[str] = Field(default_factory=list)
    phases: Dict[str, Phase]

    def execute(self) -> dict:
        context: Dict[str, Any] = {"phases": {}}
        for phase_id, phase in self.phases.items():
            if should_execute(phase, context):
                context["phases"][phase_id] = phase.execute(context)
        return context

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "Workflow":
        path = Path(path)
        if path.suffix in (".yaml", ".yml"):
            import yaml

            with open(path) as f:
                d = yaml.safe_load(f)
        elif path.suffix == ".json":
            import json

            with open(path) as f:
                d = json.load(f)
        else:
            raise ValueError("unrecognized extension", path.suffix)
        assert d, f"No data retrieved from {path}"
        return cls(**d)
