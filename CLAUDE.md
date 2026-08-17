# hevy-autopilot — routine decisions

Decisions Toni has made about his routines. Follow these when editing scripts or
routines; don't re-litigate them.

Personal/medical context is deliberately kept OUT of this repo — it lives in
Claude's private memory. Don't add health details here or to commit messages.

## Structure (redesigned 2026-08-17)

- Four routines — **Upper 1 / Lower 1 / Upper 2 / Lower 2** — cycled in order
  (U1 → L1 → U2 → L2). Replaced Full Body 1/2/3: Toni often trains 2-3 days in
  a row and full-body every day was hitting the same muscle groups back-to-back.
  Upper/lower alternation fixes that; he also asked for more variety and more
  hamstring work.
- No version suffixes in titles. Scripts identify routines by the fixed IDs in
  `update_routines.py` (+ `ids.json` for routines created later), never by title.
- **No exercise appears in more than one routine** (rowing warm-up excepted).
  `update_routines.py` asserts this.
- **Every loaded exercise works 8–12 reps.** Timed core (plank) is the only
  exception.
- Notes stay **short**: one cue + the increment. No paragraphs.
- Weights in `update_routines.py` are pinned to live values — before rebuilding,
  check the live routines so progressed weights aren't regressed.
- **Progression is manual (2026-08-17).** Toni commands weight increases
  himself. The weekly Action is suggestions-only (dry-run + issue); `--apply`
  only happens on explicit manual dispatch. The increment in each exercise note
  is guidance for Toni, not for automation.
- **Squat (Barbell) and Deadlift (Barbell): progress by feel** — in
  `HOLD_TITLES`, never suggested or auto-adjusted.

## Travel routines — delete in the app (overdue)

- **Travel 1/2** (created 2026-07-21 for two weeks away) should now be deleted —
  Toni is back. The API can't delete routines, so it has to happen in the app:
  folder `3272365`, routine IDs `dd2fe666-c34e-4555-b6ba-e40bb98e7bbe` /
  `aad79051-9ccc-4f8c-8015-b192fbd4ffd5`. `travel_routines.py` was removed
  2026-08-17 (in git history if ever needed). Drop this section once deleted.

## Gym equipment (drives all increments)

- **Cables** (lat pulldown, pushdown, face pull): +2kg add-on weights → increment 2.
- **Disks**: 2.5 / 5 / 10 / 20 kg per side → barbell +5kg (2.5/side),
  landmine and held-plate exercises +2.5kg.
- **Dumbbells**: pairs grow 2kg per hand (10, 12, 14, 16, 18, …); small DBs
  from 4kg exist for raises. Hevy logs the pair total.
- **Kettlebells**: exact rack unverified — assumed 4kg jumps per bell
  (8/12/16/20/24). Curls start with a 12kg pair, swings with a single 16.
  Confirm sizes with Toni before modelling increments any tighter.
- **Pin-stack machines** (leg extension): +5kg. Chest fly stack has 2.5 half-steps.

## Exercise history (why things are the way they are)

2026-08-17 redesign (Toni asked: more variety, focus arms/legs/core, hamstring
work back, deadlifts back, manual progression, favourites = barbell squat,
barbell bench, kettlebell curls):

- **Deadlift (Barbell)** added as the Lower 2 anchor — Toni used to deadlift
  and asked for it back. Replaces **Romanian Deadlift (Barbell)** (same hinge
  slot; DB RDL on Lower 1 still covers hamstring volume). By feel, no
  suggestions.
- **Bicep Curl**: dumbbell → **kettlebell** — Toni's favourite way to curl.
  If Hevy has no kettlebell-curl template, `update_routines.py` falls back to
  the DB template (logged with KB weights) and prints which it picked.
- **Landmine Row** retired 2026-08-17 — not disliked, just squeezed out; row
  volume is covered by Bent Over Row + Seated Cable Row. Fine to bring back if
  a slot opens.
- **New 2026-08-17**: Face Pull (rear delts/posture), Hammer Curl (DB),
  Kettlebell Swing, Back Extension (bodyweight, hamstring/glute), Plank.
  Back Extension assumes the gym has a hyperextension bench — swap for good
  mornings if not (ask first).
- **Lateral raise**: auto-progression kept writing 16kg while Toni logged 12kg
  pairs — pinned at 16 with a "drop back to 12" note; let him settle it.
- **Squat (Barbell)**: progressed by feel only — never auto-adjusted.
- **Seated leg curl**: retired 2026-07-17, hurts knees (loaded knee flexion)
  → **Romanian Deadlift (Dumbbell)**.
- **Leg extension**: retired 2026-07-06 for knees, but Toni asked for it back
  2026-07-17 — keep it, monitor knees.
- **Hip thrust**: retired 2026-07-17, Toni doesn't like it.
- **Leg press**: retired 2026-06-23 (knees).
- **Cable crunch**: retired 2026-07-17 → **Decline Crunch (Weighted)**
  (`B2398CD1`, the weighted incline abs bench).
- **Seated Cable Row - V Grip** (`0393F233`): Toni likes it — keep it.
- **Landmine 180** (`923874CA`): Toni asked for it back 2026-07-17 — the core
  slot on Lower 1.
- **Glute isolation**: explicitly not a priority (2026-07-17) — don't add hip
  thrusts or glute accessories unasked.
- Knees are sensitive: no new loaded knee-flexion/extension exercises without
  asking; low-impact lower body, controlled depth, no calf raises. (Quads are
  therefore squat + leg extension only — 1 day per cycle is accepted.)
- Don't silently drop an exercise — if a swap removes a movement, say so.
