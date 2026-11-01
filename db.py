import sqlite3, threading
from config import DB_PATH

_lock = threading.Lock()
_c = sqlite3.connect(DB_PATH, check_same_thread=False)
_c.executescript("""
CREATE TABLE IF NOT EXISTS samples(ts REAL, cpu REAL, ram REAL, procs INTEGER, spawns INTEGER, net_kb REAL, score REAL);
CREATE TABLE IF NOT EXISTS hauntings(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, tier TEXT, facts TEXT, tale TEXT);
CREATE TABLE IF NOT EXISTS ofrenda(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, name TEXT, lifespan_s REAL, rss_mb REAL, epitaph TEXT);
""")

def run(sql, args=()):
    with _lock:
        _c.execute(sql, args); _c.commit()

def q(sql, args=()):
    with _lock:
        cur = _c.execute(sql, args)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]