from .command import BUILTINS, get_all_executables


class Autocompleter:
    def __init__(self) -> None:
        self._command_names = BUILTINS.union(get_all_executables())

    def complete(self, text: str, state: int) -> str | None:
        if state == 0:
            self._matches = [s for s in self._command_names if s.startswith(text)]

        if state >= len(self._matches):
            return None
        elif len(self._matches) == 1:
            return self._matches[0] + " "
        else:
            return self._matches[state]
