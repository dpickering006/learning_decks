"""Test the updater against an isolated, local instance of Anki's sync server."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

from anki.collection import Collection
from anki.scheduler.v3 import CardAnswer

from build import ROOT, build_deck
from sync_decks import (REPOSITORY, SetupRequired, account_state, apply_packages,
                        configure, incremental_sync, initialize, run, subscriptions, wait_for_media)
from verify import import_package


def main():
    with tempfile.TemporaryDirectory(prefix="learning-decks-sync-test-") as temporary:
        root = Path(temporary)
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        endpoint = f"http://127.0.0.1:{port}/"
        env = {k: v for k, v in os.environ.items() if not k.startswith("SYNC_")}
        env.update(SYNC_USER1="test-user:test-password", SYNC_BASE=str(root / "server"),
                   SYNC_USER2="anna-test:test-password",
                   SYNC_HOST="127.0.0.1", SYNC_PORT=str(port))
        with (root / "server.log").open("w") as log:
            server = subprocess.Popen([sys.executable, "-m", "anki.syncserver"], env=env,
                                      stdout=log, stderr=log)
            phone = None
            try:
                for _ in range(100):
                    try:
                        with socket.create_connection(("127.0.0.1", port), timeout=.1):
                            break
                    except OSError:
                        if server.poll() is not None:
                            raise RuntimeError("Local test server failed to start")
                        time.sleep(.1)
                else:
                    raise RuntimeError("Local test server startup timed out")
                data = json.loads((ROOT / "sources/nsw-year-9-triangles.json").read_text())
                current_package = build_deck(data, root / "current", timestamp=int(time.time()))
                earlier = copy.deepcopy(data)
                for card in earlier["cards"]:
                    card.pop("answer_diagram", None)
                package = build_deck(earlier, root / "earlier", timestamp=int(time.time())-120)
                phone = Collection(str(root / "phone.anki2"))
                import_package(phone, package)
                auth = phone.sync_login("test-user", "test-password", endpoint)
                result = phone.sync_collection(auth, sync_media=False)
                # Full upload is limited to this disposable test server.
                assert result.required == result.FULL_UPLOAD
                phone.close_for_full_sync()
                phone.full_upload_or_download(auth=auth, server_usn=result.server_media_usn, upload=True)
                phone.reopen(after_full_sync=True)
                wait_for_media(phone, auth)

                state = root / "updater"
                state.mkdir(mode=0o700)
                initialize(state, "test-user", "test-password", endpoint)
                assert (state / "auth.bin").stat().st_mode & 0o777 == 0o600
                # A phone review AFTER the updater's initial download must survive.
                phone.decks.select(phone.decks.id_for_name(data["name"]))
                card = phone.sched.getCard()
                assert card is not None
                states = phone._backend.get_scheduling_states(card.id)
                phone.sched.answer_card(phone.sched.build_answer(card=card, states=states, rating=CardAnswer.EASY))
                before = phone.db.first("select id,nid,type,queue,due,ivl,factor,reps,lapses from cards where id=?", card.id)
                reviews = phone.db.all("select id,cid,ease,ivl,lastIvl,factor,time,type from revlog where cid=?", card.id)
                identities = phone.db.all("select id,guid from notes order by id")
                incremental_sync(phone, auth, root)
                apply_packages(state, [current_package])
                incremental_sync(phone, auth, root)
                assert phone.db.all("select id,guid from notes order by id") == identities
                assert phone.db.first("select id,nid,type,queue,due,ivl,factor,reps,lapses from cards where id=?", card.id) == before
                assert phone.db.all("select id,cid,ease,ivl,lastIvl,factor,time,type from revlog where cid=?", card.id) == reviews
                for cid in phone.find_cards(""):
                    current = phone.get_card(cid)
                    images = re.findall(r'<img src="([^"]+)"', current.note()["Back"])
                    assert len(images) == 1
                    for image in images:
                        assert image not in current.question()
                        assert (Path(phone.media.dir()) / image).is_file()
                assert list((state / "backups").glob("*.colpkg")), "No backup created"

                verify_account_routing(root, state, endpoint, data, current_package, phone, auth)

                # A schema conflict must stop rather than select an overwrite.
                updater = Collection(str(state / "collection.anki2"))
                try:
                    updater.mod_schema(check=False)
                    try:
                        incremental_sync(updater, auth, state)
                    except SetupRequired:
                        pass
                    else:
                        raise AssertionError("Full-sync conflict did not stop the updater")
                finally:
                    updater.close()
                assert phone.sync_collection(auth, sync_media=False).required == result.NO_CHANGES
                print("PASS GitHub-package → updater → local Anki server → phone: 40 updated cards, media delivered, phone reviews preserved, backup created, full-sync conflict refused")
            finally:
                if phone:
                    phone.close()
                server.terminate()
                server.wait(timeout=15)


def verify_account_routing(root, original_state, endpoint, data, current_package, original_phone, original_auth):
    """Two real sync accounts, with different subscriptions and private content."""
    anna_state = account_state(original_state, "anna")
    anna_state.mkdir(parents=True, mode=0o700)
    try:
        subscriptions(anna_state)
    except SetupRequired:
        pass
    else:
        raise AssertionError("Unconfigured named account inherited all decks")
    try:
        account_state(root, "../default")
    except ValueError:
        pass
    else:
        raise AssertionError("Account path traversal was accepted")

    extra = dict(slug="test-extra", name="Test::Unselected", deck_id=1732764503,
        description="Test-only deck", cards=[dict(id="extra-1", topic="Test", kind="recall",
        front="What is two plus two?", back="Four.")])
    extra_package = build_deck(extra, root / "extra")
    seed = copy.deepcopy(extra)
    seed.update(slug="test-personal", name="Test::Personal", deck_id=1732764504)
    seed["cards"][0]["id"] = "personal-1"
    seed_package = build_deck(seed, root / "seed")
    anna_phone = Collection(str(root / "anna-phone.anki2"))
    try:
        import_package(anna_phone, seed_package)
        auth = anna_phone.sync_login("anna-test", "test-password", endpoint)
        result = anna_phone.sync_collection(auth, sync_media=False)
        assert result.required == result.FULL_UPLOAD
        anna_phone.close_for_full_sync()
        anna_phone.full_upload_or_download(auth=auth, server_usn=result.server_media_usn, upload=True)
        anna_phone.reopen(after_full_sync=True)
        wait_for_media(anna_phone, auth)
        initialize(anna_state, "anna-test", "test-password", endpoint)
        assert (anna_state / "auth.bin").read_bytes() != (original_state / "auth.bin").read_bytes()

        payloads = {current_package.name: current_package.read_bytes(), extra_package.name: extra_package.read_bytes()}
        base_url = f"https://github.com/{REPOSITORY}/releases/download/test/"
        catalogue = [dict(slug=path.stem, name=path.stem, sha256=hashlib.sha256(payloads[path.name]).hexdigest())
                     for path in (current_package, extra_package)]
        release = dict(id=123, tag_name="test", assets=[dict(name=name, browser_download_url=base_url+name)
                       for name in ["catalog.json", *payloads]])

        class Download:
            def __init__(self, payload): self.payload = payload
            def __enter__(self): return self
            def __exit__(self, *_): pass
            def raise_for_status(self): pass
            def iter_content(self, _): yield self.payload

        def json_fixture(url):
            return catalogue if url.endswith("catalog.json") else release

        with patch("sync_decks.read_json", side_effect=json_fixture), patch("sync_decks.requests.get",
                side_effect=lambda url, **_: Download(payloads[url.rsplit("/",1)[-1]])) as download:
            configure(anna_state, [data["slug"]], release)
            run(anna_state)
            assert download.call_count == 1
            assert download.call_args.args[0].endswith(current_package.name)
            incremental_sync(anna_phone, auth, anna_state)
            assert anna_phone.card_count() == len(data["cards"]) + 1
            assert anna_phone.find_cards('deck:"Test::Personal"')
            assert not anna_phone.find_cards('deck:"Test::Unselected"')
            assert not anna_phone.db.all("select * from revlog"), "Another account's reviews leaked"
            download.reset_mock()
            run(anna_state)
            assert download.call_count == 0, "Unchanged subscriptions re-downloaded packages"

            # Subscription changes apply even without a new release. Removing a
            # subscription stops updates; it never deletes existing learner work.
            configure(anna_state, [extra["slug"]], release)
            run(anna_state)
            assert download.call_count == 1 and download.call_args.args[0].endswith(extra_package.name)
            incremental_sync(anna_phone, auth, anna_state)
            assert anna_phone.card_count() == len(data["cards"]) + 2
            assert anna_phone.find_cards('deck:"Test::Unselected"')
            try:
                apply_packages(anna_state, [current_package])
            except ValueError:
                pass
            else:
                raise AssertionError("Import outside the account's subscriptions was accepted")
            previous = (anna_state / "subscriptions.json").read_bytes()
            try:
                configure(anna_state, ["misspelled-deck"], release)
            except ValueError:
                pass
            else:
                raise AssertionError("Unknown deck subscription was accepted")
            assert (anna_state / "subscriptions.json").read_bytes() == previous
        incremental_sync(original_phone, original_auth, original_state)
        assert original_phone.card_count() == len(data["cards"]), "Another account's cards leaked"
        assert len(original_phone.db.all("select * from revlog")) == 1
        print("PASS account routing: separate collections and credentials, selected decks only, no shared reviews, same-release subscription changes, no deletions")
    finally:
        anna_phone.close()


if __name__ == "__main__":
    main()
