"""Exercise package integrity and real Anki imports in disposable collections."""
from __future__ import annotations

import copy
import csv
import html
import json
import re
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path

from anki.collection import Collection
from anki.importing import ImportAnkiPackageOptions, ImportAnkiPackageRequest
from anki.scheduler.v3 import CardAnswer

from build import ROOT, build_deck, validate


def import_package(collection: Collection, path: Path) -> None:
    collection.import_anki_package(ImportAnkiPackageRequest(
        package_path=str(path.resolve()),
        options=ImportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False)))


def verify(source: Path) -> None:
    data = json.loads(source.read_text())
    validate(data)
    package = ROOT / "dist" / f"{data['slug']}.apkg"
    count = len(data["cards"])
    with (ROOT / "dist" / f"{data['slug']}.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.reader(stream))
    assert rows == [[c["front"], c["back"]] for c in data["cards"]], "CSV content or header mismatch"

    with tempfile.TemporaryDirectory(prefix="learning-decks-test-") as temporary:
        directory = Path(temporary)
        with zipfile.ZipFile(package) as archive:
            assert archive.testzip() is None
            media = json.loads(archive.read("media"))
            assert len(set(media.values())) == len(media)
            for entry in media:
                assert archive.read(entry).startswith(b"\x89PNG\r\n\x1a\n")
            database = directory / "package.anki2"
            database.write_bytes(archive.read("collection.anki2"))
            with sqlite3.connect(database) as db:
                assert db.execute("pragma integrity_check").fetchone()[0] == "ok"
                assert db.execute("select count(*) from cards").fetchone()[0] == count
                assert db.execute("select count(distinct guid) from notes").fetchone()[0] == count
                assert db.execute("select count(*) from revlog").fetchone()[0] == 0
                for fields, in db.execute("select flds from notes"):
                    for image in re.findall(r'<img src="([^"]+)"', fields):
                        assert image in media.values(), f"Missing media: {image}"

        collection = Collection(str(directory / "collection.anki2"))
        try:
            import_package(collection, package)
            assert len(collection.find_cards("")) == count
            for cid in collection.find_cards(""):
                card = collection.get_card(cid)
                note = card.note()
                question, answer = card.question(), card.answer()
                assert note["Front"] in question and note["Back"] in answer
                assert "{{" not in question + answer, "Unresolved template"
                for filename in re.findall(r'<img src="([^"]+)"', question):
                    assert (Path(collection.media.dir()) / filename).is_file()
            import_package(collection, package)
            assert len(collection.find_cards("")) == count, "Re-import duplicated cards"

            # Review an actual card through Anki's scheduler, then publish a correction
            # to that same note plus a new note. The original review must survive.
            collection.decks.select(collection.decks.id_for_name(data["name"]))
            card = collection.sched.getCard()
            assert card is not None
            original_id = html.unescape(card.note()["CardID"])
            states = collection._backend.get_scheduling_states(card.id)
            answer = collection.sched.build_answer(card=card, states=states, rating=CardAnswer.EASY)
            collection.sched.answer_card(answer)
            before = collection.db.first(
                "select id,nid,type,queue,due,ivl,factor,reps,lapses from cards where id=?", card.id)
            reviews = collection.db.all("select * from revlog where cid=?", card.id)
            assert len(reviews) == 1

            updated = copy.deepcopy(data)
            changed = next(c for c in updated["cards"] if c["id"] == original_id)
            changed["front"] += " (Import verification.)"
            changed["back"] = "Temporary correction used only in an isolated import test."
            added = copy.deepcopy(data["cards"][0])
            added["id"] += "-new-import-test"
            updated["cards"].append(added)
            newer = build_deck(updated, directory / "updated", timestamp=int(time.time()) + 60)
            import_package(collection, newer)
            assert len(collection.find_cards("")) == count + 1, "New card not added or existing cards duplicated"
            assert collection.get_card(card.id).note()["Back"] == changed["back"], "Correction did not import"
            assert collection.db.first(
                "select id,nid,type,queue,due,ivl,factor,reps,lapses from cards where id=?", card.id) == before
            assert collection.db.all("select * from revlog where cid=?", card.id) == reviews
        finally:
            collection.close()
    print(f"PASS {data['slug']}: {count} cards, bundled media, CSV, native rendering, duplicate-free import, update, new card, review preservation")


if __name__ == "__main__":
    for source in sorted((ROOT / "sources").glob("*.json")):
        verify(source)
