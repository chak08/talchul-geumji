# -*- coding: utf-8 -*-
import tkinter as tk
import random
import math

ESCAPE_DISTANCE = 120   # 이 거리 이내로 마우스 오면 도망
CHECK_MS = 80           # 마우스 체크 주기 (ms)
WINDOW_SIZE = 80        # 아이콘 창 크기

class EscapeIcon:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)        # 제목표시줄 제거
        self.root.attributes("-topmost", True)  # 항상 위
        self.root.attributes("-alpha", 0.92)

        self.screen_w = self.root.winfo_screenwidth()
        self.screen_h = self.root.winfo_screenheight()

        # 창 크기 고정
        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")

        # UI 구성
        self.canvas = tk.Canvas(
            self.root,
            width=WINDOW_SIZE,
            height=WINDOW_SIZE,
            bg="#1a1a2e",
            highlightthickness=0
        )
        self.canvas.pack()

        # 이모지 + 텍스트
        self.canvas.create_text(
            WINDOW_SIZE // 2, 28,
            text="🎮",
            font=("Arial", 26),
            fill="white"
        )
        self.canvas.create_text(
            WINDOW_SIZE // 2, 58,
            text="못잡아!",
            font=("Arial", 9, "bold"),
            fill="#ff6b6b"
        )

        # 초기 위치: 화면 중앙
        x = self.screen_w // 2
        y = self.screen_h // 2
        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{x}+{y}")

        self._check_mouse()
        self.root.mainloop()

    def _get_pos(self):
        return self.root.winfo_x(), self.root.winfo_y()

    def _distance_to_mouse(self, mx, my):
        wx, wy = self._get_pos()
        cx = wx + WINDOW_SIZE // 2
        cy = wy + WINDOW_SIZE // 2
        return math.sqrt((mx - cx) ** 2 + (my - cy) ** 2)

    def _escape(self, mx, my):
        wx, wy = self._get_pos()
        cx = wx + WINDOW_SIZE // 2
        cy = wy + WINDOW_SIZE // 2

        # 마우스 반대 방향으로 도망
        dx = cx - mx
        dy = cy - my
        length = math.sqrt(dx**2 + dy**2) or 1

        # 200~350px 범위로 튀어나감
        jump = random.randint(200, 350)
        new_cx = cx + (dx / length) * jump
        new_cy = cy + (dy / length) * jump

        # 화면 경계 안에 클램핑
        new_x = int(max(0, min(self.screen_w - WINDOW_SIZE, new_cx - WINDOW_SIZE // 2)))
        new_y = int(max(0, min(self.screen_h - WINDOW_SIZE - 40, new_cy - WINDOW_SIZE // 2)))

        # 같은 자리면 랜덤으로 튕기기
        if abs(new_x - wx) < 50 and abs(new_y - wy) < 50:
            new_x = random.randint(0, self.screen_w - WINDOW_SIZE)
            new_y = random.randint(0, self.screen_h - WINDOW_SIZE - 40)

        self.root.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}+{new_x}+{new_y}")

    def _check_mouse(self):
        try:
            mx = self.root.winfo_pointerx()
            my = self.root.winfo_pointery()

            if self._distance_to_mouse(mx, my) < ESCAPE_DISTANCE:
                self._escape(mx, my)
        except Exception:
            pass

        self.root.after(CHECK_MS, self._check_mouse)


if __name__ == "__main__":
    EscapeIcon()
