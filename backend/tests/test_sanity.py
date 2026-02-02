import pytest


@pytest.mark.asyncio
async def test_sanity_check():
    """Verify asyncio loop is working."""
    assert 1 + 1 == 2
