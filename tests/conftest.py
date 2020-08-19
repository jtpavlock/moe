"""Shared pytest configuration."""

from typing import Callable, Iterator, Tuple
from unittest.mock import MagicMock, Mock

import pluggy
import pytest
import sqlalchemy

from moe import cli
from moe.core import library
from moe.core.config import Config


@pytest.fixture
def tmp_session() -> Iterator[sqlalchemy.orm.session.Session]:
    """Creates temporary Session instance for database interaction.

    The database is a temporary sqlite instance created in memory.

    Yields:
        session: temp Session instance
    """
    engine = sqlalchemy.create_engine("sqlite:///:memory:")
    Config(config_dir=MagicMock(), engine=engine)

    with library.session_scope() as session:
        yield session


@pytest.fixture
def tmp_live(tmp_path) -> Tuple[Config, pluggy.PluginManager]:
    """Instantiates an actual configuration and pluginmanager under a tmp path.

    Returns:
        A tuple containing the config and pluginmanager
    """
    config = Config(config_dir=tmp_path)
    pm = cli._get_plugin_manager(config)

    return config, pm


@pytest.fixture
def mock_track_factory() -> Callable[[], library.Track]:
    """Factory for mock Tracks.

    In particular, the path is mocked so the Track doesn't need to exist.

    Returns:
        Unique Track object with each call.
    """

    def _mock_track():  # noqa: WPS430
        return library.Track(path=Mock())

    return _mock_track


@pytest.fixture
def mock_track(mock_track_factory) -> library.Track:
    """Creates a single mock Track object.

    Uses `mock_track_factory`.

    Returns:
        Track object.
    """
    return mock_track_factory()