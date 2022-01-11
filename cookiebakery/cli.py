"""Main `cookiebakery` CLI. mostly a patch on top of cookiecutter.cli"""

import os
from unittest.mock import patch

import cookiecutter.cli
from cookiecutter.config import get_user_config
from cookiecutter.exceptions import InvalidModeException
from cookiecutter.generate import generate_files
from cookiecutter.replay import dump, load
from cookiecutter.repository import determine_repo_dir
from cookiecutter.utils import rmtree

from ._schema import Workflow


def find_workflow(repo_directory):
    """Determine if `repo_directory` contains a `cookiecutter.json` file.

    :param repo_directory: The candidate repository directory.
    :return: True if the `repo_directory` is valid, else False.
    """
    if not os.path.isdir(repo_directory):
        return ""

    _byaml = os.path.join(repo_directory, "cookiebakery.yaml")
    if os.path.isfile(_byaml):
        return _byaml

    _cjson = os.path.join(repo_directory, "cookiecutter.json")
    if os.path.isfile(_cjson):
        return _cjson


def generate_context(
    repo_dir, default_context=None, extra_context=None, no_input=False
):
    workflow = Workflow.from_file(find_workflow(repo_dir))
    output = workflow.get_defaults() if no_input else workflow.execute()
    return {"cookiecutter": output["steps"]}


def cookiebakery(
    template,
    checkout=None,
    no_input=False,
    extra_context=None,
    replay=False,
    overwrite_if_exists=False,
    output_dir=".",
    config_file=None,
    default_config=False,
    password=None,
    directory=None,
    skip_if_file_exists=False,
):
    """pretty much exactly cookiecutter, with different generate_context."""
    if replay and ((no_input is not False) or (extra_context is not None)):
        err_msg = (
            "You can not use both replay and no_input or extra_context "
            "at the same time."
        )
        raise InvalidModeException(err_msg)

    config_dict = get_user_config(
        config_file=config_file,
        default_config=default_config,
    )

    repo_dir, cleanup = determine_repo_dir(
        template=template,
        abbreviations=config_dict["abbreviations"],
        clone_to_dir=config_dict["cookiecutters_dir"],
        checkout=checkout,
        no_input=no_input,
        password=password,
        directory=directory,
    )

    template_name = os.path.basename(os.path.abspath(repo_dir))

    if replay:
        context = load(config_dict["replay_dir"], template_name)
    else:

        # prompt the user to manually configure at the command line.
        # except when 'no-input' flag is set
        context = generate_context(
            repo_dir,
            default_context=config_dict["default_context"],
            extra_context=extra_context,
            no_input=no_input,
        )

        # include template dir or url in the context dict
        context["cookiecutter"]["_template"] = template

        dump(config_dict["replay_dir"], template_name, context)

    # Create project from local context and project template.
    result = generate_files(
        repo_dir=repo_dir,
        context=context,
        overwrite_if_exists=overwrite_if_exists,
        skip_if_file_exists=skip_if_file_exists,
        output_dir=output_dir,
    )

    # Cleanup (if required)
    if cleanup:
        rmtree(repo_dir)

    return result


def main():
    p1 = patch(
        "cookiecutter.repository.repository_has_cookiecutter_json",
        new_callable=lambda: find_workflow,
    )
    p2 = patch("cookiecutter.cli.cookiecutter", new_callable=lambda: cookiebakery)

    with p1, p2:
        cookiecutter.cli.main()


if __name__ == "__main__":
    main()
