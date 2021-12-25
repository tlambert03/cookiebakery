import readline  # noqa
from typing import TYPE_CHECKING, TypeVar

from rich import prompt

if TYPE_CHECKING:
    from rich.text import Text

Confirm = prompt.Confirm
DefaultType = TypeVar("DefaultType")

# Prompt subclass that allows using numbers for choices
# until https://github.com/willmcgugan/rich/issues/1776


class Prompt(prompt.Prompt):
    def __init__(self, *args, show_digits: bool = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.show_digits = bool(self.choices) if show_digits is None else show_digits

    @classmethod
    def ask(cls, *args, show_digits: bool = None, **kwargs):
        default = kwargs.pop("default", ...)
        stream = kwargs.pop("stream", None)
        _prompt = cls(*args, **kwargs)
        return _prompt(default=default, stream=stream)

    def make_prompt(self, default: DefaultType) -> "Text":
        if not self.show_choices or not self.choices or not self.show_digits:
            return super().make_prompt(default)

        # build prompt with choices
        prompt = self.prompt.copy()
        choices = "\n".join(f"{i+1} - {ch}" for i, ch in enumerate(self.choices))
        prompt.append("\n" + choices, "prompt.choices")
        prompt.append(f"\nChoose from 1-{len(self.choices)}", style="#888888")
        if (
            default != ...
            and self.show_default
            and isinstance(default, (str, self.response_type))
        ):
            prompt.append(" ")
            _default = self.render_default(self.choices.index(default) + 1)
            prompt.append(_default)
        prompt.append(self.prompt_suffix)
        return prompt

    def check_choice(self, value: str) -> bool:
        assert self.choices is not None
        v = value.strip()
        if self.show_digits and self.choices:
            try:
                return 1 <= int(v) <= len(self.choices)
            except ValueError:
                pass
        return v in self.choices

    def process_response(self, value: str) -> str:
        return_value = super().process_response(value)
        if self.choices is not None and return_value not in self.choices:
            return self.choices[int(value) - 1]
        return return_value
