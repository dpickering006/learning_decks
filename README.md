# Learning decks

Short Anki decks for recall, explanation and applying ideas. Attempt each question before revealing the answer. Each card has one learning target and an answer of at most 20 words.

## Download a deck

| Deck | Contents | Downloads |
| --- | --- | --- |
| NSW Year 9 — Triangles | 40 cards, 20 question diagrams and 40 answer diagrams: angles, area, Pythagoras, similarity, right-angle trigonometry | [Anki deck (.apkg)](https://github.com/dpickering006/learning_decks/releases/latest/download/nsw-year-9-triangles.apkg) · [Plain CSV](https://github.com/dpickering006/learning_decks/releases/latest/download/nsw-year-9-triangles.csv) |

Every card now has a worked visual explanation on the answer side. Twenty cards also have a question diagram, with the solution hidden until you reveal the answer. Re-import the updated `.apkg` to add these explanations to your existing cards.

**Bookmark [the latest downloads](https://github.com/dpickering006/learning_decks/releases/latest).** Every publication includes all available decks. The links above always retrieve the newest successfully published versions.

## Try it in Anki

1. Download the **.apkg** file. It includes the cards, formatting and diagrams, and works offline after import.
2. Open it in your app:
   - **AnkiMobile (iPhone/iPad):** open the downloaded file in Files or Safari's downloads, then use Share → AnkiMobile / Open in Anki.
   - **AnkiDroid (Android):** open the downloaded file with AnkiDroid, or choose Import from AnkiDroid's menu.
   - **Anki desktop:** choose File → Import and select the file.
3. Open **Learning → NSW Year 9 → Triangles** and start studying. Use paper for calculations. Use degree mode for the calculator questions.
4. Explain your answer before revealing it. If you could only recognise the answer after seeing it, mark it **Again**. Start with a manageable number of new cards, for example 5–10 per day; deck options control this. Anki may initially show only part of the 40-card deck because of its daily limit.

These instructions are for the Anki family of apps: Anki, AnkiMobile and AnkiDroid. Similarly named flashcard apps can have different import formats.

Official import help: [AnkiMobile](https://docs.ankiweb.net/ankimobile/shared-decks), [AnkiDroid](https://www.ankidroid.org/docs/#importing), [Anki packages](https://docs.ankiweb.net/manual/importing/packaged-decks).

## Receive updates

For iPhone/iPad users who want to avoid repeated downloads, the optional
[Ubuntu background updater](SYNC.md) imports new GitHub releases into your
AnkiWeb account. After one-time setup, tap **Sync** in AnkiMobile to receive
new cards and diagrams. The updater checks every five minutes while online.
Each learner can have a separate AnkiWeb account and a selected list of decks;
their review progress stays separate. See [account subscriptions](SYNC.md#different-decks-for-different-accounts).

GitHub hosts the download; it is not an Anki sync server. Standard Anki apps do not subscribe to this repository and automatically fetch new decks. Download a new deck when you want it, or download and import an existing deck again to receive corrections and additions. Do not delete the existing deck first.

When import options are available, leave **Import any learning progress** off and use **Update notes: If newer**. These packages contain no learner review history. Permanent note IDs allow matching cards to update while preserving your existing reviews; this is checked using Anki's own importer. If you edit a card locally after a release, Anki may keep your newer copy. Choose **Always** only when you intentionally want the published text to replace your edits.

[AnkiWeb sync](https://docs.ankiweb.net/ankimobile/syncing) can then carry an imported deck between your own devices. Keep separate Anki accounts/profiles for learners who need separate progress.

The CSV alternative has two columns, front and back, with no header. It contains complete text questions but no diagrams, styling or stable Anki IDs. For reliable updates, use the .apkg file consistently; importing both formats can create duplicates.

## Scope of the triangles deck

This is a Year 9 practice deck, combining earlier geometry skills with introductory Stage 5 topics. Schools teach the topics in different orders; it is not a complete course or an official assessment.

| Topic | Cards |
| --- | ---: |
| Angles | 8 |
| Area and side lengths | 6 |
| Pythagoras | 10 |
| Similarity | 7 |
| Right-angle trigonometry | 9 |

The questions and diagrams are original. Curriculum context: [NESA Mathematics K–10 (2022) course structure](https://curriculum.nsw.edu.au/learning-areas/mathematics/mathematics-k-10-2022/overview/course) and [NSW Mathematics 7–10 teaching units](https://education.nsw.gov.au/teaching-and-learning/curriculum/mathematics/planning-programming-and-assessing-mathematics-7-10/mathematics-7-10-units).

## Add or change decks

See [AUTHORING.md](AUTHORING.md). Add a source JSON file, or edit a card while retaining its ID, and commit to `main`. GitHub Actions builds every deck, checks imports and preservation of reviews, and publishes a new release. The permanent download links continue to work.

For a local build:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
.venv/bin/python scripts/build.py
.venv/bin/python scripts/verify.py
```

Files appear in `dist/`. Build tools: [genanki](https://github.com/kerrickstaley/genanki), Pillow; import checks use the Anki Python package. The JSON [download catalogue](https://github.com/dpickering006/learning_decks/releases/latest/download/catalog.json) lists every deck and its checksum; it is for tooling, not an Anki subscription format.
