"""Package-level smoke tests."""


def test_import_ouem() -> None:
    """The package skeleton can be imported."""
    import ouem

    assert ouem.__doc__
