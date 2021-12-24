import readline  # noqa
from typing import TypeVar

from rich import prompt
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
        prompt = self.prompt.copy()
        prompt.end = ""

        if self.show_choices and self.choices:
            if not self.show_digits:
                _choices = "/".join(self.choices)
                choices = f"[{_choices}]"
                prompt.append(" ")
                prompt.append(choices, "prompt.choices")
            else:
                prompt = Text()
                _choices_list = [
                    f"[{index+1}] {choice}" for index, choice in enumerate(self.choices)
                ]

                choices = "\n".join(_choices_list)
                prompt.append(choices, "prompt.choices")
                prompt.append("\n")
                prompt.append(self.prompt.copy())
        if (
            default != ...
            and self.show_default
            and isinstance(default, (str, self.response_type))
        ):
            prompt.append(" ")
            if self.show_digits and self.choices:
                _default = self.render_default(self.choices.index(default) + 1)
            else:
                _default = self.render_default(default)
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
