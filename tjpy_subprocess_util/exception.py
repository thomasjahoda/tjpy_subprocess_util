import logging
from abc import abstractmethod
from typing import List

_logger = logging.getLogger(__name__)


class SubProcessException(Exception):

    def __init__(self,
                 subprocess_args: List[str]
                 ) -> None:
        super().__init__()
        self._subprocess_args = subprocess_args

    @property
    def subprocess_args(self):
        return self._subprocess_args

    @property
    @abstractmethod
    def message(self) -> str:
        pass

    def __str__(self) -> str:
        return self.message


class SubProcessStartException(SubProcessException):

    def __init__(self,
                 subprocess_args: List[str]
                 ) -> None:
        super().__init__(subprocess_args)

    @property
    def message(self) -> str:
        return f"Command {self._subprocess_args} could not be started."


class SubProcessExecutionException(SubProcessException):

    def __init__(self,
                 subprocess_args: List[str],
                 exit_code: int,
                 stdout: str,
                 stderr: str
                 ) -> None:
        self._exit_code = exit_code
        self._stdout = stdout
        self._stderr = stderr
        super().__init__(subprocess_args)

    @property
    def stdout(self):
        return self._stdout

    @property
    def stderr(self):
        return self._stderr

    @property
    def exit_code(self):
        return self._exit_code

    @property
    def message(self) -> str:
        max_characters_per_stream = 2000
        stdout_message_part = self._stdout_in_message(max_characters_per_stream)
        stderr_message_part = self._stderr_in_message(max_characters_per_stream)
        return f"Command {self._subprocess_args} returned non-zero exit code {self.exit_code}." \
            f"{stdout_message_part}" \
            f"{stderr_message_part}"

    def _stdout_in_message(self, max_characters_per_stream: int):
        if len(self.stdout) > max_characters_per_stream:
            trimmed_stdout = self.stdout[len(self.stdout) - max_characters_per_stream:]
            return f"\nLast {max_characters_per_stream} characters " \
                f"(from {len(self.stdout)} characters all-in-all) " \
                f"(starting at next line):\n{trimmed_stdout}"
        elif len(self.stdout) == 0:
            return ""
        else:
            return f"\nStdout (starting at next line):\n{self.stdout}"

    def _stderr_in_message(self, max_characters_per_stream: int):
        if len(self.stderr) > max_characters_per_stream:
            trimmed_stderr = self.stderr[len(self.stderr) - max_characters_per_stream:]
            return f"\nLast {max_characters_per_stream} characters " \
                f"(from {len(self.stderr)} characters all-in-all) " \
                f"(starting at next line):\n{trimmed_stderr}"
        elif len(self.stderr) == 0:
            return ""
        else:
            return f"\nStderr (starting at next line):\n{self.stderr}"
