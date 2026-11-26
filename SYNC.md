# Automatic updates for AnkiMobile

This optional updater removes the repeated download/import step on your phone:

**GitHub release → Ubuntu updater → your AnkiWeb account → Sync on iPhone/iPad.**

The updater checks for new releases every five minutes while Ubuntu is online.
It uses Anki's own Python backend; no desktop window or paid subscription is needed.
This is a custom updater, not a built-in AnkiMobile GitHub subscription.

## One-time connection

1. In AnkiMobile, tap **Sync** and let your existing cards, images and progress
   finish syncing to your AnkiWeb account.
2. On Ubuntu, run:

   ```sh
   ~/.local/share/learning-decks-updater/.venv/bin/python \
     ~/.local/share/learning-decks-updater/scripts/sync_decks.py setup
   ```

3. Enter the **same AnkiWeb email and password** as your phone at the terminal
   prompts. This is an AnkiWeb account, not an AnkiHub account. The password is
   hidden and is not saved. Do not put credentials in GitHub or command arguments.
4. After it reports that the release has synced, tap **Sync** on your phone.
   Let image syncing finish. Future published updates follow the same route;
   there is no need to download another `.apkg` manually.

The initial connection downloads your existing collection from AnkiWeb. It will
not upload an empty collection or initialise an empty remote account. If your
account has no cards, sync your phone first and retry.

## What it preserves

- Each deck keeps its permanent note IDs. Imports exclude scheduling and deck
  settings, and use Anki's default update-if-newer behaviour for note content.
- Before each update, the updater syncs existing phone reviews and edits down.
- It creates a collection backup before importing, then syncs the updated notes
  and all media back to AnkiWeb. Your phone receives them on its next sync.
- A release is recorded as delivered only after collection and media syncing
  both finish. Failed runs can retry without duplicating the cards.
- Any request for a full upload/download decision stops automatic updating.
  The updater does not choose a destructive overwrite on your behalf.

The private collection, backups and authentication session key are stored in
`~/.local/share/learning-decks-sync/` with access limited to your Ubuntu user.
They are separate from this public repository. Your password is not stored;
the protected session key lets Anki continue syncing without repeated sign-in.

## Different decks for different accounts

Each learner must use a separate AnkiWeb account. Named profiles have separate
credentials, collections, backups, release status and timers. They do not share
study history. The original account continues receiving all published decks
unless its subscriptions are explicitly changed.

From the updater checkout, list the published decks and select a learner's list:

```sh
.venv/bin/python scripts/sync_decks.py list-decks
.venv/bin/python scripts/sync_decks.py configure --account anna \
  --decks nsw-year-9-triangles
```

`anna` is a local profile label, not an email address. Pass multiple published
deck slugs after `--decks` for a larger list. New profiles require an explicit
selection; they never automatically receive every current or future deck.
Use `--decks all` only when that is intentional.

After the learner has created their AnkiWeb account and synced their initial
cards from their own phone, connect the profile once:

```sh
.venv/bin/python scripts/sync_decks.py setup --account anna
cp deploy/learning-decks-sync@.service deploy/learning-decks-sync@.timer \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now learning-decks-sync@anna.timer
```

Use that learner's AnkiWeb credentials at the prompts. Reusing an account already
connected to another profile is rejected. Their private state is stored in
`~/.local/share/learning-decks-sync/accounts/anna/`. An account that is still empty
needs the initial setup described above; the updater never selects a full upload
to initialise a remote account automatically.

To change the list, rerun `configure --account anna --decks ...`. The new list is
processed on the next scheduled run, even if no new GitHub release has appeared.
Removing a subscription stops subsequent updates; it does **not** delete cards
already imported or any other decks the learner has added independently.

```sh
.venv/bin/python scripts/sync_decks.py status --account anna
systemctl --user stop learning-decks-sync@anna.timer
systemctl --user start learning-decks-sync@anna.timer
journalctl --user -u learning-decks-sync@anna.service -n 30
```

Omit `--account` to manage the original account. For example, `configure --decks
nsw-year-9-triangles` restricts only that account to the triangles deck.

## Installation on Ubuntu

```sh
git clone https://github.com/dpickering006/learning_decks.git \
  ~/.local/share/learning-decks-updater
cd ~/.local/share/learning-decks-updater
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
mkdir -p ~/.local/share/learning-decks-sync ~/.config/systemd/user
chmod 700 ~/.local/share/learning-decks-sync
cp deploy/learning-decks-sync.service deploy/learning-decks-sync.timer \
  ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now learning-decks-sync.timer
```

The timer is safe to enable before setup: it skips running until the account is
connected. To run after logout, the Ubuntu user must have lingering enabled
(`loginctl show-user "$USER" -p Linger`). Do not point the updater at an existing
desktop Anki profile: it owns its own separate collection.

## Check, pause or repair

```sh
# Connection and last delivered release (no credentials printed)
~/.local/share/learning-decks-updater/.venv/bin/python \
  ~/.local/share/learning-decks-updater/scripts/sync_decks.py status

# Timer and logs
systemctl --user list-timers learning-decks-sync.timer
journalctl --user -u learning-decks-sync.service -n 30

# Pause / resume
systemctl --user stop learning-decks-sync.timer
systemctl --user start learning-decks-sync.timer

# Renew an expired sign-in for the same account
~/.local/share/learning-decks-updater/.venv/bin/python \
  ~/.local/share/learning-decks-updater/scripts/sync_decks.py reauth
```

Updates reach the phone only after a successful updater run and a phone sync.
If Ubuntu is offline, GitHub is unavailable, sign-in expires or a full-sync
conflict occurs, the existing deck remains usable and automatic updates wait.

## Verification

Run `python scripts/verify_sync.py` after installing the test requirements. It
starts Anki's own sync server on a temporary localhost port with two test accounts,
then checks an earlier deck → phone review → updater import → phone sync cycle.
It verifies note identity, scheduling, review history, media, backups and refusal
to choose a full-sync overwrite. It also verifies selected-deck delivery,
account isolation, subscription changes within the same release, and retention
of previously imported or unrelated cards. It never connects to a real AnkiWeb account.
