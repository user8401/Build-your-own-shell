from .token import Token, TokenType


class Scanner:
    def scan(self, source: str) -> list[Token]:
        self._initialize(source)

        while not self._is_at_end():
            self._scan_token()
            self._start = self._current
        self._add_token(TokenType.EOF)

        return self._tokens

    def _initialize(self, source: str) -> None:
        self._source = source
        self._start = 0
        self._current = 0
        self._tokens = []

    def _is_at_end(self) -> bool:
        return self._current >= len(self._source)

    def _peek(self) -> str:
        return "" if self._is_at_end() else self._source[self._current]

    def _advance(self) -> str:
        c = self._source[self._current]
        self._current += 1
        return c

    def _match(self, c: str) -> bool:
        if self._is_at_end() or self._peek() != c:
            return False
        self._current += 1
        return True

    def _add_token(self, type: TokenType) -> None:
        token = Token(type, self._extract_lexeme())
        self._tokens.append(token)

    def _extract_lexeme(self) -> str:
        return self._source[self._start:self._current]

    def _scan_token(self) -> None:
        match (c := self._advance()):
            case " ":
                pass
            case "|":
                self._add_token(TokenType.OR)
            case ">":
                self._add_token(TokenType.DGREAT if self._match(">") else TokenType.GREAT)
            case _:
                if c.isdigit():
                    self._number()
                else:
                    self._current -= 1
                    self._word()

    def _number(self) -> None:
        while not self._is_at_end() and self._peek().isdigit():
            self._advance()

        if self._peek() == ">":
            self._add_token(TokenType.IO_NUMBER)
        else:
            self._word()

    def _word(self) -> None:
        while not self._is_at_end() and self._peek() != " ":
            match self._advance():
                case "\'":
                    self._single_quote()
                case "\"":
                    self._double_quote()
                case "\\":
                    self._backslash()

        self._add_token(TokenType.WORD)

    def _single_quote(self) -> None:
        while not self._is_at_end() and self._peek() != "\'":
            self._advance()

        if not self._match("\'"):
            raise ValueError("missing single quote")

    def _double_quote(self) -> None:
        while not self._is_at_end() and self._peek() != "\"":
            if self._advance() == "\\":
                self._backslash()

        if not self._match("\""):
            raise ValueError("missing double quote")

    def _backslash(self) -> None:
        if self._is_at_end():
            raise ValueError("expected character after backslash")
        self._advance()
