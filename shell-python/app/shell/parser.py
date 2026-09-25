import glob
import shlex

from .command import Command
from .token import Token, TokenType


class Parser:
    def parse(self, tokens: list[Token]) -> list[Command]:
        self._initialize(tokens)
        commands = []
        while not self._is_at_end():
            commands.append(self._command())
            if not self._match(TokenType.OR):
                break
        return commands

    def _initialize(self, tokens: list[Token]) -> None:
        self._tokens = tokens
        self._current = 0

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _check(self, type: TokenType) -> bool:
        return self._peek().type == type

    def _is_at_end(self) -> bool:
        return self._check(TokenType.EOF)

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _advance(self) -> Token:
        if not self._is_at_end():
            self._current += 1
        return self._previous()

    def _match(self, *types: TokenType) -> bool:
        if not any(self._check(t) for t in types):
            return False
        self._advance()
        return True

    def _command(self) -> Command:
        arguments, redirs = [], {}

        while not self._is_at_end() and not self._check(TokenType.OR):
            if self._match(TokenType.WORD):
                arguments.extend(shlex.split(self._previous().lexeme))
                continue

            fd = 1
            if self._match(TokenType.IO_NUMBER):
                fd = int(self._previous().lexeme)

            assert self._match(TokenType.DGREAT, TokenType.GREAT)
            mode = "a" if self._previous().type == TokenType.DGREAT else "w"

            assert self._match(TokenType.WORD)
            path = self._previous().lexeme

            redirs[fd] = path, mode

        return Command(arguments, redir_stdout=redirs.get(1), redir_stderr=redirs.get(2))
