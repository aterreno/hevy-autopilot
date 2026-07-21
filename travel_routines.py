#!/usr/bin/env python3
"""Create 2 temporary no-gym routines (bodyweight + resistance band) in Hevy.

Context (2026-07-21): Toni is away for two weeks and may not have a gym.
  - Bodyweight + a packed resistance band only.
  - Legs stay squat + hinge (no split squats / lunges — knees, asked 2026-07-21).
  - 8-12 reps everywhere; band progression = shorten the band / step further out.
  - No exercise here appears in Full Body 1/2/3, and none in both travel days.
  - progression.py never touches these (it filters by the fixed Full Body IDs).

One-off like build_routines.py: run once, note the printed IDs, delete the
routines (and folder) when back home.
"""
import json, urllib.request, urllib.error

KEY = open(".env").read().split("=", 1)[1].strip()
BASE = "https://api.hevyapp.com"
HDRS = {"api-key": KEY, "Content-Type": "application/json"}

def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers=HDRS, method=method)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

def work():  # bodyweight/band: no logged weight, 8-12 reps
    return {"type": "normal", "weight_kg": None, "reps": None, "distance_meters": None,
            "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}

def hold(sec):  # timed set (plank)
    return {"type": "normal", "weight_kg": None, "reps": None, "distance_meters": None,
            "duration_seconds": sec, "custom_metric": None}

def ex(tid, rest, notes, sets):
    return {"exercise_template_id": tid, "superset_id": None, "rest_seconds": rest,
            "notes": notes, "sets": sets}

T1 = {"title": "Travel 1",
 "notes": "No-gym day. Warm up 2-3 min easy first. Squat, push, row, side delts, biceps, abs. Keep 1-2 reps in reserve.",
 "exercises": [
   ex("9694DA61",90,"Controlled depth, 3s down. Hold the band or a loaded backpack once all sets hit 12.",
      [work()]*3),                                          # Squat (Bodyweight)
   ex("392887AA",90,"Full range, tight body. Elevate feet or wear the backpack once all sets hit 12.",
      [work()]*3),                                          # Push Up
   ex("EA820646",90,"Stand on the band, flat back. Shorten the band once all sets hit 12.",
      [work()]*3),                                          # Bent Over Row (Band)
   ex("DF200976",45,"Strict, lead with the elbows. Shorten the band once all sets hit 12.",
      [work()]*3),                                          # Lateral Raise (Band)
   ex("1D4B3D6B",60,"No swinging. Shorten the band once all sets hit 12.",
      [work()]*3),                                          # Hammer Curl (Band)
   ex("C6C9B8A0",45,"Glutes tight, no sagging. +15s once 45s is easy.",
      [hold(45)]*3),                                        # Plank
 ]}
T2 = {"title": "Travel 2",
 "notes": "No-gym day. Warm up 2-3 min easy first. Hinge, shoulders, back, rear delts, triceps, abs. Keep 1-2 reps in reserve.",
 "exercises": [
   ex("99507114",90,"Stand on the band, hips back, flat back. Shorten or double the band once all sets hit 12.",
      [work()]*3),                                          # Deadlift (Band) — the hinge slot
   ex("0EFE8162",90,"Hips high, head between the hands. Raise the feet once all sets hit 12.",
      [work()]*3),                                          # Pike Pushup — shoulders
   ex("D2FE7B2E",90,"Anchor high (door hinge/hook). Shorten the band once all sets hit 12.",
      [work()]*3),                                          # Lat Pulldown (Band)
   ex("E8D86EE8",45,"Arms straight, squeeze the blades. Grip the band narrower once all sets hit 12.",
      [work()]*3),                                          # Band Pullaparts — rear delts
   ex("6575F52D",60,"Elbows tucked; from the knees if needed. Elevate feet once all sets hit 12.",
      [work()]*3),                                          # Diamond Push Up — triceps
   ex("D8911FC4",45,"8-12 each side, slow, low back pressed down.",
      [work()]*3),                                          # Dead Bug
 ]}

ROUTINES = (T1, T2)

# no exercise in both travel days (and none of these are in Full Body 1/2/3)
seen = {}
for r in ROUTINES:
    for e in r["exercises"]:
        tid = e["exercise_template_id"]
        assert tid not in seen, f"duplicate exercise {tid} in {seen[tid]} and {r['title']}"
        seen[tid] = r["title"]

st, folder = call("POST", "/v1/routine_folders", {"routine_folder": {"title": "Travel"}})
fid = folder.get("routine_folder", folder).get("id") if isinstance(folder, dict) else None
print(f"[{st}] folder Travel -> id {fid}")

for r in ROUTINES:
    payload = {"routine": {"title": r["title"], "folder_id": fid, "notes": r["notes"], "exercises": r["exercises"]}}
    st, resp = call("POST", "/v1/routines", payload)
    if isinstance(resp, dict):
        rt = resp.get("routine", resp)
        rid = rt[0]["id"] if isinstance(rt, list) else rt.get("id")
        print(f"  [{st}] {r['title']} -> id {rid}  ({len(r['exercises'])} exercises)")
    else:
        print(f"  [{st}] {r['title']} -> ERROR: {resp[:300]}")
