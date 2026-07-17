# Hevy routine builder

Build and update [Hevy](https://www.hevyapp.com/) workout routines programmatically via the
[Hevy API](https://api.hevyapp.com/docs/), instead of fighting the app's auto-suggested
workouts and "random" weight bumps.

Why this exists: the Hevy app likes to suggest exercises that need equipment you don't have
and auto-increment weights unpredictably. These scripts let you define a routine in code —
with **weights pinned to your actual working loads** and **explicit double-progression rules**
written into each exercise's notes — and push it straight to your account.

This particular config is a personal **3×/week full-body** plan (Full Body 1/2/3) tuned for:
- **Fat loss while keeping muscle** (moderate volume, reps in reserve, everything 8–12 reps)
- **Low-impact** lower body — no calf raises, no deep squats, no single-leg work
- **Rowing as the only cardio** (5 min / 1 km to open each session)
- **No repeats** — an exercise appears in at most one of the three routines (rowing excepted)

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
python3 build_routines.py     # creates a folder + 3 new routines (POST)
python3 update_routines.py    # updates those 3 routines in place (PUT)
python3 progression.py        # preview weight bumps from your logged sessions
python3 progression.py --apply  # ...and write them to Hevy
```

`build_routines.py` prints the routine IDs it creates — paste them into `update_routines.py`
(the `IDS` dict) before running updates.

### Auto-progression

`progression.py` reads your recent workouts and applies **double progression** to the
managed routines:

- Hit the **top of the rep range on every working set** (at or above the current target)
  → bump the weight by that exercise's increment.
- Logged a heavier weight across **all** sets without hitting the top → sync the target up
  to what you actually did. (Uses the *floor* weight of your sets, so a ramp like
  `40 → 50 → 60×8` doesn't get mistaken for a 60kg working weight.)
- Otherwise → hold.

It's **dry-run by default** — prints a table of proposed changes; `--apply` writes them via
`PUT`. Run it after a session (or weekly) and the routine keeps itself current. Increments
live in the `INCREMENTS` map at the top of the script.

**Equipment-aware (where Hevy fails).** Hevy will happily suggest a weight you can't load.
This script won't — it snaps every proposed weight to what your gym can actually make:

- **Dumbbells** are logged by Hevy as the *pair total*. The rack is modelled as 4–40 kg
  per hand in 2 kg steps, so a bump is always "the next pair up". At the top it reports
  `MAXED — progress reps/sets`, never an impossible jump. Edit `DUMBBELLS`.
- **Barbells** snap to 4 kg steps (smallest plate 2 kg, one per side). Edit `PLATE_MIN`.
- A target that isn't achievable (e.g. a leftover 34 kg DB weight) is flagged
  `FIX→achievable` and corrected down to the nearest real load.

Equipment lives in the config block at the top of `progression.py`.

## How it works

- `GET /v1/workouts` — read your recent sessions to find real working weights
- `POST /v1/routine_folders` — group the new routines
- `POST /v1/routines` — create routines with pinned weights, rep ranges, rest, and progression notes
- `PUT /v1/routines/{id}` — overwrite a routine (send the full exercise list; partial updates replace everything)

Each working set carries a `rep_range` (8–12) and a fixed `weight_kg`, plus a short note like:

> +4kg (2kg/side) once all sets hit 12.

Exercise template IDs (e.g. `75A4F6C4` = Leg Extension) come from `GET /v1/exercise_templates`.

## Notes

- `data/` (your pulled workout history) and `.env` (your key) are gitignored — keep them that way.
- The API is create/update only; deleting a routine is done in the app.
- Not medical advice — get a professional's eyes on your programming.
