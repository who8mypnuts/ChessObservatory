# ADR-0006: Linux-only target

## Status

Accepted, 2026-11-23. Summary accepted with the implementation plan; detail is
expanded in the phase that implements it.

## Context

This decision is load-bearing for the plan and is recorded now so later phases do
not quietly re-litigate it.

## Decision

Linux (X11 and Wayland) is the only supported platform for v1.0. Packaging is AppImage-first with an optional Flatpak manifest. Windows and macOS are out of scope, which keeps global shortcuts, fractional scaling and file dialogs to one well-tested path.

## Consequences

The phase that implements this decision expands the operational detail. Until
then this record is the binding summary.

*Slug: `linux-only`.*
