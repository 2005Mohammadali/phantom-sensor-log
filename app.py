import threading, time
from flask import Flask, jsonify, send_from_directory
import db, narrator
from config import *
from collector import Collector
from detector import Detector

app = Flask(__name__, static_folder="static")
col, det = Collector(), Detector()
state = {"status": "starting"}
busy = threading.Lock()          # only one Gemma call at a time
last_row = None
last_haunt = 0
last_epitaph = 0
recent_names = {}

def haunt(row, score, facts):
    with busy:
        tier = det.tier(score)
        tale = narrator.tell(facts, tier)
        db.run("INSERT INTO hauntings(ts,tier,facts,tale) VALUES(?,?,?,?)",
               (row["ts"], tier, facts, tale))

def bury(d):
    with busy:
        ep = narrator.epitaph(d["name"], d["lifespan_s"], d["rss_mb"])
        db.run("INSERT INTO ofrenda(ts,name,lifespan_s,rss_mb,epitaph) VALUES(?,?,?,?,?)",
               (time.time(), d["name"], d["lifespan_s"], d["rss_mb"], ep))

def may_haunt(score):
    since = time.time() - last_haunt
    if busy.locked():
        return False
    n = db.q("SELECT COUNT(*) c FROM hauntings WHERE ts>?", (time.time() - 86400,))[0]["c"]
    if n >= MAX_HAUNTS_PER_DAY:
        return False
    return since > COOLDOWN or (score >= BANSHEE and since > ESCALATE_COOLDOWN)

def loop():
    global last_row, last_haunt, last_epitaph
    ticks = 0
    while True:
        try:
            row, deaths = col.tick()
            row["score"] = 0.0
            if not det.ready:
                det.add_baseline(row)
                state["status"] = f"learning what normal feels like ({len(det.rows)}/{BASELINE_SAMPLES})"
            else:
                if det.med is None:
                    det.fit()
                row["score"], facts = det.score(row)
                state["status"] = "watching in the dark"
                if row["score"] >= WHISPER and may_haunt(row["score"]):
                    last_haunt = time.time()
                    threading.Thread(target=haunt, args=(row, row["score"], facts), daemon=True).start()
            last_row = row
            db.run("INSERT INTO samples VALUES(?,?,?,?,?,?,?)",
                   (row["ts"], row["cpu"], row["ram"], row["procs"], row["spawns"], row["net_kb"], row["score"]))

            now = time.time()
            for d in deaths:
                if now - last_epitaph < EPITAPH_COOLDOWN or busy.locked():
                    break
                if now - recent_names.get(d["name"], 0) < SAME_NAME_COOLDOWN:
                    continue
                recent_names[d["name"]] = now
                last_epitaph = now
                threading.Thread(target=bury, args=(d,), daemon=True).start()
                break

            ticks += 1
            if ticks % 360 == 0:   # roughly hourly
                db.run("DELETE FROM samples WHERE ts<?", (time.time() - KEEP_SAMPLE_HOURS * 3600,))
        except Exception as e:
            print("loop error:", e)
        time.sleep(SAMPLE_SECONDS)

@app.get("/")
def index():
    return send_from_directory("static", "index.html")

@app.get("/api/state")
def api_state():
    day = time.time() - 86400
    return jsonify(
        status=state["status"],
        thinking=busy.locked(),
        samples=db.q("SELECT ts,cpu,net_kb,score FROM samples ORDER BY ts DESC LIMIT 90")[::-1],
        hauntings=db.q("SELECT * FROM hauntings ORDER BY ts DESC LIMIT 40"),
        ofrenda=db.q("SELECT * FROM ofrenda ORDER BY ts DESC LIMIT 40"),
        counts=db.q("SELECT tier, COUNT(*) c FROM hauntings WHERE ts>? GROUP BY tier", (day,)))

@app.post("/api/summon")
def summon():
    row = dict(last_row or {"cpu": 10, "ram": 40, "procs": 200, "spawns": 0, "net_kb": 5})
    row.update(ts=time.time(), cpu=98, spawns=14, net_kb=4800)
    if det.med is not None:
        score, facts = det.score(row)
    else:
        score, facts = 25, "CPU load %: 98 (usually 8); new processes just spawned: 14; outbound network KB/s: 4800 (usually 5)"
    threading.Thread(target=haunt, args=(row, score, facts), daemon=True).start()
    return jsonify(ok=True)

@app.get("/api/dawn")
def api_dawn():
    hs = db.q("SELECT tier,facts FROM hauntings WHERE ts>?", (time.time() - 12 * 3600,))
    if not hs:
        return jsonify(counts={}, tale="The night was quiet. Almost suspiciously quiet.")
    counts = {}
    for h in hs:
        counts[h["tier"]] = counts.get(h["tier"], 0) + 1
    with busy:
        tale = narrator.dawn(counts, [h["facts"] for h in hs[:5]])
    return jsonify(counts=counts, tale=tale)

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="127.0.0.1", port=5000, threaded=True)