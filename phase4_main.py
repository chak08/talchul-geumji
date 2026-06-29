# -*- coding: utf-8 -*-
"""
탈출금지 Phase 4+5+6
흐름: 롤 감지 → 아이콘 등장 → 카운트다운
      클릭 성공 → 오늘 면제 / 시간 초과 → 강제 종료
설정: 우클릭 트레이 → 설정 창 (config.json 저장)
시작: Windows 시작 프로그램 자동 등록
"""
import threading
import queue
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import psutil
import ctypes
import random
import math
import time
import json
import os
import sys
import winreg
from datetime import date

import pystray
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageTk

# ── 경로 ──────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
APP_NAME    = "탈출금지"
REG_KEY     = r"Software\Microsoft\Windows\CurrentVersion\Run"

# ── 기본 설정 ──────────────────────────────────────
DEFAULT_CONFIG = {
    "enabled":            True,
    "countdown_sec":      10,
    "escape_distance":    120,
    "block_start_hour":   0,
    "block_end_hour":     24,
    "shutdown_enabled":   True,
    "shutdown_delay_min": 30,
    "shutdown_image_path": "",
}

LOL_PROCESSES = [
    "LeagueClient.exe",
    "League of Legends.exe",
    "LeagueClientUxRender.exe",
    "LeagueClientUx.exe",
    "RiotClientServices.exe",
    "RiotClientUx.exe",
]

WINDOW_SIZE = 90
CHECK_MS    = 80

CAPTCHA_CHARS  = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CAPTCHA_LENGTH = 5
CAPTCHA_SEC    = 30

event_queue = queue.Queue()
exempt_date = None


# ── 보안문자 이미지 생성 ───────────────────────────
def _get_font(size):
    for path in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/verdana.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()

def generate_captcha():
    W, H = 240, 80
    img = Image.new("RGB", (W, H), (18, 18, 38))
    draw = ImageDraw.Draw(img)

    for _ in range(10):
        x1, y1 = random.randint(0, W), random.randint(0, H)
        x2, y2 = random.randint(0, W), random.randint(0, H)
        c = (random.randint(50, 110), random.randint(50, 110), random.randint(70, 140))
        draw.line([(x1, y1), (x2, y2)], fill=c, width=2)
    for _ in range(120):
        x, y = random.randint(0, W), random.randint(0, H)
        c = (random.randint(40, 90), random.randint(40, 90), random.randint(60, 120))
        draw.point((x, y), fill=c)

    answer = ''.join(random.choices(CAPTCHA_CHARS, k=CAPTCHA_LENGTH))
    font = _get_font(36)
    slot_w = W // CAPTCHA_LENGTH

    for i, ch in enumerate(answer):
        ch_img = Image.new("RGBA", (52, 62), (0, 0, 0, 0))
        ch_draw = ImageDraw.Draw(ch_img)
        color = (
            random.randint(180, 255),
            random.randint(190, 255),
            random.randint(160, 255),
            255,
        )
        ch_draw.text((6, 8), ch, fill=color, font=font)
        ch_img = ch_img.rotate(random.randint(-28, 28), expand=False)
        x = i * slot_w + random.randint(2, 8)
        y = random.randint(4, 16)
        img.paste(ch_img, (x, y), ch_img)

    img = img.filter(ImageFilter.GaussianBlur(radius=0.7))
    return img, answer


# ── config ─────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            cfg = DEFAULT_CONFIG.copy()
            cfg.update(saved)
            return cfg
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    print("[설정저장] config.json 업데이트")


# ── 시작 프로그램 등록 ─────────────────────────────
def get_launch_cmd():
    if getattr(sys, 'frozen', False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def is_startup_registered():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
        val, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return val == get_launch_cmd()
    except FileNotFoundError:
        return False

def register_startup():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_launch_cmd())
    winreg.CloseKey(key)
    print("[시작등록] Windows 시작 프로그램에 등록됨")

def unregister_startup():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        print("[시작해제] 시작 프로그램에서 제거됨")
    except FileNotFoundError:
        pass


# ── 트레이 아이콘 이미지 생성 ──────────────────────
def make_tray_image(enabled=True):
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    color = "#34c759" if enabled else "#888888"
    d.ellipse([4, 4, 60, 60], fill=color)
    d.text((18, 18), "🔒", fill="white")
    return img


# ── 프로세스 유틸 ──────────────────────────────────
def find_lol():
    found = []
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            if proc.info['name'] in LOL_PROCESSES:
                found.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return found

def kill_lol():
    procs = find_lol()
    killed, failed = [], []
    for proc in procs:
        try:
            name = proc.name()
            proc.kill()
            killed.append(name)
        except psutil.AccessDenied:
            failed.append(proc.name())
        except psutil.NoSuchProcess:
            pass
    return killed, failed

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def is_block_time(cfg):
    h = time.localtime().tm_hour
    s, e = cfg["block_start_hour"], cfg["block_end_hour"]
    if s <= e:
        return s <= h < e
    return h >= s or h < e


# ── 백그라운드 감지 스레드 ─────────────────────────
def monitor_loop(cfg_ref):
    was_running = False
    while True:
        cfg = cfg_ref[0]
        if cfg["enabled"] and is_block_time(cfg):
            procs = find_lol()
            if procs and not was_running:
                was_running = True
                event_queue.put('LOL_DETECTED')
            elif not procs and was_running:
                was_running = False
        time.sleep(0.5)


# ── 설정 창 ────────────────────────────────────────
class SettingsWindow:
    def __init__(self, parent, cfg, on_save):
        self.cfg     = cfg
        self.on_save = on_save

        self.win = tk.Toplevel(parent)
        self.win.title("탈출금지 설정")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1a1a2e")

        pad = {"padx": 16, "pady": 6}

        # 활성화 토글
        self.var_enabled = tk.BooleanVar(value=cfg["enabled"])
        tk.Checkbutton(
            self.win, text="차단 활성화", variable=self.var_enabled,
            bg="#1a1a2e", fg="white", selectcolor="#333355",
            activebackground="#1a1a2e", activeforeground="white",
            font=("Arial", 11)
        ).pack(anchor="w", **pad)

        # 카운트다운
        tk.Label(self.win, text="카운트다운 시간 (초)", bg="#1a1a2e", fg="#aaaaaa", font=("Arial", 9)).pack(anchor="w", padx=16, pady=(10,0))
        self.var_countdown = tk.IntVar(value=cfg["countdown_sec"])
        tk.Scale(
            self.win, from_=5, to=30, orient="horizontal",
            variable=self.var_countdown, bg="#1a1a2e", fg="white",
            troughcolor="#333355", highlightthickness=0, length=220
        ).pack(padx=16)

        # 차단 시간대
        tk.Label(self.win, text="차단 시간대 (시작 ~ 종료)", bg="#1a1a2e", fg="#aaaaaa", font=("Arial", 9)).pack(anchor="w", padx=16, pady=(10,0))
        tf = tk.Frame(self.win, bg="#1a1a2e")
        tf.pack(padx=16, pady=4)
        self.var_start = tk.IntVar(value=cfg["block_start_hour"])
        self.var_end   = tk.IntVar(value=cfg["block_end_hour"])
        tk.Scale(tf, from_=0, to=23, orient="horizontal", variable=self.var_start,
                 label="시작시", bg="#1a1a2e", fg="white", troughcolor="#333355",
                 highlightthickness=0, length=100).pack(side="left", padx=4)
        tk.Scale(tf, from_=1, to=24, orient="horizontal", variable=self.var_end,
                 label="종료시", bg="#1a1a2e", fg="white", troughcolor="#333355",
                 highlightthickness=0, length=100).pack(side="left", padx=4)

        # 시작 프로그램 등록
        tk.Frame(self.win, bg="#444444", height=1).pack(fill="x", padx=16, pady=8)
        self.var_startup = tk.BooleanVar(value=is_startup_registered())
        tk.Checkbutton(
            self.win, text="Windows 시작 시 자동 실행", variable=self.var_startup,
            bg="#1a1a2e", fg="white", selectcolor="#333355",
            activebackground="#1a1a2e", activeforeground="white",
            font=("Arial", 10)
        ).pack(anchor="w", padx=16)

        # ── 강제 종료 섹션 ──────────────────────────
        tk.Frame(self.win, bg="#444444", height=1).pack(fill="x", padx=16, pady=8)
        tk.Label(self.win, text="⏻  강제 종료 설정", bg="#1a1a2e", fg="#ff9500",
                 font=("Arial", 10, "bold")).pack(anchor="w", padx=16)

        self.var_shutdown = tk.BooleanVar(value=cfg.get("shutdown_enabled", True))
        tk.Checkbutton(
            self.win, text="보안 인증 통과 후 N분 뒤 강제 종료",
            variable=self.var_shutdown,
            bg="#1a1a2e", fg="white", selectcolor="#333355",
            activebackground="#1a1a2e", activeforeground="white",
            font=("Arial", 10)
        ).pack(anchor="w", padx=16, pady=(4, 0))

        tk.Label(self.win, text="종료까지 대기 시간 (분)",
                 bg="#1a1a2e", fg="#aaaaaa", font=("Arial", 9)).pack(anchor="w", padx=16, pady=(8, 0))
        self.var_delay = tk.IntVar(value=cfg.get("shutdown_delay_min", 30))
        tk.Scale(
            self.win, from_=1, to=180, orient="horizontal",
            variable=self.var_delay, bg="#1a1a2e", fg="white",
            troughcolor="#333355", highlightthickness=0, length=220
        ).pack(padx=16)

        tk.Label(self.win, text="종료 전 표시할 이미지 (선택)",
                 bg="#1a1a2e", fg="#aaaaaa", font=("Arial", 9)).pack(anchor="w", padx=16, pady=(8, 0))
        img_frame = tk.Frame(self.win, bg="#1a1a2e")
        img_frame.pack(fill="x", padx=16, pady=(2, 0))
        self.var_img_path = tk.StringVar(value=cfg.get("shutdown_image_path", ""))
        tk.Entry(
            img_frame, textvariable=self.var_img_path,
            bg="#333355", fg="white", insertbackground="white",
            relief="flat", font=("Arial", 8), width=26
        ).pack(side="left", ipady=4)
        tk.Button(
            img_frame, text="찾기", command=self._browse_image,
            bg="#555577", fg="white", font=("Arial", 8),
            relief="flat", cursor="hand2", padx=6
        ).pack(side="left", padx=(4, 0))
        tk.Button(
            img_frame, text="지우기", command=lambda: self.var_img_path.set(""),
            bg="#444444", fg="#aaaaaa", font=("Arial", 8),
            relief="flat", cursor="hand2", padx=6
        ).pack(side="left", padx=(2, 0))

        # 저장 버튼
        tk.Button(
            self.win, text="저장", command=self._save,
            bg="#0066cc", fg="white", font=("Arial", 11, "bold"),
            relief="flat", padx=20, pady=6, cursor="hand2"
        ).pack(pady=14)

        self.win.update_idletasks()
        w, h = self.win.winfo_width(), self.win.winfo_height()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        self.win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

    def _browse_image(self):
        path = filedialog.askopenfilename(
            parent=self.win,
            title="종료 전 표시할 이미지 선택",
            filetypes=[("이미지 파일", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("모든 파일", "*.*")]
        )
        if path:
            self.var_img_path.set(path)

    def _save(self):
        self.cfg["enabled"]             = self.var_enabled.get()
        self.cfg["countdown_sec"]       = self.var_countdown.get()
        self.cfg["block_start_hour"]    = self.var_start.get()
        self.cfg["block_end_hour"]      = self.var_end.get()
        self.cfg["shutdown_enabled"]    = self.var_shutdown.get()
        self.cfg["shutdown_delay_min"]  = self.var_delay.get()
        self.cfg["shutdown_image_path"] = self.var_img_path.get()
        save_config(self.cfg)
        if self.var_startup.get():
            register_startup()
        else:
            unregister_startup()
        self.on_save(self.cfg)
        messagebox.showinfo("저장 완료", "설정이 저장되었습니다.", parent=self.win)
        self.win.destroy()


# ── 종료 경고 전체화면 ──────────────────────────────
class ShutdownWarningWindow:
    WARN_SEC = 10

    def __init__(self, parent, image_path):
        self.countdown = self.WARN_SEC

        self.win = tk.Toplevel(parent)
        self.win.overrideredirect(True)
        self.win.attributes("-topmost", True)
        self.win.attributes("-fullscreen", True)
        self.win.configure(bg="black")
        self.win.protocol("WM_DELETE_WINDOW", lambda: None)

        sw = self.win.winfo_screenwidth()
        sh = self.win.winfo_screenheight()

        if image_path and os.path.exists(image_path):
            try:
                raw = Image.open(image_path).convert("RGB")
                raw = raw.resize((sw, sh), Image.LANCZOS)
                self._tk_img = ImageTk.PhotoImage(raw)
                tk.Label(self.win, image=self._tk_img, bg="black").place(x=0, y=0)
            except Exception:
                pass

        # 반투명 오버레이 텍스트
        self._msg_var = tk.StringVar()
        tk.Label(
            self.win, textvariable=self._msg_var,
            bg="black", fg="#ff3b30",
            font=("Arial", 28, "bold"),
            wraplength=sw - 40,
        ).place(relx=0.5, rely=0.88, anchor="center")

        self._tick()

    def _tick(self):
        self._msg_var.set(f"⚠  {self.countdown}초 후 컴퓨터가 종료됩니다")
        if self.countdown <= 0:
            os.system("shutdown /s /t 0")
            return
        self.countdown -= 1
        self.win.after(1000, self._tick)


# ── 보안문자 창 ────────────────────────────────────
class CaptchaWindow:
    def __init__(self, parent, on_success, on_fail):
        self.on_success  = on_success
        self.on_fail     = on_fail
        self.countdown   = CAPTCHA_SEC
        self._running    = True

        self.win = tk.Toplevel(parent)
        self.win.title("탈출금지 — 보안 인증")
        self.win.resizable(False, False)
        self.win.attributes("-topmost", True)
        self.win.configure(bg="#1a1a2e")
        self.win.protocol("WM_DELETE_WINDOW", self._fail)

        tk.Label(self.win, text="🔒 보안 인증", bg="#1a1a2e", fg="white",
                 font=("Arial", 14, "bold")).pack(pady=(16, 2))
        tk.Label(self.win, text="아래 문자를 입력하면 오늘 하루 면제!",
                 bg="#1a1a2e", fg="#aaaaaa", font=("Arial", 9)).pack()

        # 이미지 프레임
        img_frame = tk.Frame(self.win, bg="#2a2a4a", bd=0)
        img_frame.pack(padx=24, pady=(12, 4))
        self._captcha_img, self._answer = generate_captcha()
        self._tk_img = ImageTk.PhotoImage(self._captcha_img)
        self._img_label = tk.Label(img_frame, image=self._tk_img, bg="#2a2a4a")
        self._img_label.pack(padx=6, pady=6)

        tk.Button(self.win, text="🔄  새 문자", command=self._refresh,
                  bg="#2a2a4a", fg="#aaaaaa", font=("Arial", 8),
                  relief="flat", cursor="hand2", bd=0).pack()

        # 입력
        self._var = tk.StringVar()
        self._entry = tk.Entry(self.win, textvariable=self._var,
                               font=("Arial", 20, "bold"),
                               bg="#2a2a4a", fg="white", insertbackground="white",
                               justify="center", width=9, relief="flat", bd=0)
        self._entry.pack(pady=(12, 2), padx=24, ipady=6)
        self._entry.bind("<Return>", lambda e: self._submit())
        self._entry.focus()

        # 오류 메시지
        self._err_var = tk.StringVar()
        tk.Label(self.win, textvariable=self._err_var,
                 bg="#1a1a2e", fg="#ff3b30", font=("Arial", 9)).pack(pady=(2, 0))

        # 타이머
        self._timer_var = tk.StringVar()
        tk.Label(self.win, textvariable=self._timer_var,
                 bg="#1a1a2e", fg="#ff9500", font=("Arial", 10)).pack(pady=(2, 0))

        tk.Button(self.win, text="확인", command=self._submit,
                  bg="#0066cc", fg="white", font=("Arial", 12, "bold"),
                  relief="flat", padx=36, pady=8, cursor="hand2", bd=0).pack(pady=14)

        self.win.update_idletasks()
        w, h = self.win.winfo_width(), self.win.winfo_height()
        sw, sh = self.win.winfo_screenwidth(), self.win.winfo_screenheight()
        self.win.geometry(f"+{(sw-w)//2}+{(sh-h)//2}")

        self._tick()

    def _refresh(self):
        self._captcha_img, self._answer = generate_captcha()
        self._tk_img = ImageTk.PhotoImage(self._captcha_img)
        self._img_label.configure(image=self._tk_img)
        self._var.set("")
        self._err_var.set("")

    def _tick(self):
        if not self._running:
            return
        self._timer_var.set(f"⏱  {self.countdown}초 남음")
        if self.countdown <= 0:
            self._fail()
            return
        self.countdown -= 1
        self.win.after(1000, self._tick)

    def _submit(self):
        entered = self._var.get().strip().upper()
        if entered == self._answer:
            self._running = False
            self.win.destroy()
            self.on_success()
        else:
            self._err_var.set("❌ 틀렸습니다. 다시 시도하세요.")
            self._var.set("")
            self._refresh()

    def _fail(self):
        if not self._running:
            return
        self._running = False
        try:
            self.win.destroy()
        except Exception:
            pass
        self.on_fail()


# ── 도망 아이콘 UI ─────────────────────────────────
class TalchulGeumji:
    def __init__(self, cfg):
        self.cfg = cfg

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 0.95)
        self.root.withdraw()

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        self.canvas = tk.Canvas(
            self.root, width=WINDOW_SIZE, height=WINDOW_SIZE,
            bg="#1a1a2e", highlightthickness=2, highlightbackground="#ff6b6b"
        )
        self.canvas.pack()
        self.emoji_id = self.canvas.create_text(WINDOW_SIZE//2, 25, text="🎮", font=("Arial", 24), fill="white")
        self.count_id = self.canvas.create_text(WINDOW_SIZE//2, 52, text="10", font=("Arial", 16, "bold"), fill="#ff6b6b")
        self.label_id = self.canvas.create_text(WINDOW_SIZE//2, 76, text="잡으면 면제!", font=("Arial", 7), fill="#aaaaaa")

        self.canvas.bind("<Button-1>", self._on_caught)
        self.canvas.bind("<Button-3>", self._open_settings)

        self.active              = False
        self.countdown           = self.cfg["countdown_sec"]
        self.tray                = None
        self._shutdown_scheduled = False

        self._start_tray()
        self._poll_events()
        self.root.mainloop()

    # ── 트레이 아이콘 시작 ──
    def _start_tray(self):
        def on_settings(icon, item):
            self.root.after(0, self._open_settings)

        def on_toggle(icon, item):
            self.cfg["enabled"] = not self.cfg["enabled"]
            save_config(self.cfg)
            icon.icon = make_tray_image(self.cfg["enabled"])
            status = "활성화" if self.cfg["enabled"] else "비활성화"
            print(f"[토글] 차단 {status}")

        def on_quit(icon, item):
            icon.stop()
            self.root.after(0, self.root.destroy)

        menu = pystray.Menu(
            pystray.MenuItem("탈출금지 실행 중", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("설정...", on_settings),
            pystray.MenuItem("차단 ON/OFF", on_toggle),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("종료", on_quit),
        )
        self.tray = pystray.Icon(
            APP_NAME,
            make_tray_image(self.cfg["enabled"]),
            APP_NAME,
            menu
        )
        t = threading.Thread(target=self.tray.run, daemon=True)
        t.start()
        print("[트레이] 작업표시줄 트레이에 아이콘 등록됨")

    def _update_cfg(self, new_cfg):
        self.cfg = new_cfg
        if self.tray:
            self.tray.icon = make_tray_image(self.cfg["enabled"])

    # ── 이벤트 폴링 ──
    def _poll_events(self):
        try:
            while True:
                ev = event_queue.get_nowait()
                if ev == 'LOL_DETECTED':
                    self._activate()
        except queue.Empty:
            pass
        self.root.after(200, self._poll_events)

    # ── 설정 창 열기 ──
    def _open_settings(self, event=None):
        self.root.attributes("-topmost", False)
        SettingsWindow(self.root, self.cfg, self._update_cfg)

    # ── 아이콘 활성화 ──
    def _activate(self):
        global exempt_date
        if exempt_date == date.today():
            print("[면제] 오늘 이미 잡음 — 면제 유지")
            return
        if self.active:
            return

        self.countdown = self.cfg["countdown_sec"]
        print(f"[등장] 아이콘 표시 — {self.countdown}초 안에 클릭!")
        self.active = True
        self.canvas.itemconfig(self.count_id, text=str(self.countdown))

        x = random.randint(100, self.screen_w - WINDOW_SIZE - 100)
        y = random.randint(100, self.screen_h - WINDOW_SIZE - 100)
        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{x}+{y}")
        self.root.attributes("-topmost", True)
        self.root.deiconify()

        self._tick()
        self._check_mouse()

    # ── 카운트다운 ──
    def _tick(self):
        if not self.active:
            return
        self.canvas.itemconfig(self.count_id, text=str(self.countdown))
        ratio = self.countdown / self.cfg["countdown_sec"]
        color = "#34c759" if ratio > 0.6 else "#ff9500" if ratio > 0.3 else "#ff3b30"
        self.canvas.itemconfig(self.count_id, fill=color)
        if self.countdown <= 0:
            self._time_over()
            return
        self.countdown -= 1
        self.root.after(1000, self._tick)

    # ── 마우스 도망 ──
    def _check_mouse(self):
        if not self.active:
            return
        try:
            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()
            wx, wy = self.root.winfo_x(), self.root.winfo_y()
            cx, cy = wx + WINDOW_SIZE//2, wy + WINDOW_SIZE//2
            dist = math.sqrt((mx-cx)**2 + (my-cy)**2)
            if dist < self.cfg["escape_distance"]:
                dx, dy = cx-mx, cy-my
                length = math.sqrt(dx**2+dy**2) or 1
                jump = random.randint(200, 350)
                nx = int(cx + (dx/length)*jump - WINDOW_SIZE//2)
                ny = int(cy + (dy/length)*jump - WINDOW_SIZE//2)
                nx = max(0, min(self.screen_w - WINDOW_SIZE, nx))
                ny = max(0, min(self.screen_h - WINDOW_SIZE - 40, ny))
                if abs(nx-wx) < 50 and abs(ny-wy) < 50:
                    nx = random.randint(0, self.screen_w - WINDOW_SIZE)
                    ny = random.randint(0, self.screen_h - WINDOW_SIZE - 40)
                self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{nx}+{ny}")
        except Exception:
            pass
        self.root.after(CHECK_MS, self._check_mouse)

    # ── 강제 종료 실행 ──
    def _trigger_shutdown(self):
        print("[종료] 예약 강제 종료 실행")
        ShutdownWarningWindow(self.root, self.cfg.get("shutdown_image_path", ""))

    # ── 클릭 → 보안문자 ──
    def _on_caught(self, event=None):
        if not self.active:
            return
        self.active = False
        self.root.withdraw()
        print("[아이콘 클리어] 보안 인증 창 표시")

        def on_captcha_success():
            global exempt_date
            exempt_date = date.today()
            print("[면제] 보안 인증 통과! 오늘 하루 면제. 즐겜 ㅎ")
            if self.cfg.get("shutdown_enabled") and not self._shutdown_scheduled:
                delay_min = self.cfg.get("shutdown_delay_min", 30)
                delay_ms  = delay_min * 60 * 1000
                self._shutdown_scheduled = True
                print(f"[종료예약] {delay_min}분 후 강제 종료 예약됨")
                self.root.after(delay_ms, self._trigger_shutdown)

        def on_captcha_fail():
            print("[종료] 보안 인증 실패/시간 초과 — 롤 강제 종료!")
            killed, failed = kill_lol()
            if killed:
                print(f"  종료됨: {', '.join(killed)}")
            if failed:
                print(f"  실패(권한 부족): {', '.join(failed)}")

        CaptchaWindow(self.root, on_captcha_success, on_captcha_fail)

    # ── 시간 초과 → 종료 ──
    def _time_over(self):
        self.active = False
        self.root.withdraw()
        print("[종료] 시간 초과 — 롤 강제 종료!")
        killed, failed = kill_lol()
        if killed:
            print(f"  종료됨: {', '.join(killed)}")
        if failed:
            print(f"  실패(권한 부족): {', '.join(failed)}")


# ── 진입점 ────────────────────────────────────────
if __name__ == "__main__":
    cfg = load_config()
    print(f"[설정] 카운트다운={cfg['countdown_sec']}초 | 차단={cfg['block_start_hour']}~{cfg['block_end_hour']}시 | 활성={cfg['enabled']}")

    if not is_startup_registered():
        register_startup()

    if not is_admin():
        print("[경고] 관리자 권한 없음 (대부분 정상 작동)")
    print("[탈출금지] 시작 | 트레이 우클릭 → 메뉴 | 아이콘 우클릭 → 설정\n")

    cfg_ref = [cfg]
    threading.Thread(target=monitor_loop, args=(cfg_ref,), daemon=True).start()

    TalchulGeumji(cfg)
