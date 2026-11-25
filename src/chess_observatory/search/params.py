"""Own engine parameter registry (plan Phase 2, step 1, engine-system §7).

Every engine knob is declared once, with metadata: type, default, range, step,
tier, determinism class, whether a restart is required and a documentation
sentence. CLI flags, UCI ``setoption`` names, settings controls, the generated
``docs/search.md`` page and the configuration round-trip all derive from this
registry instead of growing a second copy of the truth.

The registry starts with the engine parameters that Phase 2 declares in §7.3
and §7.6; later phases add their own knobs through the same interface.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import StrEnum


class ParamType(StrEnum):
    """The machine-readable value type of a registry parameter."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"


class ParamTier(StrEnum):
    """How dangerous a knob is; groups settings UI controls."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"
    EXPERIMENTAL = "experimental"


class Determinism(StrEnum):
    """When a search configuration guarantees identical results."""

    ALWAYS = "always"
    TIME_DEPENDENT = "time_dependent"
    HARDWARE_DEPENDENT = "hardware_dependent"


@dataclass(frozen=True, slots=True)
class Param:
    """One engine knob with its metadata."""

    name: str
    type: ParamType = ParamType.INT
    default: float = 1.0
    min: float | None = None
    max: float | None = None
    step: float = 1.0
    tier: ParamTier = ParamTier.INTERMEDIATE
    determinism: Determinism = Determinism.ALWAYS
    restart_required: bool = False
    doc: str = ""

    def validate(self, value: float) -> float:
        """Return the value when it is within range, else raise ``ValueError``."""
        if self.min is not None and value < self.min:
            raise ValueError(f"{self.name}: {value} is below the minimum {self.min}")
        if self.max is not None and value > self.max:
            raise ValueError(f"{self.name}: {value} is above the maximum {self.max}")
        return value

    def clamp(self, value: float) -> float:
        """Clamp ``value`` into the parameter range."""
        clamped = value
        if self.min is not None and clamped < self.min:
            clamped = self.min
        if self.max is not None and clamped > self.max:
            clamped = self.max
        return clamped


class ParamRegistry:
    """The single registry of engine parameters."""

    __slots__ = ("_params",)

    def __init__(self, params: dict[str, Param] | None = None) -> None:
        self._params: dict[str, Param] = (
            dict(params) if params is not None else dict(DEFAULT_PARAMS)
        )

    def __contains__(self, name: object) -> bool:
        return isinstance(name, str) and name in self._params

    def __getitem__(self, name: str) -> Param:
        return self._params[name]

    def __iter__(self) -> Iterator[str]:
        return iter(sorted(self._params))

    def __len__(self) -> int:
        return len(self._params)

    def get(self, name: str, default: Param | None = None) -> Param | None:
        return self._params.get(name, default)

    def get_param(self, name: str) -> Param:
        param = self._params.get(name)
        if param is None:
            raise KeyError(f"unknown engine parameter {name!r}")
        return param

    def sorted_params(self) -> list[Param]:
        """Registered parameters in stable (sorted) order."""
        return [self._params[name] for name in sorted(self._params)]

    def validate(self, name: str, value: float) -> float:
        """Validate and return a value for ``name``."""
        return self.get_param(name).validate(value)

    def to_dict(self) -> dict[str, float]:
        """Effective parameter values keyed by name (the registry round-trip payload)."""
        return {name: param.default for name, param in sorted(self._params.items())}

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> ParamRegistry:
        """Rebuild a registry from :meth:`to_dict` output."""
        return cls({name: Param(name, default=value) for name, value in values.items()})

    def render_markdown(self) -> str:
        """Render the generated ``docs/search.md`` body from the registry."""

        def fmt(value: float | None) -> str:
            if value is None:
                return "-"
            number = float(value)
            return str(int(number)) if number.is_integer() else str(number)

        bools = {param.name for param in self.sorted_params() if param.type is ParamType.BOOL}
        lines = [
            "# Search",
            "",
            "> **Status:** generated from the parameter registry; regenerate rather than edit.",
            "",
            'The promise is "how long to examine, and how" — so search is a',
            "first-class, inspectable subsystem, not a settings dialog",
            "([ADR-0002](adr/0002-hybrid-engine-federation.md)).",
            "",
            "## Parameters",
            "",
            "| Name | Type | Default | Min | Max | Step | Tier | Determinism | Restart required | Documentation |",
            "|------|------|--------|-----|-----|------|------|-------------|----------------|----------------|",
        ]
        for param in self.sorted_params():
            default = "true" if param.name in bools else fmt(param.default)
            lines.append(
                f"| `{param.name}` | {param.type.value} | {default} | {fmt(param.min)} | "
                f"{fmt(param.max)} | {fmt(param.step)} | {param.tier.value} | {param.determinism.value} | "
                f"{param.restart_required} | {param.doc} |"
            )
        lines += [
            "",
            "## Reproducibility",
            "",
            "- `always` — depth and node limit.",
            "- `time_dependent` — movetime.",
            "- `hardware_dependent` — threads, SIMD paths, GPU inference.",
            "",
            "The UI shows a **Reproducible** badge only when the active combination is",
            "deterministic, and reproducibility records state which parameters prevent",
            "replay of a search.",
            "",
            "## Related",
            "",
            "- [Position API](position-api.md) — the rules core this engine searches.",
            "- [ADR-0002](adr/0002-hybrid-engine-federation.md) — the hybrid engine contract.",
            "",
        ]
        return "\n".join(lines)


DEFAULT_PARAMS: dict[str, Param] = {
    "search.max_depth": Param(
        "search.max_depth",
        default=32.0,
        min=1.0,
        max=100.0,
        step=1.0,
        tier=ParamTier.INTERMEDIATE,
        doc="Maximum search depth before stopping; 0 means unlimited depth.",
    ),
    "search.multipv": Param(
        "search.multipv",
        default=1.0,
        min=1.0,
        max=32.0,
        step=1.0,
        tier=ParamTier.INTERMEDIATE,
        doc="Number of principal variations reported.",
    ),
    "search.hash_mb": Param(
        "search.hash_mb",
        default=256.0,
        min=16.0,
        max=1024.0,
        step=16.0,
        tier=ParamTier.BASIC,
        restart_required=True,
        doc="Transposition-table size in megabytes.",
    ),
    "search.threads": Param(
        "search.threads",
        default=1.0,
        min=1.0,
        max=16.0,
        step=1.0,
        tier=ParamTier.BASIC,
        determinism=Determinism.HARDWARE_DEPENDENT,
        restart_required=True,
        doc="Worker threads; 1 keeps the default node-deterministic search.",
    ),
    "search.delta_prune": Param(
        "search.delta_prune",
        type=ParamType.BOOL,
        default=True,
        tier=ParamTier.BASIC,
        doc="Enable quiescence delta pruning (Basic tier, deterministic).",
    ),
}
