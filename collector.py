import time, psutil
from config import MIN_LIFESPAN, MIN_RSS_MB

class Collector:
    def __init__(self):
        self.last_net = psutil.net_io_counters()
        self.last_t = time.time()
        self.known = None            # {(pid, create_time): (name, rss_bytes)}
        psutil.cpu_percent(None)     # first call is always 0, so prime it

    def _scan(self):
        cur = {}
        for p in psutil.process_iter(["pid", "name", "create_time", "memory_info"]):
            try:
                i = p.info
                rss = i["memory_info"].rss if i["memory_info"] else 0
                cur[(i["pid"], i["create_time"])] = (i["name"] or "unknown", rss)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return cur

    def tick(self):
        now = time.time()
        net = psutil.net_io_counters()
        dt = max(now - self.last_t, 0.001)
        net_kb = (net.bytes_sent - self.last_net.bytes_sent) / 1024 / dt
        self.last_net, self.last_t = net, now

        cur = self._scan()
        spawns, deaths = 0, []
        if self.known is not None:
            spawns = len(set(cur) - set(self.known))
            for key in set(self.known) - set(cur):
                name, rss = self.known[key]
                life = now - key[1]
                if life >= MIN_LIFESPAN and rss / 1048576 >= MIN_RSS_MB:
                    deaths.append({"name": name, "lifespan_s": life, "rss_mb": rss / 1048576})
        self.known = cur

        row = {"ts": now, "cpu": psutil.cpu_percent(None),
               "ram": psutil.virtual_memory().percent,
               "procs": len(cur), "spawns": spawns, "net_kb": net_kb}
        return row, deaths