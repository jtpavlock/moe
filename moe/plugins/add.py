"""Adds music to the library."""

import argparse
import logging
import pathlib
from typing import List

import mediafile
from sqlalchemy.orm.session import Session

import moe
from moe.core.config import Config
from moe.core.library.session import DbDupTrackError, session_scope
from moe.core.library.track import Track

log = logging.getLogger(__name__)


class AddTrackError(Exception):
    """Error adding a track to the library."""


class AddAlbumError(Exception):
    """Error adding an album to the library."""


@moe.hookimpl
def addcommand(cmd_parsers: argparse._SubParsersAction):  # noqa: WPS437
    """Adds a new `add` command to moe."""
    add_parser = cmd_parsers.add_parser(
        "add", description="Adds music to the library.", help="add music to the library"
    )
    add_parser.add_argument(
        "paths", nargs="+", help="dir to add an album or file to add a track"
    )
    add_parser.set_defaults(func=parse_args)


def parse_args(config: Config, session: Session, args: argparse.Namespace):
    """Parses the given commandline arguments.

    Args:
        config: Configuration in use.
        session: Current session.
        args: Commandline arguments to parse.

    Raises:
        SystemExit: Path given does not exist.
    """
    paths = [pathlib.Path(arg_path) for arg_path in args.paths]

    error_count = 0
    for path in paths:
        if not path.exists():
            log.error(f"Path not found: {path}")
            error_count += 1

        try:
            _add_path(path)
        except (AddTrackError, AddAlbumError) as exc:
            log.error(exc)
            error_count += 1

    if error_count:
        raise SystemExit(1)


def _add_path(path: pathlib.Path):
    """Add music at path to the library.

    Args:
        path: Path to add. If `path` is a file, it is added as a single track,
            otherwise if `path` is a directory, it is added as an album.
    """
    if path.is_file():
        _add_track(path)
    elif path.is_dir():
        _add_album(path)


def _add_album(album_path: pathlib.Path):
    """Add an album to the library from a given directory."""
    log.info(f"Adding album to the library: {album_path}")

    album_tracks: List[Track] = []
    with session_scope() as add_session:
        for file_path in album_path.rglob("*"):
            try:
                album_tracks.append(
                    Track.from_tags(path=file_path, session=add_session)
                )
            except (TypeError, mediafile.UnreadableFileError) as exc:
                log.warning(f"Could not add track to album: {str(exc)}")

        # Check if all the tracks created share the same album.
        if len(set([track._album_obj for track in album_tracks])) != 1:  # noqa: WPS437
            add_session.rollback()
            raise AddAlbumError("Not all tracks share the same album attributes.")

        for track in album_tracks:
            try:
                add_session.add(track)
            except DbDupTrackError:
                log.warning(f"Track already exists in the library: {track}")


def _add_track(track_path: pathlib.Path) -> Track:
    """Add a track to the library.

    The Track's attributes are populated from the tags read at `track_path`.

    Args:
        track_path: Path of track to add.

    Returns:
        Track added.

    Raises:
        AddTrackError: Unable to add Track to the library.
    """
    log.info(f"Adding track to the library: {track_path}")

    try:
        with session_scope() as add_session:
            track = Track.from_tags(path=track_path, session=add_session)

            add_session.add(track)
    except (TypeError, mediafile.UnreadableFileError) as exc:
        raise AddTrackError(exc) from exc
    except DbDupTrackError as exc:
        raise AddTrackError(f"Track already exists in library: {track}") from exc

    return track
