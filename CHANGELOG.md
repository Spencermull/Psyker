# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-15

### Added

- CLI: added `--verbose` (`-v`) troubleshooting output to stderr.
- CLI: added `--version` for quick version output.
- CLI: added `load --dir <path>` for non-recursive bulk load of `.psyw`, `.psya`, `.psy` files.
- GUI: added output actions to copy and clear terminal output.
- GUI: added running-task cancel controls (`Stop` button and `Ctrl+C`) with clean REPL recovery.
- GUI: added light/dark theme toggle (dark default) with persisted preference.
- Startup update check: added optional one-shot async update check via `--check-updates`.
- CI: expanded release/testing pipeline support for VSIX/coverage reporting.
- Docs: added user-facing guide (`docs/README.md`) and linked it from `README.md`.

## [0.1.0]

### Added

- CLI: Psyker runtime and interactive command workflows.
- GUI: native desktop app with embedded terminal REPL.
- EXE: Windows executable build and distribution support.
- Installer: installer packaging for desktop delivery.
- LSP: language server features for Psyker files.
- Tests: 48 automated tests across core subsystems.
