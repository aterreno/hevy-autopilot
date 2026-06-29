#!/usr/bin/env python3
"""Auto-progress Hevy routine weights from logged performance (double progression).

Reads your recent workouts, and for each working exercise in the (v2) routines:
  - if you hit the TOP of the rep range on all working sets (at >= the current target),
    bump the target by that exercise's increment;
  - if you logged a heavier weight than the target without hitting the top, sync the
    target up to what you actually used;
  - otherwise hold.

Dry-run by default — prints a table of proposed changes. Pass --apply to write them.

    python3 progression.py            # preview only
    python3 progression.py --apply    # write changes via PUT
"""
import json, re, sys, urllib.request, urllib.error

KEY = open(".env").read().split("=", 1)[1].strip()
BASE = "https://api.hevyapp.com"
HDRS = {"api-key": KEY, "Content-Type": "application/json"}
APPLY = "--apply" in sys.argv
ROUTINE_TAG = "(v2)"   # which routines to manage

# Per-exercise weight increment (kg). Falls back to parsing "+Nkg" from the note, then 2.5.
INCREMENTS = {
    "C7973E0E": 5,    # Leg Press (retired; kept for old logs)
    "68CE0B9B": 5,    # Hip Thrust (Machine) — replaces leg press on FB A
    "75A4F6C4": 5,    # Leg Extension (Machine) — replaces leg press on FB C
    "79D0BB3A": 2.5,  # Bench Press (Barbell)
    "6A6C31A5": 2.5,  # Lat Pulldown
    "11A123F3": 2.5,  # Seated Leg Curl
    "37FCC2BB": 2,    # Bicep Curl (DB)
    "2B4B7310": 2.5,  # Romanian Deadlift
    "55E6546F": 2.5,  # Bent Over Row
    "878CD1D0": 2,    # Shoulder Press (DB)
    "422B08F1": 2,    # Lateral Raise (DB)
    "23A48484": 2.5,  # Cable Crunch
    "07B38369": 2,    # Incline Bench (DB)
    "D7D7FCCE": 2.5,  # Landmine Row
    "78683336": 2.5,  # Chest Fly (Machine)
    "93A552C6": 2.5,  # Triceps Pushdown
}

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def increment_for(tid, note):
    if tid in INCREMENTS:
        return INCREMENTS[tid]
    m = re.search(r"\+(\d+(?:\.\d+)?)\s*kg", note or "")
    return float(m.group(1)) if m else 2.5

def fmt(n):
    return str(int(n)) if float(n).is_integer() else str(n)

# --- equipment model: what loads your gym can actually make ---
# This is where Hevy falls down: it'll happily suggest a weight you can't load.
EPS = 0.01
DUMBBELLS = [10, 12, 14, 16]                     # available dumbbells (kg, per hand)
PLATE_MIN = 1.25                                 # smallest plate you own
BARBELL_STEP = 2 * PLATE_MIN                      # smallest symmetric barbell jump = 2.5kg
DB_TOTAL = sorted({2 * d for d in DUMBBELLS})     # Hevy logs DB lifts as the pair total: [20,24,28,32]

def equip(title):
    if "(Dumbbell)" in title: return "db"
    if "(Barbell)" in title or "Landmine" in title: return "bb"
    return "stack"   # machine / cable — increments depend on the gym's stack

def is_db_load(w):
    return any(abs(w - x) < EPS for x in DB_TOTAL)

def snap_db_down(w):
    below = [x for x in DB_TOTAL if x <= w + EPS]
    return below[-1] if below else DB_TOTAL[0]

def db_hint(total):
    return f"({fmt(total / 2)}kg DBs)"

def next_load(kind, current, inc):
    """Next achievable load above `current`, or None if at the equipment ceiling."""
    if kind == "db":
        higher = [x for x in DB_TOTAL if x > current + EPS]
        return higher[0] if higher else None          # None => dumbbell ceiling reached
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
routines = [r for r in d["routines"] if ROUTINE_TAG in r["title"]]

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
        inc = increment_for(tid, ex.get("notes"))
        title = ex["title"]
        kind = equip(title)

        # Correct any target that isn't an achievable load (e.g. a DB weight your rack can't make).
        if kind == "db" and not is_db_load(target):
            fixed = snap_db_down(target)
            rows.append(("ROW", title, f"{fmt(target)}kg", "not an achievable DB load", "FIX→achievable", f"{fmt(fixed)}kg"))
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
            if nxt is None:                       # at the dumbbell ceiling — can't add load
                new = target
                decision = f"MAXED {db_hint(target)} +reps"
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

print(f"\n{len(changes)} weight change(s) proposed.")
if not changes:
    print("Nothing to do.")
    sys.exit(0)

if not APPLY:
    print("Dry-run. Re-run with --apply to write these to Hevy.")
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
    if ex.get("notes"):
        ex["notes"] = re.sub(r"Start\s+\d+(?:\.\d+)?kg", f"Start {fmt(new)}kg", ex["notes"])

for rid, r in touched.items():
    payload = {"routine": {"title": r["title"], "notes": r.get("notes"), "exercises": [
        {"exercise_template_id": ex["exercise_template_id"], "superset_id": ex.get("superset_id"),
         "rest_seconds": ex.get("rest_seconds"), "notes": ex.get("notes"),
         "sets": [set_payload(s) for s in ex["sets"]]}
        for ex in r["exercises"]]}}
    st, resp = call("PUT", f"/v1/routines/{rid}", payload)
    ok = isinstance(resp, dict)
    print(f"[{st}] updated {r['title']}" + ("" if ok else f"  ERROR: {str(resp)[:200]}"))
