"""Pytest fixtures shared across tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_vietnamese_text() -> str:
    return (
        "Điều 5. Chế độ nghỉ phép\n\n"
        "5.1. Nghỉ phép năm: Nhân viên có hợp đồng chính thức được nghỉ 12 ngày phép/năm. "
        "Sau mỗi 5 năm làm việc, được cộng thêm 1 ngày/năm.\n"
        "5.2. Nghỉ ốm: Được nghỉ tối đa 30 ngày/năm có hưởng 75% lương cơ bản."
    )


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
