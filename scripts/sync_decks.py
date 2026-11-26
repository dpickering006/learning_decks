"""Subscribe separate AnkiWeb accounts to selected published decks.

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


def initialize(state: Path, email: str, password: str, endpoint: str | None = None,
               initial_packages: list[Path] | None = None) -> None:
    """Download an existing account, or explicitly seed a verified empty one."""
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
        if result.required in (result.FULL_DOWNLOAD, result.FULL_SYNC):
            collection.close_for_full_sync()
            collection.full_upload_or_download(auth=auth, server_usn=result.server_media_usn, upload=False)
            collection.reopen(after_full_sync=True)
        elif result.required == result.FULL_UPLOAD:
            if not initial_packages:
                raise SetupRequired("First sync your existing phone cards, or explicitly use --new-account for a new empty account.")
        elif result.required != result.NO_CHANGES:
            raise SetupRequired("The account needs a sync decision. Nothing was uploaded.")

        if not collection.card_count():
            if not initial_packages:
                raise SetupRequired("This AnkiWeb account contains no cards. Sync your phone first, or use --new-account for a new account.")
            selected = subscriptions(state)
            if selected is None or any(path.stem not in selected for path in initial_packages):
                raise ValueError("A new account needs an explicit list of selected decks")
            for path in initial_packages:
                collection.import_anki_package(ImportAnkiPackageRequest(
                    package_path=str(path.resolve()),
                    options=ImportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False)))
            # Prefer incremental sync. If the empty server needs initialisation,
            # recheck immediately before the explicitly requested initial upload.
            result = collection.sync_collection(auth, sync_media=False)
            if result.new_endpoint:
                auth.endpoint = result.new_endpoint
            if result.required == result.FULL_UPLOAD:
                collection.close_for_full_sync()
                collection.full_upload_or_download(auth=auth, server_usn=result.server_media_usn, upload=True)
                collection.reopen(after_full_sync=True)
            elif result.required != result.NO_CHANGES:
                raise SetupRequired("The account changed during setup. No full upload was performed; inspect before retrying.")
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


def account_state(root: Path, account: str | None) -> Path:
    if account is None:
        return root
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", account):
        raise ValueError("Account labels must use lowercase letters, numbers and hyphens")
    return root / "accounts" / account


def subscriptions(state: Path) -> list[str] | None:
    path = state / "subscriptions.json"
    if not path.exists():
        # Backwards compatibility for the original account only. New named
        # accounts must have an explicit list, never inherit all public decks.
        if state.parent.name == "accounts":
            raise SetupRequired("Choose this account's decks with configure --decks before connecting it.")
        return None
    value = json.loads(path.read_text())
    if value == {"decks": "all"}:
        return None
    decks = value.get("decks")
    if not isinstance(decks, list) or not decks or any(
        not isinstance(slug, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in decks
    ):
        raise ValueError("Invalid deck subscriptions")
    return sorted(set(decks))


def release_catalogue(release: dict) -> tuple[dict, list]:
    assets = {item["name"]: item["browser_download_url"] for item in release["assets"]}
    prefix = f"https://github.com/{REPOSITORY}/releases/download/"
    if not all(url.startswith(prefix) for url in assets.values()):
        raise ValueError("Unexpected release asset origin")
    catalogue = read_json(assets["catalog.json"])
    seen = set()
    for deck in catalogue:
        slug = deck["slug"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) or slug in seen:
            raise ValueError("Invalid or duplicate deck slug")
        seen.add(slug)
    return assets, catalogue


def select_decks(catalogue: list, selected: list[str] | None) -> list:
    if selected is None:
        return catalogue
    unknown = set(selected) - {deck["slug"] for deck in catalogue}
    if unknown:
        raise ValueError("Unknown deck subscription: " + ", ".join(sorted(unknown)))
    return [deck for deck in catalogue if deck["slug"] in selected]


def configure(state: Path, decks: list[str], release: dict) -> None:
    _, catalogue = release_catalogue(release)
    if not decks:
        raise ValueError("Select at least one deck, or use all explicitly")
    selected = None if decks == ["all"] else sorted(set(decks))
    select_decks(catalogue, selected)
    private_write(state / "subscriptions.json", (json.dumps({"decks": selected if selected is not None else "all"}, indent=2) + "\n").encode())


def fetch_packages(release: dict, directory: Path, selected: list[str] | None = None) -> list[Path]:
    """Pin all downloads to one release and verify each package's checksum."""
    assets, catalogue = release_catalogue(release)
    catalogue = select_decks(catalogue, selected)
    packages = []
    for deck in catalogue:
        slug = deck["slug"]
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
    selected = subscriptions(state)
    if selected is not None and any(path.stem not in selected for path in packages):
        raise ValueError("Refusing a deck outside this account's subscriptions")
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
    selected = subscriptions(state)
    selection_key = selected if selected is not None else "all"
    release = read_json(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
    applied = state / "applied.json"
    previous = json.loads(applied.read_text()) if applied.exists() else {}
    if previous.get("release_id") == release["id"] and previous.get("decks", "all") == selection_key:
        print("Already up to date.")
        return
    with tempfile.TemporaryDirectory(prefix="download-", dir=state) as temporary:
        packages = fetch_packages(release, Path(temporary), selected)
        apply_packages(state, packages)
    private_write(applied, (json.dumps({"release_id": release["id"], "tag": release["tag_name"], "decks": selection_key,
        "synced_at": datetime.now(timezone.utc).isoformat()}, indent=2) + "\n").encode())
    print(f"Published deck update synced to AnkiWeb: {release['tag_name']}. Tap Sync on your iPhone.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("setup", "run", "status", "reauth", "configure", "list-decks"))
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--account", help="Separate account label, e.g. anna; omitted uses the original account")
    parser.add_argument("--decks", nargs="+", help="Published deck slugs, or all; used with configure")
    parser.add_argument("--email", help="Email for setup; passwords are always entered at a hidden prompt")
    parser.add_argument("--new-account", action="store_true", help="During setup, seed a new empty account with its selected decks")
    args = parser.parse_args()
    os.umask(0o077)
    root = args.state.expanduser().resolve()
    state = account_state(root, args.account)
    if args.command == "configure" and not args.decks:
        parser.error("configure requires --decks")
    if args.decks and args.command != "configure":
        parser.error("--decks is only used with configure")
    if (args.email or args.new_account) and args.command != "setup":
        parser.error("--email and --new-account are only used with setup")
    if args.new_account and not args.account:
        parser.error("--new-account requires a separate named --account")
    with locked(state):
        if args.command in ("configure", "list-decks"):
            release = read_json(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
            if args.command == "configure":
                configure(state, args.decks, release)
                print("Deck subscriptions saved. Previously imported decks are not deleted.")
            else:
                _, catalogue = release_catalogue(release)
                for deck in catalogue:
                    print(f"{deck['slug']}: {deck['name']}")
        elif args.command == "setup":
            chosen = subscriptions(state)  # Fail before credentials if unconfigured.
            if args.new_account and chosen is None:
                raise SetupRequired("Choose specific decks before setting up a new account.")
            if (state / "ready").exists():
                raise SetupRequired("Already connected. Use run or status; no new sign-in is needed.")
            if args.new_account:
                print("New account setup: selected decks will be sent only if Anki reports the account is empty.")
            else:
                print("First sync your existing cards from AnkiMobile to AnkiWeb.")
            print("Use the same AnkiWeb account here. Your password will not be saved.")
            email = (args.email or input("AnkiWeb email: ")).strip()
            if args.email:
                print("Connecting AnkiWeb account: " + email)
            other_accounts = [root / "account.txt", *root.glob("accounts/*/account.txt")]
            if any(path.parent != state and path.exists() and path.read_text().strip() == email.casefold()
                   for path in other_accounts):
                raise SetupRequired("That AnkiWeb account is already connected under another profile. Use a separate account.")
            password = getpass.getpass("AnkiWeb password: ")
            if args.new_account:
                release = read_json(f"https://api.github.com/repos/{REPOSITORY}/releases/latest")
                with tempfile.TemporaryDirectory(prefix="initial-", dir=state) as temporary:
                    packages = fetch_packages(release, Path(temporary), chosen)
                    initialize(state, email, password, initial_packages=packages)
            else:
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
            try:
                chosen = subscriptions(state)
                print("Deck subscriptions: " + (", ".join(chosen) if chosen is not None else "all published decks"))
            except SetupRequired:
                print("Deck subscriptions: not selected yet.")
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
