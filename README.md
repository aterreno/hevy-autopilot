# Hevy routine builder

Build and update [Hevy](https://www.hevyapp.com/) workout routines programmatically via the
[Hevy API](https://api.hevyapp.com/docs/), instead of fighting the app's auto-suggested
workouts and "random" weight bumps.

Why this exists: the Hevy app likes to suggest exercises that need equipment you don't have
and auto-increment weights unpredictably. These scripts let you define a routine in code —
with **weights pinned to your actual working loads** and the progression rule written into
each exercise's notes — and push it straight to your account.

This particular config is a **4-day upper/lower rotation** (Upper 1 → Lower 1 → Upper 2 →
Lower 2, repeat) tuned for:
- **Training on consecutive days** — upper/lower alternation means 2-3 gym days in a row
  never hit the same muscle groups twice
- **Fat loss while keeping muscle** (moderate volume, 1-2 reps in reserve, everything 8–12 reps)
- **Arms, legs and core emphasis** — biceps and triceps every upper day, two hamstring-heavy
  lower days (DB Romanian deadlift + a barbell deadlift hinge day), core in every session
- **Low-impact** lower body — no calf raises, controlled squat depth, no lunges
- **Rowing as the only cardio** (5 min / 1 km to open each session)
- **No repeats** — an exercise appears in at most one of the four routines (rowing excepted)
- **Manual progression** — the weekly job only *suggests* weight bumps; nothing changes
  unless you say so

Treat the weights and exercise picks as an example — edit them to your own numbers.

## Setup

Requires a Hevy Pro subscription (the API key lives in **Settings → Developer**).
No dependencies — pure Python 3 standard library.

```bash
cp .env.example .env
# paste your key into .env
```

## Usage

```bash
python3 update_routines.py          # dry-run: resolve exercises, print the plan
python3 update_routines.py --apply  # PUT the existing routines, POST any missing
python3 progression.py              # suggest weight bumps from your logged sessions
python3 progression.py --apply      # ...and write them to Hevy
```

`update_routines.py` owns the whole design. Routines it has created before are updated in
place (ids live in the `IDS` dict + `ids.json`); a routine with no id yet is created and its
id saved to `ids.json` — commit that file. Exercise template ids for new movements are
resolved by title against `GET /v1/exercise_templates` at run time, and the resolution is
printed so a fallback pick is never silent.

Both scripts can also be run from the **Actions** tab (the API key lives in the repo
secrets), so no laptop is needed:

- **Rebuild routines** — manual only. Dry-run by default; tick the box to write.
- **Weekly progression** — runs every Sunday night as **suggestions only**: it opens an
  issue listing which lifts look ready for more weight, and writes nothing. To apply,
  bump the weight in the app yourself, or run the workflow manually with the apply box
  ticked. (Squat and deadlift are excluded — they progress by feel.)

### Progression logic (double progression)

- Hit the **top of the rep range on every working set** (at or above the current target)
  → suggest bumping the weight by that exercise's increment.
- Logged a heavier weight across **all** sets without hitting the top → suggest syncing
  the target up to what you actually did. (Uses the *floor* weight of your sets, so a ramp
  like `40 → 50 → 60×8` doesn't get mistaken for a 60kg working weight.)
- Otherwise → hold.

**Equipment-aware (where Hevy fails).** Hevy will happily suggest a weight you can't load.
This script won't — it snaps every proposed weight to what your gym can actually make:

- **Dumbbells** are logged by Hevy as the *pair total*. The rack is modelled as 4–40 kg
  per hand in 2 kg steps, so a bump is always "the next pair up". At the top it reports
  `MAXED — progress reps/sets`, never an impossible jump. Edit `DUMBBELLS`.
- **Kettlebells** snap to the rack (8–24 kg bells): swings to the next single bell,
  curls to the next pair. Edit `KETTLEBELLS`.
- **Cable stations** snap to the real stack (25–50 kg pins + a 2 kg add-on), including
  the 3 kg pin-jump after an add-on (42 → 45) and the 52 kg ceiling. Edit `CABLE_STACK`.
- **Barbells** snap to 2.5 kg steps (smallest disk 1.25 kg, one per side). Edit `PLATE_MIN`.
- A target that isn't achievable (e.g. a leftover 34 kg DB weight) is flagged
  `FIX→achievable` and corrected down to the nearest real load.

Equipment lives in the config block at the top of `progression.py`.

## How it works

- `GET /v1/workouts` — read your recent sessions to find real working weights
- `GET /v1/exercise_templates` — resolve template ids for new exercises by title
- `POST /v1/routines` — create a routine that doesn't exist yet
- `PUT /v1/routines/{id}` — overwrite a routine (send the full exercise list; partial updates replace everything)

Each working set carries a `rep_range` (8–12) and a fixed `weight_kg`, plus a short note like:

> +5kg (2.5/side) once all sets hit 12.

## Notes

- `data/` (your pulled workout history) and `.env` (your key) are gitignored — keep them that way.
- The API is create/update only; deleting a routine is done in the app.
- Not medical advice — get a professional's eyes on your programming.
