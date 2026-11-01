import multiprocessing as mp, subprocess, sys, time

def spin(seconds):
    end = time.time() + seconds
    while time.time() < end:
        pass

if __name__ == "__main__":
    mem = b"x" * (600 * 1024 * 1024)       # grab ~600 MB of RAM
    # a doomed process that will give you an ofrenda card when it dies
    subprocess.Popen([sys.executable, "-c", "x=b'a'*80_000_000; import time; time.sleep(25)"])
    # burst of short-lived processes
    for _ in range(12):
        subprocess.Popen([sys.executable, "-c", "import time; time.sleep(4)"])
    with mp.Pool(mp.cpu_count()) as p:      # max out every core for 25s
        p.map(spin, [25] * mp.cpu_count())
    print("The haunting subsides.")