"""PGN reading and writing (plan Phase 1, step 12).

The reader handles the parts of PGN that real archives use: tag pairs with
escaped values, brace and semicolon comments, NAGs (numeric and symbolic),
nested RAV variations, results, and clock/evaluation annotations. It is
streaming: :func:`iter_pgn` yields one :class:`PgnGame` at a time and never
needs the whole file in memory.

Moves are stored as packed integers resolved against the game's start position,
so the writer can regenerate canonical SAN and every consumer gets flags for
make/unmake. The tree is immutable; a variation is a tuple of nodes attached to
the node it replaces.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field, replace
from typing import Final, TextIO

from chess_observatory.core.fen import STARTING_FEN, parse_fen, to_fen
from chess_observatory.core.make import Board
from chess_observatory.core.moves import move_to_uci
from chess_observatory.core.pieces import Color
from chess_observatory.core.position import Position
from chess_observatory.core.san import parse_san, to_san
from chess_observatory.errors import InvalidPgnError

RESULTS: Final = frozenset({"1-0", "0-1", "1/2-1/2", "*"})
NAG_BY_SYMBOL: Final[dict[str, int]] = {
    "!": 1,
    "?": 2,
    "!!": 3,
    "??": 4,
    "!?": 5,
    "?!": 6,
}
_HEADER_RE = re.compile(r'^\s*\[([A-Za-z0-9_]+)\s+"((?:[^"\\]|\\.)*)"\]\s*$')
_MOVE_NUMBER_RE = re.compile(r"^\d+\.+")
_ANNOTATION_RE = re.compile(r"^(.*?)([!?]+)$")
_CLOCK_RE = re.compile(r"\[%clk\s+([^\]]+)\]")
_EVAL_RE = re.compile(r"\[%eval\s+([^\]]+)\]")


@dataclass(frozen=True, slots=True)
class PgnNode:
    """One move plus everything attached to it."""

    move: int
    san: str
    comment: str | None = None
    nags: tuple[int, ...] = ()
    clock: float | None = None
    eval_cp: int | None = None
    eval_mate: int | None = None
    variations: tuple[tuple[PgnNode, ...], ...] = ()

    def with_variation(self, variation: tuple[PgnNode, ...]) -> PgnNode:
        return replace(self, variations=(*self.variations, variation))


@dataclass(frozen=True, slots=True)
class PgnGame:
    """A parsed game: tag pairs, mainline and attached variations."""

    headers: dict[str, str] = field(default_factory=dict)
    moves: tuple[PgnNode, ...] = ()
    comment: str | None = None

    @property
    def result(self) -> str:
        return self.headers.get("Result", "*")

    @property
    def start_fen(self) -> str:
        return self.headers.get("FEN", STARTING_FEN)

    def header(self, name: str, default: str | None = None) -> str | None:
        return self.headers.get(name, default)

    def start_position(self) -> Position:
        try:
            return parse_fen(self.start_fen, strict=False)
        except Exception as exc:
            raise InvalidPgnError(
                "the FEN header is not a valid FEN",
                context={"fen": self.start_fen},
            ) from exc

    def final_position(self) -> Position:
        board = Board(self.start_position())
        for node in self.moves:
            board.make(node.move)
        return board.to_position()

    def mainline_moves(self) -> list[int]:
        return [node.move for node in self.moves]

    def mainline_uci(self) -> list[str]:
        return [move_to_uci(node.move) for node in self.moves]

    def to_pgn(self, *, line_width: int = 80) -> str:
        return emit_pgn(self, line_width=line_width)


def _unescape(value: str) -> str:
    result: list[str] = []
    escaped = False
    for char in value:
        if escaped:
            result.append(char)
            escaped = False
        elif char == "\\":
            escaped = True
        else:
            result.append(char)
    if escaped:
        result.append("\\")
    return "".join(result)


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _parse_headers(lines: list[str], source: str) -> tuple[dict[str, str], int]:
    headers: dict[str, str] = {}
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        match = _HEADER_RE.match(line)
        if match is None:
            break
        headers[match.group(1)] = _unescape(match.group(2))
        index += 1
    return headers, index


def _strip_percent_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.startswith("%"))


def _tokenize_movetext(text: str) -> list[tuple[str, object]]:
    tokens: list[tuple[str, object]] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        if char == "{":
            end = text.find("}", index + 1)
            if end < 0:
                raise InvalidPgnError(
                    "unterminated comment",
                    context={"text": text[index : index + 40]},
                )
            tokens.append(("comment", text[index + 1 : end]))
            index = end + 1
            continue
        if char == ";":
            end = text.find("\n", index + 1)
            index = length if end < 0 else end + 1
            continue
        if char == "(":
            tokens.append(("(", None))
            index += 1
            continue
        if char == ")":
            tokens.append((")", None))
            index += 1
            continue
        if char == "$":
            end = index + 1
            while end < length and text[end].isdigit():
                end += 1
            if end == index + 1:
                raise InvalidPgnError("NAG marker without a number", context={"text": "$"})
            tokens.append(("nag", int(text[index + 1 : end])))
            index = end
            continue
        if char == "[":
            end = text.find("]", index + 1)
            if end < 0:
                raise InvalidPgnError(
                    "unterminated annotation",
                    context={"text": text[index : index + 40]},
                )
            tokens.append(("comment", text[index : end + 1]))
            index = end + 1
            continue

        end = index
        while end < length and not text[end].isspace() and text[end] not in "{};()$[":
            end += 1
        word = text[index:end]
        index = end
        while True:
            match = _MOVE_NUMBER_RE.match(word)
            if match is None:
                break
            word = word[match.end() :]
        if not word:
            continue
        if word in {"e.p.", "ep", "e.p"}:
            continue
        if word in {"--", "Z0"}:
            raise InvalidPgnError(
                "null moves are not supported in PGN import",
                context={"move": word},
            )
        if word in RESULTS:
            tokens.append(("result", word))
            continue
        annotation = _ANNOTATION_RE.match(word)
        if annotation is not None and annotation.group(1):
            word = annotation.group(1)
            symbol = annotation.group(2)
            tokens.append(("move", word))
            nag = NAG_BY_SYMBOL.get(symbol)
            if nag is not None:
                tokens.append(("nag", nag))
            continue
        tokens.append(("move", word))
    return tokens


def _parse_clock(value: str) -> float:
    parts = value.strip().split(":")
    if not 2 <= len(parts) <= 3:
        raise InvalidPgnError(f"invalid clock annotation {value!r}")
    try:
        numbers = [float(part) for part in parts]
    except ValueError as exc:
        raise InvalidPgnError(f"invalid clock annotation {value!r}") from exc
    seconds = 0.0
    for number in numbers:
        seconds = seconds * 60 + number
    return seconds


def _parse_eval(value: str) -> tuple[int | None, int | None]:
    cleaned = value.strip()
    mate = re.fullmatch(r"([+-]?)#(\d+)", cleaned)
    if mate is not None:
        sign = -1 if mate.group(1) == "-" else 1
        return None, sign * int(mate.group(2))
    try:
        return round(float(cleaned) * 100), None
    except ValueError as exc:
        raise InvalidPgnError(f"invalid evaluation annotation {value!r}") from exc


def _extract_annotations(
    comment: str,
) -> tuple[str | None, float | None, int | None, int | None]:
    clock: float | None = None
    eval_cp: int | None = None
    eval_mate: int | None = None
    cleaned = comment
    for match in _CLOCK_RE.finditer(comment):
        clock = _parse_clock(match.group(1))
    cleaned = _CLOCK_RE.sub("", cleaned)
    for match in _EVAL_RE.finditer(comment):
        eval_cp, eval_mate = _parse_eval(match.group(1))
    cleaned = _EVAL_RE.sub("", cleaned)
    cleaned = " ".join(cleaned.split())
    return cleaned or None, clock, eval_cp, eval_mate


def _copy_board(board: Board) -> Board:
    return Board.from_position(board.to_position())


def _attach(
    nodes: list[PgnNode],
    *,
    comment: str | None = None,
    nag: int | None = None,
) -> None:
    if not nodes:
        return
    node = nodes[-1]
    if comment is not None:
        cleaned, clock, eval_cp, eval_mate = _extract_annotations(comment)
        nodes[-1] = replace(
            node,
            comment=cleaned if cleaned is not None else node.comment,
            clock=clock if clock is not None else node.clock,
            eval_cp=eval_cp if eval_cp is not None else node.eval_cp,
            eval_mate=eval_mate if eval_mate is not None else node.eval_mate,
        )
    if nag is not None:
        nodes[-1] = replace(nodes[-1], nags=(*nodes[-1].nags, nag))


def _parse_line(
    tokens: list[tuple[str, object]],
    index: int,
    board: Board,
    source: str,
    *,
    nested: bool,
) -> tuple[list[PgnNode], int]:
    nodes: list[PgnNode] = []
    before_last: Board | None = None
    while index < len(tokens):
        kind, value = tokens[index]
        if kind == ")":
            if not nested:
                raise InvalidPgnError("unbalanced ')' in movetext", context={"source": source})
            return nodes, index + 1
        if kind == "(":
            if not nodes or before_last is None:
                raise InvalidPgnError(
                    "variation without a preceding move",
                    context={"source": source},
                )
            variation, index = _parse_line(
                tokens, index + 1, _copy_board(before_last), source, nested=True
            )
            nodes[-1] = nodes[-1].with_variation(tuple(variation))
            continue
        if kind == "result":
            return nodes, len(tokens)
        if kind == "comment":
            _attach(nodes, comment=str(value))
            index += 1
            continue
        if kind == "nag":
            assert isinstance(value, int)
            _attach(nodes, nag=value)
            index += 1
            continue
        if kind != "move":  # pragma: no cover - defensive; the tokenizer is closed
            raise InvalidPgnError(f"unexpected token {kind!r}", context={"source": source})
        san_text = str(value)
        try:
            move = parse_san(board, san_text)
        except Exception as exc:
            raise InvalidPgnError(
                f"cannot play {san_text!r} in {to_fen(board.to_position())}",
                context={"source": source, "move": san_text},
            ) from exc
        node = PgnNode(move=move, san=to_san(board, move))
        before_last = _copy_board(board)
        board.make(move)
        nodes.append(node)
        index += 1
    if nested:
        raise InvalidPgnError("unterminated variation", context={"source": source})
    return nodes, index


def parse_pgn(text: str, *, source: str = "<string>") -> PgnGame:
    """Parse the first game in ``text``."""
    games = parse_pgn_games(text, source=source)
    if not games:
        raise InvalidPgnError("no game found in PGN", context={"source": source})
    return games[0]


def parse_pgn_games(text: str, *, source: str = "<string>") -> list[PgnGame]:
    return [_parse_block(block, source) for block in _split_blocks(_strip_percent_lines(text))]


def _split_blocks(text: str) -> list[list[str]]:
    blocks: list[list[str]] = []
    current: list[str] = []
    movetext_started = False
    brace_depth = 0
    for line in text.splitlines():
        stripped = line.strip()
        in_comment = brace_depth > 0
        brace_depth += line.count("{") - line.count("}")
        if stripped.startswith("[") and not in_comment:
            if movetext_started and current:
                blocks.append(current)
                current = []
            movetext_started = False
            current.append(line)
            continue
        if stripped:
            current.append(line)
            if not stripped.startswith("["):
                movetext_started = True
        elif current and not movetext_started:
            current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _parse_block(lines: list[str], source: str) -> PgnGame:
    headers, index = _parse_headers(lines, source)
    movetext = "\n".join(lines[index:])
    tokens = _tokenize_movetext(movetext)
    start = _start_board(headers, source)
    leading: list[str] = []
    while tokens and tokens[0][0] == "comment":
        leading.append(str(tokens.pop(0)[1]))
    nodes, _ = _parse_line(tokens, 0, start, source, nested=False)
    for kind, value in tokens:
        if kind == "result":
            headers.setdefault("Result", str(value))
            break
    game_comment = " ".join(part for part in leading if part.strip()) or None
    return PgnGame(headers=headers, moves=tuple(nodes), comment=game_comment)


def _start_board(headers: dict[str, str], source: str) -> Board:
    fen = headers.get("FEN", STARTING_FEN)
    try:
        return Board(parse_fen(fen, strict=False))
    except Exception as exc:
        raise InvalidPgnError(
            "the FEN tag is not a valid FEN",
            context={"source": source, "fen": fen},
        ) from exc


def _decode(raw: bytes, encoding: str) -> str:
    for candidate in (encoding, "utf-8-sig", "utf-8", "latin-1"):
        try:
            return raw.decode(candidate)
        except UnicodeDecodeError:
            continue
    raise AssertionError("latin-1 decodes every byte sequence")  # pragma: no cover


def iter_pgn(
    stream: TextIO | Iterable[str] | Iterable[bytes],
    *,
    encoding: str = "utf-8",
) -> Iterator[PgnGame]:
    """Yield games from a text or byte stream without loading the whole file."""
    lines: list[str] = []
    movetext_started = False
    brace_depth = 0

    def flush() -> Iterator[PgnGame]:
        nonlocal lines, movetext_started
        if lines:
            text = _strip_percent_lines("\n".join(lines))
            if text.strip():
                yield _parse_block(text.splitlines(), "<stream>")
        lines = []
        movetext_started = False

    for item in stream:
        line = _decode(item, encoding) if isinstance(item, bytes) else item
        line = line.rstrip("\r\n")
        in_comment = brace_depth > 0
        brace_depth += line.count("{") - line.count("}")
        if line.strip().startswith("[") and not in_comment and movetext_started:
            yield from flush()
        lines.append(line)
        if line.strip() and not line.strip().startswith("["):
            movetext_started = True
    yield from flush()


def read_pgn(
    stream: TextIO | str | bytes,
    *,
    encoding: str = "utf-8",
    source: str = "<stream>",
) -> list[PgnGame]:
    """Read every game from a path-like text, a string or a byte string."""
    if isinstance(stream, str):
        return parse_pgn_games(stream, source=source)
    if isinstance(stream, bytes):
        return parse_pgn_games(_decode(stream, encoding), source=source)
    return list(iter_pgn(stream, encoding=encoding))


def _format_clock(seconds: float) -> str:
    total = round(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}"


def _comment_text(node: PgnNode) -> str | None:
    pieces: list[str] = []
    if node.comment:
        pieces.append(node.comment)
    if node.clock is not None:
        pieces.append(f"[%clk {_format_clock(node.clock)}]")
    if node.eval_mate is not None:
        sign = "-" if node.eval_mate < 0 else ""
        pieces.append(f"[%eval {sign}#{abs(node.eval_mate)}]")
    elif node.eval_cp is not None:
        pieces.append(f"[%eval {node.eval_cp / 100:+.2f}]")
    if not pieces:
        return None
    return " ".join(pieces)


def _emit_nodes(
    nodes: tuple[PgnNode, ...],
    board: Board,
    words: list[str],
    *,
    fullmove: int,
    side: Color,
) -> None:
    for position, node in enumerate(nodes):
        if side is Color.WHITE:
            words.append(f"{fullmove}.")
        elif position == 0 or words[-1] == ")":
            words.append(f"{fullmove}...")
        words.append(to_san(board, node.move))
        for nag in node.nags:
            words.append(f"${nag}")
        comment = _comment_text(node)
        if comment:
            words.append("{" + comment + "}")
        before = _copy_board(board)
        board.make(node.move)
        if side is Color.BLACK:
            fullmove += 1
        for variation in node.variations:
            words.append("(")
            _emit_nodes(
                variation,
                _copy_board(before),
                words,
                fullmove=fullmove - (1 if side is Color.BLACK else 0),
                side=side,
            )
            words.append(")")
        side = side.opposite


def _wrap(words: list[str], width: int) -> str:
    lines: list[str] = []
    current: list[str] = []
    length = 0
    for word in words:
        extra = len(word) + (1 if current else 0)
        if current and length + extra > width:
            lines.append(" ".join(current))
            current = [word]
            length = len(word)
        else:
            current.append(word)
            length += extra
    if current:
        lines.append(" ".join(current))
    return "\n".join(line.replace("( ", "(").replace(" )", ")") for line in lines)


def emit_pgn(game: PgnGame, *, line_width: int = 80) -> str:
    """Serialise a game to canonical PGN text."""
    headers = dict(game.headers)
    if "FEN" in headers:
        headers.setdefault("SetUp", "1")
    if "Result" not in headers:
        headers["Result"] = "*"
    header_lines = [f'[{name} "{_escape(value)}"]' for name, value in headers.items()]
    words: list[str] = []
    if game.comment:
        words.append("{" + game.comment + "}")
    board = Board(game.start_position())
    side = board.side
    fullmove = board.fullmove
    _emit_nodes(game.moves, board, words, fullmove=fullmove, side=side)
    words.append(game.result)
    movetext = _wrap(words, line_width)
    return "\n".join(header_lines) + "\n\n" + movetext + "\n"


def write_pgn(games: Iterable[PgnGame], stream: TextIO, *, line_width: int = 80) -> None:
    """Write games separated by a blank line."""
    for index, game in enumerate(games):
        if index:
            stream.write("\n")
        stream.write(emit_pgn(game, line_width=line_width))
