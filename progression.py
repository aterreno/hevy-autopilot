#!/usr/bin/env python3
"""Auto-progress Hevy routine weights from logged performance (double progression).

Reads your recent workouts, and for each working exercise in the managed routines
(identified by the fixed IDS below, not by title):
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
IDS = {  # the managed routines (same ids as update_routines.py)
    "c63a8064-bd5a-439d-b6c6-0808bfbaf8b6",  # Full Body 1
    "f2dfd68b-377f-430d-a894-c7cdac854614",  # Full Body 2
    "dc6a26fe-2098-4c1c-bff9-9454d7cd1386",  # Full Body 3
}
HOLD = {"D04AC939"}    # Squat (Barbell) — weight managed by feel, never auto-changed

# Per-exercise weight increment (kg). Gym inventory (see CLAUDE.md):
# cables have +2kg add-on weights; disks are 2.5/5/10/20 per side, so barbell = 5
# (2.5/side) and single-end/held-plate = 2.5; pin-stack machines = 5.
# Dumbbell lifts ignore this — they snap to the next real pair in DB_TOTAL.
INCREMENTS = {
    "75A4F6C4": 5,    # Leg Extension (Machine) — pin stack
    "79D0BB3A": 5,    # Bench Press (Barbell)
    "6A6C31A5": 2,    # Lat Pulldown (Cable)
    "0393F233": 2,    # Seated Cable Row - V Grip
    "923874CA": 2.5,  # Landmine 180 — disk on the loaded end
    "2B4B7310": 5,    # Romanian Deadlift (Barbell)
    "55E6546F": 5,    # Bent Over Row (Barbell)
    "B2398CD1": 2.5,  # Decline Crunch (Weighted) — held disk, smallest 2.5
    "D7D7FCCE": 2.5,  # Landmine Row — one 2.5kg disk on the loaded end
    "78683336": 2.5,  # Chest Fly (Machine) — stack has half-steps (15 → 17.5)
    "93A552C6": 2,    # Triceps Pushdown (Cable)
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
    return float(m.group(1)) if m else 2

def fmt(n):
    return str(int(n)) if float(n).is_integer() else str(n)

# --- equipment model: what loads your gym can actually make ---
# This is where Hevy falls down: it'll happily suggest a weight you can't load.
EPS = 0.01
DUMBBELLS = list(range(4, 41, 2))                 # rack runs 4-40kg per hand in 2kg steps
PLATE_MIN = 2.5                                   # smallest disk: 2.5kg
BARBELL_STEP = 2 * PLATE_MIN                      # smallest symmetric barbell jump = 5kg
DB_TOTAL = sorted({2 * d for d in DUMBBELLS})     # Hevy logs DB lifts as the pair total

def equip(title):
    if "(Dumbbell)" in title: return "db"
    if "(Barbell)" in title: return "bb"
    return "stack"   # machine / cable / landmine — trust the configured increment

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
        return current + steps * BARBELL_STEP          # snapped to 5kg
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
        inc = increment_for(tid, ex.get("notes"))
        title = ex["title"]
        kind = equip(title)

        if tid in HOLD:
            rows.append(("ROW", title, f"{fmt(target)}kg", "managed by feel", "hold (manual)", f"{fmt(target)}kg"))
            continue

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

for rid, r in touched.items():
    payload = {"routine": {"title": r["title"], "notes": r.get("notes"), "exercises": [
        {"exercise_template_id": ex["exercise_template_id"], "superset_id": ex.get("superset_id"),
         "rest_seconds": ex.get("rest_seconds"), "notes": ex.get("notes"),
         "sets": [set_payload(s) for s in ex["sets"]]}
        for ex in r["exercises"]]}}
    st, resp = call("PUT", f"/v1/routines/{rid}", payload)
    ok = isinstance(resp, dict)
    print(f"[{st}] updated {r['title']}" + ("" if ok else f"  ERROR: {str(resp)[:200]}"))
