# hevy-autopilot — routine decisions

Decisions Toni has made about his routines. Follow these when editing scripts or
routines; don't re-litigate them.

Personal/medical context is deliberately kept OUT of this repo — it lives in
Claude's private memory. Don't add health details here or to commit messages.

## Structure

- Three routines titled **Full Body 1/2/3** — no version suffixes ("(v2)" etc.).
  Scripts identify routines by the fixed IDs in `update_routines.py` /
  `progression.py`, never by title.
- **No exercise appears in more than one routine** (rowing warm-up excepted).
  `update_routines.py` asserts this.
- **Every exercise works 8–12 reps.** No 12–15 / 12–20 ranges.
- Notes stay **short**: one cue + the progression rule. No paragraphs.
- Weights in `update_routines.py` are pinned to live values — before rebuilding,
  check the live routines so progressed weights aren't regressed.

## Gym equipment (drives all increments)

- **Cables** (lat pulldown, pushdown): +2kg add-on weights → increment 2.
- **Disks**: 2.5 / 5 / 10 / 20 kg per side → barbell +5kg (2.5/side),
  landmine and held-plate exercises +2.5kg.
- **Dumbbells**: pairs grow 2kg per hand (10, 12, 14, 16, 18, …); small DBs
  from 4kg exist for raises. Hevy logs the pair total.
- **Pin-stack machines** (leg extension): +5kg. Chest fly stack has 2.5 half-steps.

## Exercise history (why things are the way they are)

- **Squat (Barbell)**: progressed by feel only — in `HOLD`, never auto-adjusted.
- **Seated leg curl**: retired 2026-07-17, hurts knees (loaded knee flexion)
  → **Romanian Deadlift (Dumbbell)** on Full Body 1.
- **Leg extension**: retired 2026-07-06 for knees, but Toni asked for it back
  2026-07-17 — keep it, monitor knees.
- **Hip thrust**: retired 2026-07-17, Toni doesn't like it.
- **Leg press**: retired 2026-06-23 (knees).
- **Cable crunch**: retired 2026-07-17 → **Decline Crunch (Weighted)**
  (`B2398CD1`, the weighted incline abs bench).
- **Lateral raise** base weight: 4kg × 2 = 8kg pair total.
- **Seated Cable Row - V Grip** (`0393F233`): Toni likes it — added to Full
  Body 2 on 2026-07-17 at his logged 40kg.
- **Landmine 180** (`923874CA`): the core slot on Full Body 3 (Toni used to do
  it and asked for it back, 2026-07-17).
- **Glute isolation**: explicitly not a priority (2026-07-17) — don't add hip
  thrusts or glute accessories unasked.
- Knees are sensitive: no new loaded knee-flexion/extension exercises without
  asking; low-impact lower body, controlled depth, no calf raises.
- Don't silently drop an exercise — if a swap removes a movement, say so.
