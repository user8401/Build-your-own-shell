import io
import os
import readline
import shutil
import subprocess
import sys
from contextlib import ExitStack, nullcontext, redirect_stderr, redirect_stdout
from dataclasses import dataclass


BUILTINS = set(["cd", "echo", "exit", "history", "pwd", "type"])


def get_all_executables() -> set[str]:
    executables = set()

    path_env = os.getenv("PATH")
    if path_env is None:
        return executables

    for directory in path_env.split(":"):
        try:
            names = os.listdir(directory)
        except FileNotFoundError:
            continue

        for name in names:
            path = os.path.join(directory, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                executables.add(name)

    return executables


@dataclass(frozen=True)
class Command:
    arguments: list[str]
    redir_stdout: tuple[str, str] | None
    redir_stderr: tuple[str, str] | None


def _execute_cd(arguments: list[str]) -> None:
    destination = os.path.expanduser(arguments[1])
    try:
        os.chdir(destination)
    except FileNotFoundError:
        sys.stderr.write(f"cd: {destination}: No such file or directory\n")


def _execute_echo(arguments: list[str]) -> None:
    sys.stdout.write(" ".join(arguments[1:]) + "\n")


def _execute_exit(arguments: list[str]) -> None:
    sys.exit(int(arguments[1]) if len(arguments) > 1 else 0)


_last_append_nitems = 0


def _execute_history(arguments: list[str]) -> None:
    nitems = readline.get_current_history_length()

    if len(arguments) == 3:
        histfile = arguments[2]
        match arguments[1]:
            case "-r":
                readline.read_history_file(histfile)
            case "-w":
                readline.write_history_file(histfile)
            case "-a":
                global _last_append_nitems
                readline.append_history_file(nitems - _last_append_nitems, histfile)
                _last_append_nitems = nitems
        return

    n = int(arguments[1]) if len(arguments) > 1 else nitems
    for i in range(nitems + 1 - n, nitems + 1):
        line = readline.get_history_item(i)
        sys.stdout.write(f"{i:>5}  {line}\n")


def _execute_pwd(arguments: list[str]) -> None:
    sys.stdout.write(os.getcwd() + "\n")


def _execute_type(arguments: list[str]) -> None:
    for command_name in arguments[1:]:
        if command_name in BUILTINS:
            sys.stdout.write(f"{command_name} is a shell builtin\n")
        elif (path := shutil.which(command_name)) is not None:
            sys.stdout.write(f"{command_name} is {path}\n")
        else:
            sys.stdout.write(f"{command_name}: not found\n")


def _execute(arguments: list[str]) -> None:
    match (command_name := arguments[0]):
        case "cd":
            _execute_cd(arguments)
        case "echo":
            _execute_echo(arguments)
        case "exit":
            _execute_exit(arguments)
        case "history":
            _execute_history(arguments)
        case "pwd":
            _execute_pwd(arguments)
        case "type":
            _execute_type(arguments)
        case _:
            try:
                subprocess.run(arguments, stdout=sys.stdout, stderr=sys.stderr)
            except FileNotFoundError:
                sys.stderr.write(f"{command_name}: command not found\n")


def execute_command(command: Command) -> None:
    with ExitStack() as stack:
        if command.redir_stdout is not None:
            f = open(*command.redir_stdout)
            stack.enter_context(f)
            stack.enter_context(redirect_stdout(f))

        if command.redir_stderr is not None:
            f = open(*command.redir_stderr)
            stack.enter_context(f)
            stack.enter_context(redirect_stderr(f))

        _execute(command.arguments)


def _stderr_context(command: Command):
    if command.redir_stderr is not None:
        return open(*command.redir_stderr)
    return nullcontext(sys.stderr)


def execute_commands(commands: list[Command]) -> None:
    if not commands:
        return
    elif len(commands) == 1:
        execute_command(commands[0])
        return

    # NOTE: the original implementation used os.fork() + os.pipe() to wire
    # pipeline stages together at the OS level. os.fork() does not exist on
    # Windows, so this version runs each stage sequentially in-process
    # instead, capturing each stage's full output in memory and feeding it
    # as the next stage's stdin. This trades true concurrent streaming for
    # portability -- fine for typical shell usage, but a stage that produces
    # a very large amount of output before the next stage can consume it
    # will use more memory than the original streaming version would.
    piped_input: bytes = b""

    for i, command in enumerate(commands):
        is_first = i == 0
        is_last = i == len(commands) - 1
        command_name = command.arguments[0]

        with _stderr_context(command) as stderr_file:
            if command_name in BUILTINS:
                out_buffer = io.StringIO()
                saved_cwd = os.getcwd()
                try:
                    with redirect_stdout(out_buffer), redirect_stderr(stderr_file):
                        _execute(command.arguments)
                except SystemExit:
                    # In a real shell, `exit` inside a pipeline only ends
                    # that stage's subshell, not the whole shell process.
                    pass
                finally:
                    # Every pipeline stage runs in its own subshell in a
                    # real shell, so a `cd` here must not persist afterwards.
                    os.chdir(saved_cwd)
                stage_output = out_buffer.getvalue().encode()
            else:
                run_kwargs = dict(stdout=subprocess.PIPE, stderr=stderr_file)
                if not is_first:
                    run_kwargs["input"] = piped_input
                try:
                    completed = subprocess.run(command.arguments, **run_kwargs)
                    stage_output = completed.stdout
                except FileNotFoundError:
                    sys.stderr.write(f"{command_name}: command not found\n")
                    stage_output = b""

        if is_last:
            if command.redir_stdout is not None:
                with open(*command.redir_stdout) as f:
                    f.write(stage_output.decode(errors="replace"))
            else:
                sys.stdout.buffer.write(stage_output)
                sys.stdout.flush()
        else:
            piped_input = stage_output