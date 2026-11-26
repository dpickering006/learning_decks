"""Subscribe one AnkiWeb account to this repository's published decks.

Uses Anki's own backend in a separate collection, never an open desktop profile.
Credentials and collection data live outside the Git checkout. Normal operation
only performs incremental syncs; it never chooses a full upload or overwrite.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time

import requests
from anki.collection import Collection
from anki.importing import ImportAnkiPackageOptions, ImportAnkiPackageRequest
from anki.sync_pb2 import SyncAuth

REPOSITORY = "dpickering006/learning_decks"
DEFAULT_STATE = Path.home() / ".local/share/learning-decks-sync"
MAX_DOWNLOAD = 128 * 1024 * 1024


class SetupRequired(RuntimeError):
    pass


def private_write(path: Path, content: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


@contextmanager
def locked(state: Path):
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    state.chmod(0o700)
    with (state / "lock").open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def save_auth(state: Path, auth: SyncAuth) -> None:
    private_write(state / "auth.bin", auth.SerializeToString())


def wait_for_media(collection: Collection, auth: SyncAuth) -> None:
    collection.sync_media(auth)
    deadline = time.monotonic() + 1200
    while collection.media_sync_status().active:
        if time.monotonic() > deadline:
            collection.abort_media_sync()
            raise RuntimeError("Media sync timed out; the next run will retry.")
        time.sleep(.25)


def incremental_sync(collection: Collection, auth: SyncAuth, state: Path) -> None:
    result = collection.sync_collection(auth, sync_media=False)
    if result.new_endpoint:
        auth.endpoint = result.new_endpoint
        save_auth(state, auth)
    if result.required != result.NO_CHANGES:
        raise SetupRequired("Anki requires a full-sync decision. No overwrite was performed; resolve it before resuming.")
    wait_for_media(collection, auth)


def initialize(state: Path, email: str, password: str, endpoint: str | None = None) -> None:
    """One-time bootstrap: download the existing account, never upload it."""
    if (state / "ready").exists():
        raise SetupRequired("Already configured. Use run or status; setup will not replace an existing collection.")
    collection = Collection(str(state / "collection.anki2"))
    try:
        if collection.card_count():
            raise SetupRequired("An unfinished setup contains cards. Preserve it and inspect it before retrying.")
        auth = collection.sync_login(email, password, endpoint)
        auth.io_timeout_secs = 60
        result = collection.sync_collection(auth, sync_media=False)
        if result.new_endpoint:
            auth.endpoint = result.new_endpoint
        if result.required not in (result.FULL_DOWNLOAD, result.FULL_SYNC):
            raise SetupRequired("First tap Sync on your iPhone to put your existing cards in this AnkiWeb account, then retry setup.")
        collection.close_for_full_sync()
        collection.full_upload_or_download(auth=auth, server_usn=result.server_media_usn, upload=False)
        collection.reopen(after_full_sync=True)
        if not collection.card_count():
            raise SetupRequired("This AnkiWeb account contains no cards. Sync your iPhone first; nothing was uploaded.")
        save_auth(state, auth)
        private_write(state / "account.txt", (email.strip().casefold() + "\n").encode())
        private_write(state / "ready", b"configured\n")
        # A media interruption can now be resumed by run without repeating setup.
        wait_for_media(collection, auth)
    finally:
        collection.close()


def read_json(url: str):
    response = requests.get(url, timeout=(15, 90), headers={"Accept": "application/vnd.github+json"})
    response.raise_for_status()
    return response.json()


def fetch_packages(release: dict, directory: Path) -> list[Path]:
    """Pin all downloads to one release and verify each package's checksum."""
    assets = {item["name"]: item["browser_download_url"] for item in release["assets"]}
    prefix = f"https://github.com/{REPOSITORY}/releases/download/"
    if not all(url.startswith(prefix) for url in assets.values()):
        raise ValueError("Unexpected release asset origin")
    catalogue = read_json(assets["catalog.json"])
    packages = []
    seen = set()
    for deck in catalogue:
        slug = deck["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError("Invalid or duplicate deck slug")
        seen.add(slug)
        if not re.fullmatch(r"[0-9a-f]{64}", deck["sha256"]):
            raise ValueError("Invalid package checksum")
        path = directory / f"{slug}.apkg"
        digest = hashlib.sha256()
        count = 0
        with requests.get(assets[path.name], stream=True, timeout=(15, 90)) as response:
            response.raise_for_status()
            with path.open("wb") as stream:
                for chunk in response.iter_content(1024 * 1024):
                    count += len(chunk)
                    if count > MAX_DOWNLOAD:
                        raise ValueError("Package exceeds download size limit")
                    digest.update(chunk)
                    stream.write(chunk)
        if digest.hexdigest() != deck["sha256"]:
            raise ValueError("Package checksum mismatch; nothing will be imported")
        packages.append(path)
    if not packages:
        raise ValueError("The release has no decks")
    return packages


def apply_packages(state: Path, packages: list[Path]) -> None:
    if not (state / "ready").exists():
        raise SetupRequired("Run setup once to connect your AnkiWeb account.")
    auth = SyncAuth.FromString((state / "auth.bin").read_bytes())
    collection = Collection(str(state / "collection.anki2"))
    try:
        # Bring phone reviews and edits into this collection before importing.
        incremental_sync(collection, auth, state)
        backups = state / "backups"
        backups.mkdir(exist_ok=True)
        collection.create_backup(backup_folder=str(backups), force=True, wait_for_completion=True)
        for path in packages:
            collection.import_anki_package(ImportAnkiPackageRequest(
                package_path=str(path.resolve()),
                options=ImportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False)))
        # Never mark a release delivered before both collection and media sync.
        incremental_sync(collection, auth, state)
    finally:
        collection.close()


def run(state: Path) -> None:
    if not (state / "ready").exists():
        raise SetupRequired("Run setup once to connect your AnkiWeb account.")
    release = read_json(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
    applied = state / "applied.json"
    previous = json.loads(applied.read_text()) if applied.exists() else {}
    if previous.get("release_id") == release["id"]:
        print("Already up to date.")
        return
    with tempfile.TemporaryDirectory(prefix="download-", dir=state) as temporary:
        packages = fetch_packages(release, Path(temporary))
        apply_packages(state, packages)
    private_write(applied, (json.dumps({"release_id": release["id"], "tag": release["tag_name"],
        "synced_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n").encode())
    print(f"Published deck update synced to AnkiWeb: {release['tag_name']}. Tap Sync on your iPhone.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "run", "status", "reauth"))
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    os.umask(0o077)
    state = args.state.expanduser().resolve()
    with locked(state):
        if args.command == "setup":
            print("First sync your existing cards from AnkiMobile to AnkiWeb.")
            print("Use the same AnkiWeb account here. Your password will not be saved.")
            email = input("AnkiWeb email: ").strip()
            password = getpass.getpass("AnkiWeb password: ")
            initialize(state, email, password)
            del password
            print("Account connected; fetching the latest deck release.")
            run(state)
        elif args.command == "reauth":
            if not (state / "ready").exists():
                raise SetupRequired("Run setup first.")
            email = (state / "account.txt").read_text().strip()
            password = getpass.getpass("AnkiWeb password for the configured account: ")
            collection = Collection(str(state / "collection.anki2"))
            try:
                auth = collection.sync_login(email, password, None)
                auth.io_timeout_secs = 60
                save_auth(state, auth)
            finally:
                collection.close()
            del password
            print("Sign-in refreshed.")
        elif args.command == "run":
            run(state)
        else:
            print("Account connected." if (state / "ready").exists() else "Waiting for one-time AnkiWeb sign-in.")
            if (state / "applied.json").exists():
                print((state / "applied.json").read_text())


if __name__ == "__main__":
    try:
        main()
    except SetupRequired as error:
        print(str(error))
        raise SystemExit(2)
    except BlockingIOError:
        print("Another updater is already running.")
    except Exception as error:
        # Never print authentication response objects or credential-bearing data.
        print(f"Updater failed ({type(error).__name__}); no release marked as delivered. Resolve the connection/error and retry.")
        raise SystemExit(1)
