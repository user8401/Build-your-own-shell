import atexit
import os
import readline
from typing import NoReturn

from .autocomplete import Autocompleter
from .command import execute_commands
from .scanner import Scanner
from .parser import Parser


class Shell:
    def __init__(self, prompt: str = "$ ") -> None:
        self._prompt = prompt
        self._autocompleter = Autocompleter()
        self._scanner = Scanner()
        self._parser = Parser()

    def start(self) -> NoReturn:
        readline.parse_and_bind("tab: complete")
        readline.set_completer(self._autocompleter.complete)

        if hasattr(readline, "set_auto_history"):
            readline.set_auto_history(True)
        readline.parse_and_bind("\"\\C-p\": previous-history")
        readline.parse_and_bind("\"\\C-n\": next-history")

        if (histfile := os.environ.get("HISTFILE")) is not None:
            try:
                readline.read_history_file(histfile)
            except OSError:
                pass
            atexit.register(readline.write_history_file, histfile)

        while True:
            line = input(self._prompt)
            tokens = self._scanner.scan(line)
            commands = self._parser.parse(tokens)
            execute_commands(commands)
