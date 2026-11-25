"""Error taxonomy for Chess Observatory.

Every user-visible failure is one of these types. Each type carries a stable
machine-readable ``code`` and an optional human fix hint, so the CLI, the UI and
reports can present the same failure consistently (plan §13.4).

Rules:

* Never raise a bare ``ValueError`` from a public boundary; wrap it.
* Never swallow an error silently: either handle it or let it propagate.
* Hints are actionable ("run this", "check that"), not restatements of the
  message.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar


class ChessObservatoryError(Exception):
    """Base class for every error raised by this project."""

    code: ClassVar[str] = "app.error"
    default_hint: ClassVar[str | None] = None

    def __init__(
        self,
        message: str,
        *,
        hint: str | None = None,
        context: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint if hint is not None else self.default_hint
        self.context: dict[str, object] = dict(context or {})

    def __str__(self) -> str:
        if self.hint:
            return f"{self.message}\nHint: {self.hint}"
        return self.message

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
            "context": dict(self.context),
        }


# --------------------------------------------------------------------------- #
# Core: rules, positions, notation
# --------------------------------------------------------------------------- #
class CoreError(ChessObservatoryError):
    """Failure inside the position/rules core."""

    code = "core.error"


class IllegalMoveError(CoreError):
    code = "core.illegal_move"
    default_hint = "Check the move against the legal moves in the current position."


class InvalidFenError(CoreError):
    code = "core.invalid_fen"
    default_hint = "Check the six FEN fields: placement, side, castling, en passant, clocks."


class InvalidSanError(CoreError):
    code = "core.invalid_san"
    default_hint = "Check the SAN move, including capture, disambiguation and promotion markers."


class InvalidPgnError(CoreError):
    code = "core.invalid_pgn"
    default_hint = "Check the PGN headers and that moves are legal from the start position."


class InvalidPositionError(CoreError):
    code = "core.invalid_position"
    default_hint = "A position needs exactly one king per side and no pawns on rank 1 or 8."


# --------------------------------------------------------------------------- #
# Analysis
# --------------------------------------------------------------------------- #
class AnalysisError(ChessObservatoryError):
    code = "analysis.error"


class AnalyzerFailure(AnalysisError):
    code = "analysis.analyzer_failure"
    default_hint = "One analyzer failed; the rest of the analysis is still valid."


class BudgetExceededError(AnalysisError):
    code = "analysis.budget_exceeded"
    default_hint = "Raise the effort profile or reduce the requested scope."


class CanceledError(AnalysisError):
    code = "analysis.canceled"
    default_hint = None


# --------------------------------------------------------------------------- #
# Engines (own engine and UCI federation)
# --------------------------------------------------------------------------- #
class EngineError(ChessObservatoryError):
    code = "engine.error"


class EngineNotFoundError(EngineError):
    code = "engine.not_found"
    default_hint = "Install the engine or set its path with 'chess-obs engines add'."


class EngineTimeoutError(EngineError):
    code = "engine.timeout"
    default_hint = "The engine did not answer in time; it may be busy or hung."


class EngineCrashError(EngineError):
    code = "engine.crash"
    default_hint = "The engine process exited unexpectedly. Check its output in the log."


class EngineProtocolError(EngineError):
    code = "engine.protocol"
    default_hint = "The engine sent a line that is not valid UCI."


# --------------------------------------------------------------------------- #
# Storage
# --------------------------------------------------------------------------- #
class StorageError(ChessObservatoryError):
    code = "storage.error"


class CorruptIndexError(StorageError):
    code = "storage.corrupt_index"
    default_hint = "Rebuild the index with 'chess-obs build-index --force'."


class MigrationError(StorageError):
    code = "storage.migration"
    default_hint = "Back up the store, then run 'chess-obs doctor --repair'."


# --------------------------------------------------------------------------- #
# Chess knowledge: books, tablebases, proofs
# --------------------------------------------------------------------------- #
class BookError(ChessObservatoryError):
    code = "book.error"
    default_hint = "Check the book format and that the file is readable."


class TablebaseError(ChessObservatoryError):
    code = "tablebase.error"
    default_hint = "Check that the tablebase directory contains the required files."


class ProofError(ChessObservatoryError):
    code = "proof.error"
    default_hint = "The proof does not verify; treat the claim as unproven."


# --------------------------------------------------------------------------- #
# Machine learning
# --------------------------------------------------------------------------- #
class MLError(ChessObservatoryError):
    code = "ml.error"


class ModelNotFoundError(MLError):
    code = "ml.model_not_found"
    default_hint = "Download the model with 'chess-obs models download <id>'."


class ModelIntegrityError(MLError):
    code = "ml.model_integrity"
    default_hint = "The artifact hash does not match its registry entry; delete and re-download."


class GateFailedError(MLError):
    code = "ml.gate_failed"
    default_hint = "The model failed a parity gate and will not be used for this profile."


class InferenceError(MLError):
    code = "ml.inference"
    default_hint = "Check the inference backend and device; the classical path still works."


class DeviceUnavailableError(MLError):
    code = "ml.device_unavailable"
    default_hint = "Choose another device with 'ml.device' or fall back to CPU."


# --------------------------------------------------------------------------- #
# Assistant
# --------------------------------------------------------------------------- #
class AssistantError(ChessObservatoryError):
    code = "assistant.error"


class AssistantDisabledError(AssistantError):
    code = "assistant.disabled"
    default_hint = "Enable a provider in Settings > Assistant; it is off by default."


class GroundingError(AssistantError):
    code = "assistant.grounding"
    default_hint = "The answer cited a fact that is not in the analysis bundle."


class ProviderTimeoutError(AssistantError):
    code = "assistant.provider_timeout"
    default_hint = "The provider did not answer in time; try again or use a local model."


# --------------------------------------------------------------------------- #
# Plugins
# --------------------------------------------------------------------------- #
class PluginError(ChessObservatoryError):
    code = "plugin.error"


class PluginManifestError(PluginError):
    code = "plugin.manifest"
    default_hint = "Check the plugin manifest against docs/plugins/manifest.md."


class PluginApiMismatchError(PluginError):
    code = "plugin.api_mismatch"
    default_hint = "The plugin targets a different API version; update one of them."


# --------------------------------------------------------------------------- #
# Application plumbing (config, serialization, CLI)
# --------------------------------------------------------------------------- #
class ConfigError(ChessObservatoryError):
    code = "config.error"
    default_hint = "Run 'chess-obs config show' to inspect the effective configuration."


class ConfigParseError(ConfigError):
    code = "config.parse"
    default_hint = "Configuration is TOML; check quoting and section names."


class ConfigMigrationError(ConfigError):
    code = "config.migration"
    default_hint = "Back up the config file; it may come from a newer version."


class ConfigWriteError(ConfigError):
    code = "config.write"
    default_hint = "Check that the configuration directory is writable."


class SerializationError(ChessObservatoryError):
    code = "serialization.error"
    default_hint = "The value does not match its declared type."


class CLIError(ChessObservatoryError):
    code = "cli.error"
    default_hint = "Run 'chess-obs --help' for usage."
