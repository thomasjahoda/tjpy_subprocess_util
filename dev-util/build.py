import os
import re

import subprocess
import time
from pathlib import Path
from typing import List

output_logs_if_successful = False
project_name = "tjpy_subprocess_util"

project_directory: Path = Path(os.getcwd()).parent
assert project_directory.joinpath("Makefile").exists()


def execute(command: List[str]):
    print(f"{' '.join(command)} ... ", end="")

    start_time_seconds = time.perf_counter()
    result: subprocess.CompletedProcess = subprocess.run(
        command,
        cwd=str(project_directory),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
        encoding="utf-8",
    )
    duration_seconds = time.perf_counter() - start_time_seconds
    duration_output = f"{round(duration_seconds * 1000)}ms"

    if result.returncode != 0:
        print(f"failed with exit code {result.returncode} ({duration_output})")
        _print_output(result)
        exit(1)
    else:
        print(f"success ({duration_output})")
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
    """
    This is necessary that the output has paths relative to this script and not to the project directory.
    Having paths relative to the script will make IDEs create links from the paths in the output.
    """
    output_with_absolute_paths: str = re.sub(f"^{project_name}/", f"../{project_name}/",
                                             output, flags=re.RegexFlag.MULTILINE)
    output_with_absolute_paths: str = re.sub(f"^tests/", f"../tests/",
                                             output_with_absolute_paths, flags=re.RegexFlag.MULTILINE)
    return output_with_absolute_paths


execute(["make", "install-dev"])
execute(["make", "test"])
execute(["make", "flake8"])
execute(["make", "mypy"])
