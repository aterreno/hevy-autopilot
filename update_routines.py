#!/usr/bin/env python3
"""Rebuild the 3 v2 routines to match current live state (idempotent).

Reflects: leg press retired -> Hip Thrust (FB A,
glute/quad) + Leg Extension (FB C, quad), both low-impact; weights at their current
progressed values as of 2026-06-23. Re-running this PUTs the routines as written, so
keep the weights here in sync with progression.py --apply (or it will regress them)."""
import json, urllib.request, urllib.error

KEY = open(".env").read().split("=", 1)[1].strip()
BASE = "https://api.hevyapp.com"
HDRS = {"api-key": KEY, "Content-Type": "application/json"}
IDS = {  # routine ids created earlier
    "A": "c63a8064-bd5a-439d-b6c6-0808bfbaf8b6",
    "B": "f2dfd68b-377f-430d-a894-c7cdac854614",
    "C": "dc6a26fe-2098-4c1c-bff9-9454d7cd1386",
}

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

def work(weight, lo, hi):
    return {"type": "normal", "weight_kg": weight, "reps": None, "distance_meters": None,
            "duration_seconds": None, "custom_metric": None, "rep_range": {"start": lo, "end": hi}}

def warm(n=1):
    return [{"type": "warmup", "weight_kg": None, "reps": None, "distance_meters": None,
             "duration_seconds": None, "custom_metric": None, "rep_range": {"start": 8, "end": 12}}
            for _ in range(n)]

def prog(w, top, inc):
    return (f"Start {w}kg. Add +{inc}kg ONLY after you hit {top} reps on all working sets; "
            f"otherwise keep the same weight next time. Targets are fixed on purpose — "
            f"ignore any auto-suggested jump.")

ROWNOTE = "5 min / ~1 km, easy–moderate. Your only gym cardio."
HIP = ("Replaces leg press — LOW-IMPACT. Feet flat, drive through your HEELS. "
       "Ribs down, squeeze glutes hard at top, 1s pause. "
       "Machine preferred; if none, barbell/Smith across a bench. ")
EXT = ("Replaces leg press — LOW-IMPACT (knee-only isolation). "
       "Controlled tempo, squeeze 1s at top, no swinging or kicking. Higher reps to spare the knee. ")

def ex(tid, rest, notes, sets, warmups=0):
    return {"exercise_template_id": tid, "superset_id": None, "rest_seconds": rest,
            "notes": notes, "sets": warm(warmups) + sets}

A = {"title": "FB A · Legs/Push (v2)",
 "notes": "Full-body A. 5-min row → glutes (hip thrust) → chest → back → ham → biceps → abs. "
          "Cut + muscle retention: keep 1–2 reps in reserve, eat your protein. "
          "Low-impact: leg press retired, no calf raises, no deep squats.",
 "exercises": [
   ex("0222DB42",120,ROWNOTE,[row()]),
   ex("68CE0B9B",120,HIP+prog(60,12,5),[work(60,8,12)]*3,1),
   ex("79D0BB3A",120,prog(37.5,12,2.5),[work(37.5,8,12)]*3,2),
   ex("6A6C31A5",90,prog(47.5,12,2.5),[work(47.5,8,12)]*3,1),
   ex("11A123F3",75,prog(32.5,15,2.5),[work(32.5,10,15)]*3),
   ex("37FCC2BB",60,prog(28,15,2),[work(28,10,15)]*3),
   ex("09C9F635",45,"Lying leg raise — bodyweight, slow lower, no swinging. Lower abs.",
      [work(None,12,20)]*3),
 ]}
B = {"title": "FB B · Hinge/Pull (v2)",
 "notes": "Full-body B. 5-min row → hip hinge → row → shoulders → side delts → abs. "
          "Romanian deadlift is low-impact. Stop each set 1–2 reps before failure.",
 "exercises": [
   ex("0222DB42",120,ROWNOTE,[row()]),
   ex("2B4B7310",120,"Hips back, soft knees, bar close, flat back. Stop when the low back rounds. "+prog(60,12,2.5),
      [work(60,8,12)]*3,2),
   ex("55E6546F",90,prog(52.5,12,2.5),[work(52.5,8,12)]*3,1),
   ex("878CD1D0",90,prog(32,12,2),[work(32,8,12)]*3,1),
   ex("422B08F1",45,"Light and clean — lead with the elbows, no swinging. Drop weight if you can't hit 12 strict.",
      [work(20,12,20)]*3),
   ex("23A48484",45,prog(35,20,2.5),[work(35,12,20)]*3),
 ]}
C = {"title": "FB C · Legs/Upper (v2)",
 "notes": "Full-body C. 5-min row → quad (leg extension) → incline chest → back → chest fly → triceps. "
          "Second quad day, low-impact (leg press retired). Keep it controlled.",
 "exercises": [
   ex("0222DB42",120,ROWNOTE,[row()]),
   ex("75A4F6C4",90,EXT+prog(35,15,5),[work(35,12,15)]*3,1),
   ex("07B38369",90,prog(32,12,2),[work(32,8,12)]*3,1),
   ex("D7D7FCCE",90,prog(50,12,2.5),[work(50,8,12)]*3,1),
   ex("78683336",60,prog(20,15,2.5),[work(20,12,15)]*3),
   ex("93A552C6",60,prog(25,15,2.5),[work(25,12,15)]*3),
 ]}

for key, r in (("A",A),("B",B),("C",C)):
    st, resp = call("PUT", f"/v1/routines/{IDS[key]}", {"routine": r})
    ok = isinstance(resp, dict)
    print(f"[{st}] {r['title']} ({len(r['exercises'])} ex)" + ("" if ok else f"  ERROR: {str(resp)[:200]}"))
