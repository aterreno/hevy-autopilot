#!/usr/bin/env python3
"""Rebuild the 3 routines to the current design (idempotent).

Design rules (2026-07-17):
  - Titles are "Full Body 1/2/3" — no version suffix; routines are identified
    by the fixed IDS below, not by title.
  - No exercise appears in more than one routine (rowing warm-up excepted).
  - Every exercise works 8-12 reps.
  - Notes are short: cue + progression rule only.
  - Equipment (see CLAUDE.md): cables +2kg add-ons; disks are 2.5/5/10/20 per
    side so barbell +5kg and landmine +2.5kg; dumbbells grow 2kg per hand.
  - No loaded knee-flexion/extension work except the leg extension (monitored):
    seated leg curl retired 2026-07-17 (knees) -> DB Romanian Deadlift.

Weights are pinned to live values as of 2026-07-17. Re-running PUTs the routines
as written, so keep them in sync with progression.py --apply (or it will regress
them)."""
import json, urllib.request, urllib.error

KEY = open(".env").read().split("=", 1)[1].strip()
BASE = "https://api.hevyapp.com"
HDRS = {"api-key": KEY, "Content-Type": "application/json"}
IDS = {  # fixed routine ids (created once by build_routines.py)
    "1": "c63a8064-bd5a-439d-b6c6-0808bfbaf8b6",
    "2": "f2dfd68b-377f-430d-a894-c7cdac854614",
    "3": "dc6a26fe-2098-4c1c-bff9-9454d7cd1386",
}
ROW_TID = "0222DB42"  # Rowing Machine — the only exercise allowed in all 3

def call(method, path, body):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def row():  # 5 min, 1 km
    return {"type": "normal", "duration_seconds": 300, "distance_meters": 1000,
            "weight_kg": None, "reps": None, "custom_metric": None}

def work(weight):
    return {"type": "normal", "weight_kg": weight, "reps": None, "distance_meters": None,
            "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}

def warm(n=1):
    return [{"type": "warmup", "weight_kg": None, "reps": None, "distance_meters": None,
             "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}
            for _ in range(n)]

def ex(tid, rest, notes, sets, warmups=0):
    return {"exercise_template_id": tid, "superset_id": None, "rest_seconds": rest,
            "notes": notes, "sets": warm(warmups) + sets}

R1 = {"title": "Full Body 1",
 "notes": "Row 5 min. Quads, chest, back, hamstrings, biceps, abs. Keep 1-2 reps in reserve.",
 "exercises": [
   ex("0222DB42",120,"5 min / ~1 km, easy.",[row()]),
   ex("75A4F6C4",90,"Smooth reps — back off if the knees niggle. +5kg once all sets hit 12.",
      [work(45)]*3,1),                                     # Leg Extension (Machine)
   ex("79D0BB3A",120,"+5kg (2.5/side) once all sets hit 12.",[work(40)]*3,2),   # Bench Press (Barbell)
   ex("6A6C31A5",90,"+2kg once all sets hit 12.",[work(52)]*3,1),               # Lat Pulldown (Cable)
   ex("72CFFAD5",90,"Hips back, flat back. Next DBs up (+2kg/hand) once all sets hit 12.",
      [work(40)]*3),                                       # Romanian Deadlift (DB) — leg curl retired (knees)
   ex("37FCC2BB",60,"Next DBs up (+2kg/hand) once all sets hit 12.",[work(28)]*3),  # Bicep Curl (DB)
   ex("09C9F635",45,"Slow lower, no swinging.",[work(None)]*3),                 # Lying Leg Raise
 ]}
R2 = {"title": "Full Body 2",
 "notes": "Row 5 min. Hinge, row, shoulders, side delts, abs. Keep 1-2 reps in reserve.",
 "exercises": [
   ex("0222DB42",120,"5 min / ~1 km, easy.",[row()]),
   ex("2B4B7310",120,"Hips back, flat back. +5kg (2.5/side) once all sets hit 12.",
      [work(65)]*3,2),                                     # Romanian Deadlift (Barbell)
   ex("55E6546F",90,"+5kg (2.5/side) once all sets hit 12.",[work(55)]*3,1),    # Bent Over Row (Barbell)
   ex("878CD1D0",90,"Next DBs up (+2kg/hand) once all sets hit 12.",[work(32)]*3,1),  # Shoulder Press (DB)
   ex("422B08F1",45,"Strict, lead with the elbows. Next DBs up once all sets hit 12.",
      [work(8)]*3),                                        # Lateral Raise (DB) — 4kg per hand
   ex("B2398CD1",45,"Plate on chest. +2.5kg once all sets hit 12.",[work(5)]*3),  # Decline Crunch (Weighted)
 ]}
R3 = {"title": "Full Body 3",
 "notes": "Row 5 min. Squat, incline chest, back, fly, triceps. Keep 1-2 reps in reserve.",
 "exercises": [
   ex("0222DB42",120,"5 min / ~1 km, easy.",[row()]),
   ex("D04AC939",120,"Controlled depth. Progress by feel — never auto-adjusted.",
      [work(60)]*3,2),                                     # Squat (Barbell)
   ex("07B38369",90,"Next DBs up (+2kg/hand) once all sets hit 12.",[work(32)]*3,1),  # Incline Bench Press (DB)
   ex("D7D7FCCE",90,"+2.5kg once all sets hit 12.",[work(45)]*3,1),             # Landmine Row
   ex("78683336",60,"+2.5kg once all sets hit 12.",[work(17.5)]*3),             # Chest Fly (Machine)
   ex("93A552C6",60,"+2kg once all sets hit 12.",[work(25)]*3),                 # Triceps Pushdown
 ]}

ROUTINES = (("1", R1), ("2", R2), ("3", R3))

# rule: no exercise may appear in more than one routine (rowing excepted)
seen = {}
for key, r in ROUTINES:
    for e in r["exercises"]:
        tid = e["exercise_template_id"]
        if tid == ROW_TID:
            continue
        assert tid not in seen, f"duplicate exercise {tid} in Full Body {seen[tid]} and Full Body {key}"
        seen[tid] = key

for key, r in ROUTINES:
    st, resp = call("PUT", f"/v1/routines/{IDS[key]}", {"routine": r})
    ok = isinstance(resp, dict)
    print(f"[{st}] {r['title']} ({len(r['exercises'])} ex)" + ("" if ok else f"  ERROR: {str(resp)[:200]}"))
