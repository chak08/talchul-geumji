# -*- coding: utf-8 -*-
import psutil
import time

LOL_PROCESSES = [
    "LeagueClient.exe",
    "League of Legends.exe",
    "LeagueClientUx.exe",
]

def find_lol():
    found = []
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] in LOL_PROCESSES:
                found.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found

print("[탈출금지] 롤 감지 시작... (Ctrl+C 종료)")
print()

was_running = False

while True:
    lol_procs = find_lol()

    if lol_procs and not was_running:
        print("[감지] 롤 실행됨!")
        for p in lol_procs:
            print(f"  -> {p['name']} (PID: {p['pid']})")
        was_running = True

    elif not lol_procs and was_running:
        print("[종료] 롤이 꺼졌습니다.\n")
        was_running = False

    time.sleep(0.5)
