#!/usr/bin/env python3
"""Build 3 low-impact, cut+build full-body routines in Hevy via the API.
Re-runnable: creates a folder + 3 routines alongside the user's existing ones.
Weights are pinned to the user's last-logged working loads so Hevy stops guessing.
"""
import json, os, urllib.request, urllib.error

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

# ---- set builders ----
def row(sec=600):
    return {"type": "normal", "duration_seconds": sec, "weight_kg": None, "reps": None,
            "distance_meters": None, "custom_metric": None}

def work(weight, lo, hi):
    return {"type": "normal", "weight_kg": weight, "reps": None, "distance_meters": None,
            "duration_seconds": None, "custom_metric": None, "rep_range": {"start": lo, "end": hi}}

def warm(n=1):
    return [{"type": "warmup", "weight_kg": None, "reps": None, "distance_meters": None,
             "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}
            for _ in range(n)]

def prog(w, top, inc):
    return (f"Start {w}kg. Add +{inc}kg ONLY after you hit {top} reps on all working sets; "
            f"otherwise keep the same weight next time.")

LOWIMPACT = "Feet high on platform; stop short of a deep bottom — keep the range controlled. " \
            "If anything pinches, reduce range before adding weight. "

def ex(tid, title, sets, rest, notes, warmups=0):
    return {"exercise_template_id": tid, "superset_id": None, "rest_seconds": rest,
            "notes": notes, "sets": warm(warmups) + sets}

# ---- the three days ----
A = {
 "title": "FB A · Legs/Push (v2)",
 "notes": "Full-body A. 10-min row → quad → chest → back → ham → biceps → abs. "
          "Cut + muscle retention: keep 1–2 reps in reserve, eat your protein, "
          "rowing is the only cardio. Low-impact: no calf raises, no deep squats.",
 "exercises": [
   ex("0222DB42","Rowing Machine",[row(600)],120,"10 min easy–moderate. Your only gym cardio."),
   ex("C7973E0E","Leg Press (Machine)",[work(80,8,12)]*3,120, LOWIMPACT+prog(80,12,5),1),
   ex("79D0BB3A","Bench Press (Barbell)",[work(35,8,12)]*3,120, prog(35,12,2.5),2),
   ex("6A6C31A5","Lat Pulldown (Cable)",[work(45,8,12)]*3,90, prog(45,12,2.5),1),
   ex("11A123F3","Seated Leg Curl (Machine)",[work(30,10,15)]*3,75, prog(30,15,2.5)),
   ex("37BC31A5".replace("37BC31A5","37FCC2BB"),"Bicep Curl (Dumbbell)",[work(24,10,15)]*3,60, prog(24,15,2)),
   ex("EB43ADD4","Crunch (Machine)",[work(None,12,20)]*3,45,"Slow, full crunch. Add light load when 20 reps is easy."),
 ]}
B = {
 "title": "FB B · Hinge/Pull (v2)",
 "notes": "Full-body B. 10-min row → hip hinge → row → shoulders → side delts → abs. "
          "Romanian deadlift is a low-impact way to train legs hard. "
          "Stop each set 1–2 reps before failure.",
 "exercises": [
   ex("0222DB42","Rowing Machine",[row(600)],120,"10 min easy–moderate."),
   ex("2B4B7310","Romanian Deadlift (Barbell)",[work(60,8,12)]*3,120,
      "Hips back, soft knees, bar close, flat back. Stop the set when the low back starts to round. "+prog(60,12,2.5),2),
   ex("55E6546F","Bent Over Row (Barbell)",[work(50,8,12)]*3,90, prog(50,12,2.5),1),
   ex("878CD1D0","Shoulder Press (Dumbbell)",[work(32,8,12)]*3,90, prog(32,12,2),1),
   ex("422B08F1","Lateral Raise (Dumbbell)",[work(20,12,20)]*3,45,
      "Light and clean — lead with the elbows, no swinging. Drop the weight if you can't hit 12 strict."),
   ex("23A48484","Cable Crunch",[work(35,12,20)]*3,45, prog(35,20,2.5)),
 ]}
C = {
 "title": "FB C · Legs/Upper (v2)",
 "notes": "Full-body C. 10-min row → quad → incline chest → back → chest fly → triceps. "
          "Second quad exposure of the week via leg press (controlled range, no deep bottom). Keep it smooth.",
 "exercises": [
   ex("0222DB42","Rowing Machine",[row(600)],120,"10 min easy–moderate."),
   ex("C7973E0E","Leg Press (Machine)",[work(80,8,12)]*3,120, LOWIMPACT+prog(80,12,5),1),
   ex("07B38369","Incline Bench Press (Dumbbell)",[work(32,8,12)]*3,90, prog(32,12,2),1),
   ex("D7D7FCCE","Landmine Row",[work(50,8,12)]*3,90, prog(50,12,2.5),1),
   ex("78683336","Chest Fly (Machine)",[work(20,12,15)]*3,60, prog(20,15,2.5)),
   ex("93A552C6","Triceps Pushdown",[work(25,12,15)]*3,60, prog(25,15,2.5)),
 ]}

# ---- create folder ----
st, folder = call("POST", "/v1/routine_folders", {"routine_folder": {"title": "Cut+Build · Low-Impact 🚣"}})
print("folder:", st, folder if isinstance(folder, str) else folder.get("routine_folder", folder))
fid = None
if isinstance(folder, dict):
    rf = folder.get("routine_folder", folder)
    fid = rf.get("id")
print("folder_id:", fid)

# ---- create routines ----
for r in (A, B, C):
    payload = {"routine": {"title": r["title"], "folder_id": fid, "notes": r["notes"], "exercises": r["exercises"]}}
    st, resp = call("POST", "/v1/routines", payload)
    if isinstance(resp, dict):
        rt = resp.get("routine", resp)
        rid = rt[0]["id"] if isinstance(rt, list) else rt.get("id")
        print(f"  [{st}] {r['title']}  -> id {rid}  ({len(r['exercises'])} exercises)")
    else:
        print(f"  [{st}] {r['title']}  -> ERROR: {resp[:300]}")
