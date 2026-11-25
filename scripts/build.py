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
from PIL import Image, ImageDraw, ImageFont

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
        if card.get("diagram") and card["diagram"] not in DIAGRAMS:
            raise ValueError(f"Unknown diagram: {card['diagram']}")


def draw_diagram(kind: str, directory: Path) -> Path:
    """Original diagrams, built from geometry; no external image dependencies."""
    img = Image.new("RGB", (800, 480), "#ffffff")
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default(size=31)
    small = ImageFont.load_default(size=21)
    ink, accent = "#172a3a", "#007b80"

    def line(points, fill=ink, width=5):
        draw.line(points, fill=fill, width=width, joint="curve")

    def label(point, text, fill=ink):
        if text == "θ":
            # Pillow's bundled font lacks Greek glyphs; draw the symbol directly.
            x, y = point
            draw.ellipse((x - 8, y - 14, x + 8, y + 14), outline=fill, width=2)
            draw.line([(x - 7, y), (x + 7, y)], fill=fill, width=2)
            return
        draw.text(point, text, fill=fill, font=font, anchor="mm")

    if kind == "angles":
        line([(130, 370), (650, 370), (410, 75), (130, 370)])
        label((220, 332), "52°")
        label((563, 332), "67°")
        label((407, 146), "?")
    elif kind == "isosceles":
        line([(160, 370), (640, 370), (400, 65), (160, 370)])
        label((400, 144), "40°")
        label((242, 332), "?")
        label((558, 332), "?")
        line([(265, 202), (289, 221)], accent)
        line([(511, 221), (535, 202)], accent)
    elif kind == "area":
        line([(100, 365), (680, 365), (460, 65), (100, 365)])
        for y in range(75, 365, 22):
            line([(460, y), (460, min(y + 12, 365))], accent, 3)
        line([(460, 340), (485, 340), (485, 365)], accent, 3)
        label((390, 402), "12 cm")
        label((522, 230), "7 cm", accent)
    else:
        # Right angle at the bottom right; the marked acute angle is bottom left.
        line([(150, 365), (650, 365), (650, 75), (150, 365)])
        line([(623, 365), (623, 338), (650, 338)], accent, 3)
        labels = DIAGRAMS[kind]
        for text, point in zip(labels, [(400, 402), (708, 220), (375, 177), (244, 340)]):
            if text:
                label(point, text, accent if "?" in text or text == "θ" else ink)
    draw.text((400, 460), "Diagram not to scale", font=small, fill="#52677b", anchor="mm")
    # Content-addressed names make media corrections reliable during re-import.
    import io
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    raw = buffer.getvalue()
    name = f"ld-triangles-{kind}-{hashlib.sha256(raw).hexdigest()[:12]}.png"
    path = directory / name
    path.write_bytes(raw)
    return path


DIAGRAMS = {
    "angles": (), "isosceles": (), "area": (),
    "pythagoras": ("8 cm", "6 cm", "?", ""),
    "trig-sides": ("", "", "", "θ"),
    "trig-sine": ("", "?", "10 cm", "30°"),
    "trig-tangent": ("8 cm", "?", "", "35°"),
    "trig-cosine": ("?", "", "12 cm", "40°"),
}


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
        diagram = ""
        if card.get("diagram"):
            path = draw_diagram(card["diagram"], media_dir)
            media.add(str(path))
            diagram = f'<img src="{path.name}" alt="Triangle diagram; all given measurements are also in the question.">'
        note = genanki.Note(model=model,
            guid=genanki.guid_for(GUID_NAMESPACE, data["slug"], card["id"]),
            fields=[html.escape(card["id"]), html.escape(card["front"]),
                    html.escape(card["back"]), diagram, html.escape(card["topic"])],
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
