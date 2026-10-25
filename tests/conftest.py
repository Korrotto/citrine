from __future__ import annotations

import pytest
from assembler.source.models import AssemblerContext

from tests.utils import build_context, make_architecture, make_pseudo_architecture


@pytest.fixture
def architecture() -> dict[str, object]:
    return make_architecture()


@pytest.fixture
def pseudo_architecture() -> dict[str, object]:
    return make_pseudo_architecture()


@pytest.fixture
def context() -> AssemblerContext:
    return build_context()


@pytest.fixture
def pseudo_context() -> AssemblerContext:
    return build_context(make_pseudo_architecture())
