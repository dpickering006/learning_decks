# Adding learning material

Create `sources/<slug>.json`, using the existing triangles source as an example. Keep all questions self-contained in plain text so the CSV also works. Optional diagrams supplement the text.

```json
{
  "slug": "example-topic",
  "name": "Learning::Year group::Example topic",
  "deck_id": 1732764506,
  "description": "Audience, prerequisites and topic scope.",
  "cards": [
    {
      "id": "example-001",
      "topic": "Example topic",
      "kind": "why",
      "front": "Why does doubling a rectangle's width double its area when its length stays fixed?",
      "back": "Area equals length times width, so doubling just the width doubles the product."
    }
  ]
}
```

## Learning style

- One fact, relationship or short application per card.
- Ask for an answer from memory: no yes/no questions or multiple-choice options.
- Include explanation and transfer to unfamiliar examples, alongside necessary formula recall.
- Prefer “why” and “how” where natural. Use `kind` values `recall`, `why` or `apply`.
- Keep each answer to at most 20 whitespace-separated words, including formulas. The builder enforces this limit.
- Write for the stated school year. Check maths, units, rounding, ambiguity and syllabus scope before publishing.
- State all essential information in the question. Avoid giving away the answer in the diagram or topic label.
- Put only material intended for public sharing in this public repository.

You can ask an assistant:

> Add a deck on [topic] for [year/curriculum] to this repository. Follow AUTHORING.md and the existing JSON format. Include recall, explanation and application questions, each with one learning target and an answer of at most 20 words. Check the current curriculum and all answers. Preserve the IDs of existing cards. Build and run the import checks before publishing.

## Stable identities

Use a unique, permanent slug and deck ID. Deck IDs are integers from 1073741824 to 2147483647; the build rejects collisions. The example ID above is available until used. Card IDs must be unique within a deck; give new cards new IDs. Never renumber cards, reuse a deleted ID, or change IDs just because wording changes.

The builder derives each Anki GUID from a permanent namespace, deck slug and card ID. It uses a fixed note model and fields. Keep the model ID, field names and template layout schema stable; ordinary wording, CSS and diagram edits are safe. Correct existing cards in place. Removing a card from a future package does not delete a learner's existing copy; tell learners to suspend or delete obsolete cards themselves.

## Diagrams

Both `diagram` (question side) and `answer_diagram` (revealed answer only) are optional scene names from `DIAGRAMS` in `scripts/diagrams.py`. Each scene includes a family, labelled geometry, explanation steps and descriptive alternative text. Register a new scene, or add a renderer for a new geometry family. Do not put worked answers in question scenes, including their titles and alternative text.

Scenes may also be registered in `visuals/*.json`, which the renderer loads automatically. The Pythagoras scenes use this format; their additional geometric constructions are implemented in `scripts/pythagoras_diagrams.py`.

The builder appends answer images to the existing `Back` field. Keep the permanent model ID, five fields, template and note GUIDs unchanged when adding diagrams. CSV exports retain the original plain-text answers.

Every referenced image is bundled in the package and given a content-based filename so updated images import correctly. Keep labels readable on a phone. The bundled Noto Sans and Noto Sans Math fonts cover mathematical symbols consistently across computers; the renderer rejects unsupported glyphs and labels outside the image. View the actual generated images to catch overlaps and mathematical mistakes. Font provenance and licence are in `assets/fonts/README.md` and `OFL.txt`.

To check upgrading a previously published deck, keep its `.apkg` outside `dist`, build the new version, then run:

```sh
python scripts/verify.py --previous-package /path/to/earlier/nsw-year-9-triangles.apkg
```

This additionally verifies the original card identities, scheduling and review history survive and that the new answer diagrams appear only after revealing.

## Publication

1. Edit/add source files and update the README download table for new decks.
2. Run `python scripts/build.py` and `python scripts/verify.py` in the installed virtual environment.
3. Commit and push to `main`.
4. Check the **Build and publish learning decks** Actions run. A successful run creates a release containing every deck, CSV and catalogue. A failed build leaves the previous release available.

The permanent link for a deck is:

```text
https://github.com/dpickering006/learning_decks/releases/latest/download/<slug>.apkg
```

The checks import each package twice into a temporary Anki collection, render its cards, check bundled images and CSV, review a card, and import a changed version with an additional card. They assert that the correction arrives, the extra card appears, and the existing card's scheduling and review log survive. They do not use anyone's actual Anki collection and do not replace a human content review or testing in the intended mobile app.
