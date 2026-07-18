#!/usr/bin/env python3
"""Figma configuration loader using environment variables."""

from __future__ import annotations

import os


def get_figma_token() -> str:
    return os.getenv("FIGMA_TOKEN", "").strip()


def get_figma_file_key() -> str:
    return os.getenv("FIGMA_FILE_KEY", "").strip()


def has_figma_config() -> bool:
    return bool(get_figma_token() and get_figma_file_key())
