#!/usr/bin/env python3
"""Rebuild the managed routines to the current design (dry-run by default).

Design (2026-08-17) — a 4-routine upper/lower rotation, cycled in order
(Upper 1 -> Lower 1 -> Upper 2 -> Lower 2), so training 2-3 days in a row
never hits the same muscle groups on consecutive days:

  Upper 1 — flat chest, barbell row, shoulders, arms, abs
  Lower 1 — squat + hamstrings (DB RDL) + quads + rotational core
  Upper 2 — lats/rows, incline chest, side/rear delts, arms, abs
  Lower 2 — hinge day: deadlift, kettlebell swing, back extension, plank

Rules (see CLAUDE.md): no exercise in more than one routine (rowing warm-up
excepted); every loaded exercise works 8-12 reps (timed core excepted); notes
stay short; weights pinned to live values. Progression is MANUAL — each note
carries the increment as guidance, Toni decides when to add weight.

Usage:
    python3 update_routines.py            # dry-run: resolve ids, print the plan
    python3 update_routines.py --apply    # PUT existing routines, POST missing

Template ids for new exercises are resolved by title against
GET /v1/exercise_templates at run time (resolution is always printed).
A routine created by --apply gets its id written to ids.json (commit it) so
later runs update it in place instead of creating duplicates."""
import json, os, sys, urllib.request, urllib.error

APPLY = "--apply" in sys.argv
KEY = open(".env").read().split("=", 1)[1].strip()
BASE = "https://api.hevyapp.com"
HDRS = {"api-key": KEY, "Content-Type": "application/json"}

IDS = {  # routine title -> fixed id (never match live routines by title)
    "Upper 1": "c63a8064-bd5a-439d-b6c6-0808bfbaf8b6",  # was Full Body 1
    "Lower 1": "f2dfd68b-377f-430d-a894-c7cdac854614",  # was Full Body 2
    "Upper 2": "dc6a26fe-2098-4c1c-bff9-9454d7cd1386",  # was Full Body 3
    "Lower 2": None,  # created on first --apply; id is stored in ids.json
}
if os.path.exists("ids.json"):
    IDS.update(json.load(open("ids.json")))

ROW_TID = "0222DB42"  # Rowing Machine — the only exercise allowed everywhere

# New exercises whose Hevy template id we don't know yet: placeholder ->
# acceptable template titles, most specific first. Resolved at run time and
# printed, so a fallback pick is always visible, never silent.
NEW = {
    "NEW:DEADLIFT":    ["Deadlift (Barbell)"],
    "NEW:FACE_PULL":   ["Face Pull", "Face Pull (Cable)"],
    "NEW:HAMMER_CURL": ["Hammer Curl (Dumbbell)"],
    "NEW:KB_CURL":     ["Bicep Curl (Kettlebell)", "Kettlebell Curl",
                        "Bicep Curl (Dumbbell)"],  # last resort: log KB weights under the DB template
    "NEW:KB_SWING":    ["Kettlebell Swing"],
    "NEW:BACK_EXT":    ["Back Extension (Hyperextension)", "Back Extension",
                        "Hyperextension"],
    "NEW:SIDE_PLANK":  ["Side Plank"],
}

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# ---- set builders ----
def row():  # 5 min, 1 km
    return {"type": "normal", "duration_seconds": 300, "distance_meters": 1000,
            "weight_kg": None, "reps": None, "custom_metric": None}

def work(weight):
    return {"type": "normal", "weight_kg": weight, "reps": None, "distance_meters": None,
            "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}

def hold(sec):  # timed set (plank)
    return {"type": "normal", "weight_kg": None, "reps": None, "distance_meters": None,
            "duration_seconds": sec, "custom_metric": None}

def warm(n=1):
    return [{"type": "warmup", "weight_kg": None, "reps": None, "distance_meters": None,
             "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}
            for _ in range(n)]

def ex(tid, title, rest, notes, sets, warmups=0):
    return {"exercise_template_id": tid, "title": title, "superset_id": None,
            "rest_seconds": rest, "notes": notes, "sets": warm(warmups) + sets}

# ---- the four days (weights pinned to live values, 2026-08-17) ----
U1 = {"title": "Upper 1",
 "notes": "Chest, row, shoulders, arms, abs. Row 5 min first. 1-2 reps in reserve. Cycle: U1 > L1 > U2 > L2.",
 "exercises": [
   ex(ROW_TID, "Rowing Machine", 120, "5 min / ~1 km, easy.", [row()]),
   ex("79D0BB3A", "Bench Press (Barbell)", 120, "+2.5kg (1.25/side) once all sets hit 12.", [work(40)]*3, 2),
   ex("55E6546F", "Bent Over Row (Barbell)", 90, "Flat back, pull to the hips. +2.5kg (1.25/side) once all sets hit 12.", [work(45)]*3, 1),
   ex("878CD1D0", "Shoulder Press (Dumbbell)", 90, "Next DBs up (+2kg/hand) once all sets hit 12.", [work(36)]*3, 1),
   ex("78683336", "Chest Fly (Machine)", 60, "+2.5kg once all sets hit 12.", [work(22.5)]*3),
   ex("NEW:KB_CURL", "Bicep Curl (Kettlebell)", 60, "Pair of 12kg bells, no swinging. Next bells up once all sets hit 12.", [work(24)]*3),
   ex("93A552C6", "Triceps Pushdown", 60, "+2kg once all sets hit 12.", [work(27)]*3),
   ex("B2398CD1", "Decline Crunch (Weighted)", 45, "Plate on chest. +2.5kg once all sets hit 12.", [work(12.5)]*3),
 ]}
L1 = {"title": "Lower 1",
 "notes": "Squat day: quads + hamstrings + core. Row 5 min first. 1-2 reps in reserve. Cycle: U1 > L1 > U2 > L2.",
 "exercises": [
   ex(ROW_TID, "Rowing Machine", 120, "5 min / ~1 km, easy.", [row()]),
   ex("D04AC939", "Squat (Barbell)", 120, "Controlled depth. Progress by feel.", [work(60)]*3, 2),
   ex("72CFFAD5", "Romanian Deadlift (Dumbbell)", 90, "Hips back, flat back. Next DBs up (+2kg/hand) once all sets hit 12.", [work(44)]*3),
   ex("75A4F6C4", "Leg Extension (Machine)", 90, "Smooth reps — back off if the knees niggle. +5kg once all sets hit 12.", [work(70)]*3, 1),
   ex("923874CA", "Landmine 180", 45, "8-12 each side. +2.5kg once all sets hit 12.", [work(5)]*3),
   ex("D8911FC4", "Dead Bug", 45, "8-12 each side, slow, low back pressed down.", [work(None)]*3),
 ]}
U2 = {"title": "Upper 2",
 "notes": "Back, incline chest, delts, arms, abs. Row 5 min first. 1-2 reps in reserve. Cycle: U1 > L1 > U2 > L2.",
 "exercises": [
   ex(ROW_TID, "Rowing Machine", 120, "5 min / ~1 km, easy.", [row()]),
   ex("6A6C31A5", "Lat Pulldown (Cable)", 90, "+2kg once all sets hit 12.", [work(52)]*3, 1),
   ex("07B38369", "Incline Bench Press (Dumbbell)", 90, "Next DBs up (+2kg/hand) once all sets hit 12.", [work(36)]*3, 1),
   ex("0393F233", "Seated Cable Row - V Grip", 90, "+2kg once all sets hit 12.", [work(42)]*3),
   ex("422B08F1", "Lateral Raise (Dumbbell)", 45, "Strict, lead with the elbows. Back to 12kg if 16 is too big a jump.", [work(16)]*3),
   ex("NEW:FACE_PULL", "Face Pull", 45, "Stack starts at 25 — slow and strict, thumbs back, squeeze the rear delts. +2kg once all sets hit 12.", [work(25)]*3),
   ex("NEW:HAMMER_CURL", "Hammer Curl (Dumbbell)", 60, "Neutral grip, no swinging. Next DBs up (+2kg/hand) once all sets hit 12.", [work(20)]*3),
   ex("09C9F635", "Lying Leg Raise", 45, "Slow lower, no swinging.", [work(None)]*3),
 ]}
L2 = {"title": "Lower 2",
 "notes": "Hinge day: deadlift, swings, back extension, core. Row 5 min first. 1-2 reps in reserve. Cycle: U1 > L1 > U2 > L2.",
 "exercises": [
   ex(ROW_TID, "Rowing Machine", 120, "5 min / ~1 km, easy.", [row()]),
   ex("NEW:DEADLIFT", "Deadlift (Barbell)", 120, "Flat back, bar close, reset each rep. Progress by feel.", [work(70)]*3, 2),
   ex("NEW:KB_SWING", "Kettlebell Swing", 60, "Snap the hips, arms just hold on. Next bell up once all sets hit 12.", [work(16)]*3),
   ex("NEW:BACK_EXT", "Back Extension", 60, "Squeeze glutes and hams at the top, don't hyperextend. Hold a 2.5kg plate once all sets hit 12.", [work(None)]*3),
   ex("C6C9B8A0", "Plank", 45, "Glutes tight, no sagging. +15s once 45s is easy.", [hold(45)]*3),
   ex("NEW:SIDE_PLANK", "Side Plank", 45, "30s each side, hips high and stacked. +15s once 30s is easy.", [hold(30)]*3),
 ]}

ROUTINES = [U1, L1, U2, L2]

# ---- resolve template ids for the NEW placeholders ----
def fetch_templates():
    titles, page = {}, 1
    while True:
        st, d = call("GET", f"/v1/exercise_templates?page={page}&pageSize=100")
        if not isinstance(d, dict) or not d.get("exercise_templates"):
            break
        for t in d["exercise_templates"]:
            titles[t["title"]] = t["id"]
        if page >= int(d.get("page_count") or page):
            break
        page += 1
    return titles

def resolve():
    titles = fetch_templates()
    if not titles:
        sys.exit("could not fetch exercise templates — check the API key")
    lower = {t.lower(): (t, i) for t, i in titles.items()}
    resolved, missing = {}, []
    for key, cands in NEW.items():
        hit = next((lower[c.lower()] for c in cands if c.lower() in lower), None)
        if hit:
            resolved[key] = hit  # (canonical title, id)
            print(f"  {key:17s} -> {hit[0]}  ({hit[1]})")
        else:
            words = [w for w in cands[0].replace("(", " ").replace(")", " ").split() if len(w) > 3]
            near = [t for t in titles if any(w.lower() in t.lower() for w in words)][:12]
            missing.append((key, cands, near))
    for key, cands, near in missing:
        print(f"\n{key}: none of {cands} found. Near matches:")
        for t in near:
            print(f"    {t}  ({titles[t]})")
    if missing:
        sys.exit("unresolved exercises — pick from the near matches and update NEW")
    return resolved

print("Resolving new exercise templates:")
RESOLVED = resolve()
for r in ROUTINES:
    for e in r["exercises"]:
        if e["exercise_template_id"].startswith("NEW:"):
            title, tid = RESOLVED[e["exercise_template_id"]]
            e["exercise_template_id"], e["title"] = tid, title

# rule: no exercise may appear in more than one routine (rowing excepted)
seen = {}
for r in ROUTINES:
    for e in r["exercises"]:
        tid = e["exercise_template_id"]
        if tid == ROW_TID:
            continue
        assert tid not in seen, f"duplicate exercise {tid} in {seen[tid]} and {r['title']}"
        seen[tid] = r["title"]

# ---- print the plan ----
def fmt(w):
    if w is None:
        return "bw"
    return f"{int(w) if float(w).is_integer() else w}kg"

for r in ROUTINES:
    rid = IDS.get(r["title"])
    print(f"\n== {r['title']} ==  ({'update ' + rid if rid else 'CREATE new'})")
    for e in r["exercises"]:
        n_work = sum(1 for s in e["sets"] if s["type"] == "normal")
        n_warm = sum(1 for s in e["sets"] if s["type"] == "warmup")
        first = next(s for s in e["sets"] if s["type"] == "normal")
        if e["exercise_template_id"] == ROW_TID:
            desc = "5 min row"
        elif first.get("duration_seconds"):
            desc = f"{n_work}x{first['duration_seconds']}s hold"
        else:
            desc = f"{n_work}x8-12 @ {fmt(first['weight_kg'])}"
        wu = f" (+{n_warm} warmup)" if n_warm else ""
        print(f"  {e['title']:32s} {desc}{wu}")

if not APPLY:
    print("\nDry-run. Re-run with --apply to write these to Hevy.")
    sys.exit(0)

# ---- apply ----
def payload(r):
    return {"routine": {"title": r["title"], "notes": r["notes"], "exercises": [
        {k: v for k, v in e.items() if k != "title"} for e in r["exercises"]]}}

def folder_of(rid):
    for page in range(1, 6):
        st, d = call("GET", f"/v1/routines?page={page}&pageSize=10")
        if not isinstance(d, dict) or not d.get("routines"):
            return None
        for rt in d["routines"]:
            if rt["id"] == rid:
                return rt.get("folder_id")
    return None

print()
created = {}
for r in ROUTINES:
    rid = IDS.get(r["title"])
    if rid:
        st, resp = call("PUT", f"/v1/routines/{rid}", payload(r))
        ok = isinstance(resp, dict)
        print(f"[{st}] updated {r['title']} ({len(r['exercises'])} ex)" + ("" if ok else f"  ERROR: {str(resp)[:200]}"))
    else:
        body = payload(r)
        body["routine"]["folder_id"] = folder_of(IDS["Upper 1"])
        st, resp = call("POST", "/v1/routines", body)
        if isinstance(resp, dict):
            rt = resp.get("routine", resp)
            new_id = rt[0]["id"] if isinstance(rt, list) else rt.get("id")
            created[r["title"]] = new_id
            print(f"[{st}] created {r['title']} -> id {new_id}")
        else:
            print(f"[{st}] create {r['title']} FAILED: {str(resp)[:200]}")

if created:
    IDS.update(created)
    json.dump({t: i for t, i in IDS.items() if i}, open("ids.json", "w"), indent=1)
    print("ids.json updated — commit it so future runs update instead of re-creating.")
