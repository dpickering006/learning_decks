"""Test the updater against an isolated, local instance of Anki's sync server."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time

from anki.collection import Collection
from anki.scheduler.v3 import CardAnswer

from build import ROOT, build_deck
from sync_decks import SetupRequired, apply_packages, incremental_sync, initialize, wait_for_media
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


if __name__ == "__main__":
    main()
