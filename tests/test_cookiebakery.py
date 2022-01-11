from pathlib import Path
from unittest.mock import patch

import pytest

from cookiebakery import Workflow

TESTS = Path(__file__).parent


@pytest.fixture
def prompt_defaults():
    with patch("rich.prompt.PromptBase.get_input", return_value=""):
        yield


def test_something(prompt_defaults):
    w = Workflow.from_file(TESTS / "steps-test.yaml")

    result = w.execute()
    assert (
        result
        == w.get_defaults()
        == {
            "steps": {
                "some_key1": "Some Value",
                "some_key2": "Some Value",
                "some_key3": 10,
                "some_key4": "10",
                "some_choice1": "some",
                "some_choice2": "some",
                "github_username_or_organization": "githubuser",
                "plugin_name": "napari-foobar",
                "module_name": "napari_foobar",
                "github_repository_url": "https://github.com/githubuser/napari-foobar",
                "short_description": "A simple plugin to use with napari",
                "ask_all_plugins": True,
                "plugin_choice": None,
                "includes": {
                    "include_reader_plugin": True,
                    "include_writer_plugin": True,
                    "include_dock_widget_plugin": True,
                    "include_function_plugin": True,
                },
                "use_git_tags_for_versioning": False,
                "install_precommit": False,
            }
        }
    )


def test_napari(prompt_defaults):
    w = Workflow.from_file(TESTS / "napari-plugin.yaml")
    w.execute()
