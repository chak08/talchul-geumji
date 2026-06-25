# -*- coding: utf-8 -*-
import psutil
import time
import sys
import ctypes

LOL_PROCESSES = [
    "LeagueClient.exe",
    "League of Legends.exe",
    "LeagueClientUxRender.exe",
    "LeagueClientUx.exe",
    "RiotClientServices.exe",   # 라이엇 런처
    "RiotClientUx.exe",
]

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def find_lol():
    found = []
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] in LOL_PROCESSES:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found

def kill_lol(procs):
    killed = []
    failed = []
    for proc in procs:
        try:
            name = proc.name()
            proc.kill()
            killed.append(name)
        except psutil.AccessDenied:
            failed.append(proc.name())
        except psutil.NoSuchProcess:
            pass  # 이미 꺼진 경우
    return killed, failed

# --- 관리자 권한 체크 ---
if not is_admin():
    print("[경고] 관리자 권한 없음 - 일부 프로세스 종료 실패할 수 있음")
    print("       .py 파일을 관리자 권한으로 실행하면 100% 종료 가능\n")
else:
    print("[OK] 관리자 권한 확인\n")

print("[탈출금지] 감지+종료 시작... (Ctrl+C 종료)")
print()

was_running = False

while True:
    lol_procs = find_lol()

    if lol_procs and not was_running:
        print("[감지] 롤 실행됨!")
        for p in lol_procs:
            try:
                print(f"  -> {p.name()} (PID: {p.pid})")
            except:
                pass
        was_running = True

        # 3초 카운트다운
        for i in range(3, 0, -1):
            print(f"  {i}초 후 강제 종료...")
            time.sleep(1)

        # 종료 실행
        lol_procs = find_lol()  # 다시 찾기 (그 사이 추가 프로세스 생길 수 있음)
        killed, failed = kill_lol(lol_procs)

        if killed:
            print(f"[완료] 종료됨: {', '.join(killed)}")
        if failed:
            print(f"[실패] 권한 부족: {', '.join(failed)}")
            print("       관리자 권한으로 다시 실행하세요.")
        print()

    elif not lol_procs and was_running:
        was_running = False

    time.sleep(0.5)
