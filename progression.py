#!/usr/bin/env python3
"""Suggest Hevy routine weight bumps from logged performance (double progression).

SUGGESTIONS ONLY by default (2026-08-17): Toni commands weight increments
himself, so the weekly run just prints what looks ready. Nothing is written
to Hevy unless --apply is passed explicitly (manual workflow dispatch or CLI).

Reads your recent workouts, and for each working exercise in the managed routines
(identified by the fixed ids below + ids.json, not by title):
  - if you hit the TOP of the rep range on all working sets (at >= the current target),
    suggest bumping the target by that exercise's increment;
  - if you logged a heavier weight than the target without hitting the top, suggest
    syncing the target up to what you actually used;
  - otherwise hold.

    python3 progression.py            # preview only (the default and the schedule)
    python3 progression.py --apply    # write the suggestions via PUT
"""
import json, os, re, sys, urllib.request, urllib.error

KEY = open(".env").read().split("=", 1)[1].strip()
BASE = "https://api.hevyapp.com"
HDRS = {"api-key": KEY, "Content-Type": "application/json"}
APPLY = "--apply" in sys.argv
IDS = {  # the managed routines (same ids as update_routines.py)
    "c63a8064-bd5a-439d-b6c6-0808bfbaf8b6",  # Upper 1 (was Full Body 1)
    "f2dfd68b-377f-430d-a894-c7cdac854614",  # Lower 1 (was Full Body 2)
    "dc6a26fe-2098-4c1c-bff9-9454d7cd1386",  # Upper 2 (was Full Body 3)
}
if os.path.exists("ids.json"):  # routines created later (Lower 2) land here
    IDS |= set(json.load(open("ids.json")).values())

# Managed by feel — never suggested or auto-changed (matched by exercise title,
# since template ids for new exercises are resolved at run time).
HOLD_TITLES = {"Squat (Barbell)", "Deadlift (Barbell)"}

# Per-exercise weight increment (kg). Gym inventory (see CLAUDE.md):
# cables have +2kg add-on weights; disks are 2.5/5/10/20 per side, so barbell = 5
# (2.5/side) and single-end/held-plate = 2.5; pin-stack machines = 5.
# Dumbbell lifts ignore this — they snap to the next real pair in DB_TOTAL.
INCREMENTS = {
    "75A4F6C4": 5,    # Leg Extension (Machine) — pin stack
    "79D0BB3A": 2.5,  # Bench Press (Barbell) — 1.25kg disks exist
    "923874CA": 2.5,  # Landmine 180 — disk on the loaded end
    "55E6546F": 2.5,  # Bent Over Row (Barbell) — 1.25kg disks exist
    "B2398CD1": 2.5,  # Decline Crunch (Weighted) — held disk
    "78683336": 2.5,  # Chest Fly (Machine) — stack has half-steps (15 → 17.5)
}
# Cable stations and kettlebells snap to the racks modelled below instead —
# their INCREMENTS entries would be ignored.

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def increment_for(tid, title, note):
    if tid in INCREMENTS:
        return INCREMENTS[tid]
    m = re.search(r"\+(\d+(?:\.\d+)?)\s*kg", note or "")
    return float(m.group(1)) if m else 2

def fmt(n):
    return str(int(n)) if float(n).is_integer() else str(n)

# --- equipment model: what loads your gym can actually make ---
# This is where Hevy falls down: it'll happily suggest a weight you can't load.
# Inventory confirmed by Toni 2026-08-17 (see CLAUDE.md).
EPS = 0.01
DUMBBELLS = list(range(4, 41, 2))                 # rack runs 4-40kg per hand in 2kg steps
PLATE_MIN = 1.25                                  # smallest disk: 1.25kg
BARBELL_STEP = 2 * PLATE_MIN                      # smallest symmetric barbell jump = 2.5kg
DB_TOTAL = sorted({2 * d for d in DUMBBELLS})     # Hevy logs DB lifts as the pair total
KETTLEBELLS = [8, 12, 16, 20, 24]                 # single bells
CABLE_STACK = [25, 30, 35, 40, 45, 50]            # cable stations: pin values
CABLE_ADDON = 2                                   # one +2kg add-on weight
CABLE_LOADS = sorted({s + a for s in CABLE_STACK for a in (0, CABLE_ADDON)})
CABLE_TITLES = {"Triceps Pushdown", "Face Pull"}  # cable stations w/o "Cable" in the title

# kind -> the discrete loads that kind snaps to (bb/stack progress by increment)
LOADS = {
    "db": DB_TOTAL,
    "cable": CABLE_LOADS,
    "kb1": KETTLEBELLS,                    # single bell (swings)
    "kb2": [2 * k for k in KETTLEBELLS],   # pair, logged as the total (curls)
}

def equip(title):
    if "(Dumbbell)" in title: return "db"
    if "(Barbell)" in title: return "bb"
    if "Kettlebell" in title:
        return "kb1" if "Swing" in title else "kb2"
    if "Cable" in title or title in CABLE_TITLES: return "cable"
    return "stack"   # other machines / landmine / held plate — trust the configured increment

def is_load(kind, w):
    L = LOADS.get(kind)
    return True if L is None else any(abs(w - x) < EPS for x in L)

def snap_down(kind, w):
    L = LOADS[kind]
    below = [x for x in L if x <= w + EPS]
    return below[-1] if below else L[0]

def maxed_hint(kind, total):
    if kind in ("db", "kb2"):
        return f"({fmt(total / 2)}kg per hand)"
    return "(top of rack)"

def next_load(kind, current, inc):
    """Next achievable load above `current`, or None if at the equipment ceiling."""
    L = LOADS.get(kind)
    if L is not None:
        higher = [x for x in L if x > current + EPS]
        return higher[0] if higher else None          # None => equipment ceiling reached
    if kind == "bb":
        steps = max(1, round(inc / BARBELL_STEP))
        return current + steps * BARBELL_STEP          # snapped to 2.5kg
    return current + inc                                # stack: trust configured increment

# --- pull recent workouts (enough history to cover every exercise) ---
perf = {}   # template_id -> (date, [(weight, reps), ...] normal sets, latest only)
for page in range(1, 6):
    st, d = call("GET", f"/v1/workouts?page={page}&pageSize=10")
    if not isinstance(d, dict) or not d.get("workouts"):
        break
    for w in d["workouts"]:               # API returns newest-first
        for ex in w["exercises"]:
            tid = ex["exercise_template_id"]
            if tid in perf:
                continue                   # keep only the most recent session
            sets = [(s.get("weight_kg"), s.get("reps")) for s in ex["sets"]
                    if s["type"] == "normal" and s.get("reps") is not None]
            if sets:
                perf[tid] = (w["start_time"][:10], sets)

# --- pull the managed routines ---
st, d = call("GET", "/v1/routines?page=1&pageSize=10")
routines = [r for r in d["routines"] if r["id"] in IDS]

changes = []   # (routine, exercise_obj, old, new)
rows = []
for r in sorted(routines, key=lambda x: x["title"]):
    rows.append(("HDR", r["title"]))
    for ex in r["exercises"]:
        tid = ex["exercise_template_id"]
        work = [s for s in ex["sets"] if s["type"] == "normal" and s.get("rep_range") and s.get("weight_kg") is not None]
        if not work:
            continue   # cardio / bodyweight — nothing to load
        target = work[0]["weight_kg"]
        top = work[0]["rep_range"]["end"]
        n_expected = len(work)
        title = ex["title"]
        inc = increment_for(tid, title, ex.get("notes"))
        kind = equip(title)

        if title in HOLD_TITLES:
            rows.append(("ROW", title, f"{fmt(target)}kg", "managed by feel", "hold (manual)", f"{fmt(target)}kg"))
            continue

        # Correct any target that isn't an achievable load (e.g. a DB weight your rack can't make).
        if not is_load(kind, target):
            fixed = snap_down(kind, target)
            rows.append(("ROW", title, f"{fmt(target)}kg", "not an achievable load", "FIX→achievable", f"{fmt(fixed)}kg"))
            changes.append((r, ex, target, fixed))
            continue

        if tid not in perf:
            rows.append(("ROW", title, f"{fmt(target)}kg", "no recent log", "hold", f"{fmt(target)}kg"))
            continue
        date, sets = perf[tid]
        weights = [w for w, _ in sets]
        reps = [rp for _, rp in sets]
        # working weight = the load you completed across ALL sets (floor), so ramp/pyramid
        # sets like 40/50/60 don't trick it into chasing a single heavy top-set.
        used = min(weights)
        last = ", ".join(f"{fmt(w)}×{rp}" for w, rp in sets)
        hit_top = len(sets) >= n_expected and all(rp >= top for rp in reps) and used >= target - EPS
        if hit_top:
            nxt = next_load(kind, used, inc)
            if nxt is None:                       # at the equipment ceiling — can't add load
                new = target
                decision = f"MAXED {maxed_hint(kind, target)} +reps"
            else:
                new = nxt
                decision = f"PROGRESS → {fmt(new)}"
        elif used > target + EPS:
            new = used
            decision = "sync to actual"
        else:
            new = target
            decision = "hold"
        rows.append(("ROW", title, f"{fmt(target)}kg", f"{last} ({date})", decision, f"{fmt(new)}kg"))
        if abs(new - target) > EPS:
            changes.append((r, ex, target, new))

# --- print table ---
print(f"\n{'EXERCISE':30s} {'TARGET':>8s}  {'LAST SESSION':28s} {'DECISION':16s} {'NEW':>8s}")
print("-" * 96)
for row in rows:
    if row[0] == "HDR":
        print(f"\n== {row[1]} ==")
    else:
        _, title, tgt, last, dec, new = row
        flag = "→" if dec.startswith("PROGRESS") or dec.startswith("sync") else " "
        print(f"{flag}{title:29s} {tgt:>8s}  {last:28s} {dec:16s} {new:>8s}")

print(f"\n{len(changes)} weight change(s) suggested.")
if not changes:
    print("Nothing to do.")
    sys.exit(0)

if not APPLY:
    print("Suggestions only — nothing written to Hevy. Re-run with --apply to write them.")
    sys.exit(0)

# --- apply: round-trip each routine, mutating only the weights, then PUT ---
def set_payload(s):
    return {"type": s["type"], "weight_kg": s.get("weight_kg"), "reps": s.get("reps"),
            "distance_meters": s.get("distance_meters"), "duration_seconds": s.get("duration_seconds"),
            "custom_metric": s.get("custom_metric"),
            **({"rep_range": s["rep_range"]} if s.get("rep_range") else {})}

touched = {}
for r, ex, old, new in changes:
    touched.setdefault(r["id"], r)
    for s in ex["sets"]:
        if s["type"] == "normal" and s.get("rep_range") and s.get("weight_kg") is not None:
            s["weight_kg"] = new

for rid, r in touched.items():
    payload = {"routine": {"title": r["title"], "notes": r.get("notes"), "exercises": [
        {"exercise_template_id": ex["exercise_template_id"], "superset_id": ex.get("superset_id"),
         "rest_seconds": ex.get("rest_seconds"), "notes": ex.get("notes"),
         "sets": [set_payload(s) for s in ex["sets"]]}
        for ex in r["exercises"]]}}
    st, resp = call("PUT", f"/v1/routines/{rid}", payload)
    ok = isinstance(resp, dict)
    print(f"[{st}] updated {r['title']}" + ("" if ok else f"  ERROR: {str(resp)[:200]}"))
