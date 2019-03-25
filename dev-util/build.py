import os
import re

import subprocess
from pathlib import Path
from typing import List

output_logs_if_successful = False
project_name = "tjpy_subprocess_util"

project_directory: Path = Path(os.getcwd()).parent
assert project_directory.joinpath("Makefile").exists()


def execute_and_translate_to_absolute_filenames(command: List[str]):
    print(f"{' '.join(command)} ... ", end="")
    # output_pipe = os.pipe()
    result: subprocess.CompletedProcess = subprocess.run(
        command,
        cwd=str(project_directory),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        encoding="utf-8",
    )
    if result.returncode != 0:
        print(f"failed with exit code {result.returncode}")
        _print_output(result)
        exit(1)
    else:
        print("success")
        if output_logs_if_successful:
            _print_output(result)


def _print_output(result: subprocess.CompletedProcess):
    stdout = _replace_source_paths_with_paths_relative_to_this_script(result.stdout)
    stderr = _replace_source_paths_with_paths_relative_to_this_script(result.stderr)
    if len(stdout) != 0:
        print(f"Stdout:\n{stdout}")
    if len(stderr) != 0:
        print(f"Stderr:\n{stderr}")


def _replace_source_paths_with_paths_relative_to_this_script(output: str):
    output_with_absolute_paths: str = re.sub(f"^{project_name}/", f"../{project_name}/",
                                             output, flags=re.RegexFlag.MULTILINE)
    output_with_absolute_paths: str = re.sub(f"^tests/", f"../tests/",
                                             output_with_absolute_paths, flags=re.RegexFlag.MULTILINE)
    return output_with_absolute_paths


execute_and_translate_to_absolute_filenames(["make", "install-dev"])
execute_and_translate_to_absolute_filenames(["pytest"])
execute_and_translate_to_absolute_filenames(["make", "lint"])
execute_and_translate_to_absolute_filenames(["make", "type-check"])
