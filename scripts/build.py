"""Build every source deck as a self-contained Anki package and plain-text CSV."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
from pathlib import Path

import genanki
from diagrams import DIAGRAMS, draw_diagram

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "dpickering006/learning_decks"
# Permanent namespace from the original test download. Keep it even if the repo moves.
GUID_NAMESPACE = "dpickering006/learning-decks"
MODEL_ID = 1732764500  # Permanent: existing learners must keep their note identity.
FIELDS = ["CardID", "Front", "Back", "Diagram", "Topic"]
QFMT = '''<div class="wrap"><div class="topic">{{Topic}}</div>
<div class="question">{{Front}}</div>
{{#Diagram}}<div class="diagram">{{Diagram}}</div>{{/Diagram}}
<div class="prompt">Try it from memory. Explain your reasoning before revealing.</div></div>'''
AFMT = '''{{FrontSide}}<hr id="answer"><div class="wrap answer">{{Back}}</div>'''
CSS = '''.card { font-family: Arial, sans-serif; font-size: 22px; line-height: 1.5;
 text-align: left; color: #172a3a; background: #f7f8fb; margin: 0; padding: 22px; }
.wrap { max-width: 680px; margin: auto; }
.topic { font-size: 13px; text-transform: uppercase; letter-spacing: .08em; color: #52677b; margin-bottom: 16px; }
.question { font-weight: 600; }
.prompt { font-size: 14px; color: #52677b; margin-top: 18px; }
.diagram img { display: block; width: 100%; max-width: 560px; height: auto; margin: 18px auto 0; border-radius: 12px; }
.answer { padding-top: 10px; color: #075f50; }
hr { border: 0; border-top: 2px solid #cbd5df; margin: 24px auto; max-width: 680px; }
.nightMode.card, .night_mode.card { color: #edf2f7; background: #16212c; }
.nightMode .topic, .nightMode .prompt, .night_mode .topic, .night_mode .prompt { color: #bdccdb; }
.nightMode .answer, .night_mode .answer { color: #81e0c0; }
@media(max-width: 420px) { .card { font-size: 20px; padding: 16px; } }'''


def validate(data: dict) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", data["slug"]):
        raise ValueError("Use a lowercase hyphenated slug")
    if not isinstance(data["deck_id"], int) or not 2**30 <= data["deck_id"] < 2**31:
        raise ValueError("deck_id must be a permanent integer between 2**30 and 2**31")
    if not data["cards"]:
        raise ValueError("A deck must contain cards")
    ids = set()
    for card in data["cards"]:
        if card["id"] in ids:
            raise ValueError(f"Duplicate card ID: {card['id']}")
        ids.add(card["id"])
        for field in ("id", "front", "back", "topic"):
            if not isinstance(card[field], str) or not card[field].strip():
                raise ValueError(f"Empty {field}: {card['id']}")
        if len(card["back"].split()) > 20:
            raise ValueError(f"Answer exceeds 20 words: {card['id']}")
        if card["kind"] not in {"recall", "why", "apply"}:
            raise ValueError(f"Unknown question kind: {card['id']}")
        for field in ("diagram", "answer_diagram"):
            if card.get(field) and card[field] not in DIAGRAMS:
                raise ValueError(f"Unknown {field}: {card[field]}")


def build_deck(data: dict, output: Path, timestamp: int | None = None) -> Path:
    validate(data)
    output.mkdir(parents=True, exist_ok=True)
    media_dir = output / "media"
    media_dir.mkdir(exist_ok=True)
    model = genanki.Model(MODEL_ID, "Learning decks - recall v1",
        fields=[{"name": name} for name in FIELDS],
        templates=[{"name": "Recall", "qfmt": QFMT, "afmt": AFMT}],
        css=CSS, sort_field_index=0)
    deck = genanki.Deck(data["deck_id"], data["name"],
        description=html.escape(data["description"]))
    media = set()
    for card in data["cards"]:
        def image_markup(key):
            if not key:
                return ""
            path = draw_diagram(key, media_dir)
            media.add(str(path))
            alt = html.escape(DIAGRAMS[key]["alt"], quote=True)
            return f'<img src="{path.name}" alt="{alt}">'

        diagram = image_markup(card.get("diagram"))
        back = html.escape(card["back"])
        if card.get("answer_diagram"):
            # Keep the permanent five-field model. Answer media belongs in Back,
            # so it cannot appear in the question or reset learners' card IDs.
            back += '<div class="diagram explanation">' + image_markup(card["answer_diagram"]) + '</div>'
        note = genanki.Note(model=model,
            guid=genanki.guid_for(GUID_NAMESPACE, data["slug"], card["id"]),
            fields=[html.escape(card["id"]), html.escape(card["front"]),
                    back, diagram, html.escape(card["topic"])],
            tags=[data["slug"], card["kind"], card["topic"].lower().replace(" ", "_")])
        deck.add_note(note)
    package = genanki.Package(deck)
    package.media_files = sorted(media)
    apkg = output / f"{data['slug']}.apkg"
    package.write_to_file(str(apkg), timestamp=timestamp)
    # Plain text, two columns, no header. All questions also work without images.
    with (output / f"{data['slug']}.csv").open("w", encoding="utf-8", newline="") as stream:
        csv.writer(stream).writerows((card["front"], card["back"]) for card in data["cards"])
    return apkg


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    sources = sorted((ROOT / "sources").glob("*.json"))
    if not sources:
        raise ValueError("No decks found")
    decks = [json.loads(path.read_text()) for path in sources]
    if len({d["deck_id"] for d in decks}) != len(decks) or len({d["slug"] for d in decks}) != len(decks):
        raise ValueError("Deck IDs and slugs must be unique")
    catalog = []
    for deck in decks:
        apkg = build_deck(deck, args.output)
        catalog.append({"name": deck["name"], "slug": deck["slug"], "cards": len(deck["cards"]),
            "description": deck["description"],
            "download": f"https://github.com/{REPOSITORY}/releases/latest/download/{apkg.name}",
            "sha256": hashlib.sha256(apkg.read_bytes()).hexdigest()})
        print(f"Built {apkg.name}: {len(deck['cards'])} cards")
    (args.output / "catalog.json").write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
    notes = ["Download a .apkg file below, then open it in Anki. Each package includes its diagrams.",
        "", "Try answering from memory before revealing. Re-import later versions to receive updates; keep learning-progress import disabled.", ""]
    notes += [f"- [{d['name']}]({d['download']}) — {d['cards']} cards" for d in catalog]
    notes += ["", "CSV alternatives have two plain-text columns and no header. Use .apkg for diagrams and reliable card matching on updates."]
    (args.output / "RELEASE.md").write_text("\n".join(notes) + "\n")


if __name__ == "__main__":
    main()
