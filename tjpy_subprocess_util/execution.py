import sys

import logging
import subprocess
from pathlib import Path
from subprocess import CompletedProcess
from typing import Any, IO, Iterable, List, Optional, Union

from tjpy_subprocess_util.exception import SubProcessExecutionException, SubProcessStartException

_logger = logging.getLogger(__name__)


class Result:
    def __init__(self,
                 exit_code: int,
                 stdout: str,
                 stderr: str):
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr

    @property
    def trimmed_stdout(self):
        # the output of a sub-process normally ends with a new line for formatting purposes
        # however, it is not part of the value that is being returned from the sub-process
        # this utility property automatically removes this formatting new-line
        if self.stdout.endswith("\n"):
            return self.stdout[:-1]
        else:
            return self.stdout


class SubProcessExecution:

    @staticmethod
    def execute(args: List[str],
                check_error_code: bool = True,
                follow_output: bool = False,
                working_directory: Path = None,
                logging_level: str = "DEBUG",
                custom_input: Optional[str] = None) -> Result:
        SubProcessExecution._log_execute_call(args, working_directory, logging_level)

        stdout: Union[None, int, IO[Any]] = sys.stdout if follow_output else subprocess.PIPE
        stderr: Union[None, int, IO[Any]] = sys.stderr if follow_output else subprocess.PIPE
        stdin: Union[None, int, IO[Any]] = sys.stdin if custom_input is None else None
        try:
            result: CompletedProcess = subprocess.run(
                args,
                cwd=working_directory,
                stdout=stdout,
                stderr=stderr,
                stdin=stdin,
                input=custom_input,
                encoding="utf-8"
            )

            if check_error_code:
                if result.returncode != 0:
                    if not follow_output:
                        if len(result.stdout) != 0:
                            _logger.info("Stdout of failed command:\n" + result.stdout)
                        if len(result.stderr) != 0:
                            _logger.info("Stderr of failed command:\n" + result.stderr)
                    else:
                        _logger.info("Output of failed command has been redirected to stdout and stderr streams.")
                        pass
                result.check_returncode()
            else:
                if follow_output:
                    pass
        except subprocess.CalledProcessError as called_sub_process_error:
            raise SubProcessExecutionException(list(args),
                                               called_sub_process_error.returncode,
                                               SubProcessExecution._output_to_string(called_sub_process_error.stdout),
                                               SubProcessExecution._output_to_string(called_sub_process_error.stderr),
                                               ) from called_sub_process_error
        except subprocess.SubprocessError as sub_process_error:
            raise SubProcessStartException(list(args)) from sub_process_error
        return Result(
            exit_code=result.returncode,
            stdout=SubProcessExecution._output_to_string(result.stdout),
            stderr=SubProcessExecution._output_to_string(result.stderr)
        )

    @staticmethod
    def _output_to_string(output):
        return "" if output is None else str(output)

    @staticmethod
    def _log_execute_call(args: Iterable[str], working_directory: Optional[Path], log_level: str):
        command_text = SubProcessExecution._get_command_text_for_logging(args, working_directory)
        log_level_int: int = logging._nameToLevel[log_level]
        _logger.log(log_level_int, f"Executing command: {command_text}")

    @staticmethod
    def _get_command_text_for_logging(args: Iterable[str], working_directory: Optional[Path]) -> str:
        working_directory_note = ""
        if working_directory is not None:
            working_directory_note = f" in {working_directory}"
        filler = '" "'
        formatted_args = f'"{filler.join(list(args)[1:])}"'
        return f"{next(iter(args))} {formatted_args}{working_directory_note}"
