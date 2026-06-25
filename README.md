# 탈출금지 — 게임중독치료 앱

> 롤을 켜면 감지 → 도망다니는 아이콘 등장 → 못 잡으면 강제 종료

---

## 실행 방법

```powershell
$env:PYTHONUTF8=1
python phase4_main.py
```

---

## 파일 구조

```
탈출금지/
├── phase4_main.py     # ★ 메인 실행 파일 (이걸 쓰면 됨)
├── config.json        # 설정 저장 파일 (자동 생성)
├── phase1_detect.py   # 감지만 (개발 참고용)
├── phase2_kill.py     # 감지 + 강제 종료 (개발 참고용)
├── phase3_icon.py     # 도망 아이콘만 (개발 참고용)
└── README.md
```

---

## 설치 패키지

```powershell
python -m pip install psutil pystray pillow
```

---

## 동작 흐름

```
실행 → config.json 로드 → 트레이 아이콘 등록 → 롤 감지 대기
                                                        ↓
                                                   롤 켜짐
                                                        ↓
                                             🎮 아이콘 화면 등장
                                             카운트다운 시작 (기본 10초)
                                               ↙              ↘
                                          클릭 성공         시간 초과
                                         오늘 면제          롤 강제 종료
```

---

## config.json 설정

```json
{
  "enabled": true,          // 차단 활성화 여부
  "countdown_sec": 10,      // 잡을 수 있는 시간 (5~30초)
  "escape_distance": 120,   // 마우스 도망 감지 거리 (px)
  "block_start_hour": 0,    // 차단 시작 시간
  "block_end_hour": 24      // 차단 종료 시간
}
```

직접 편집 또는 → 트레이 우클릭 → 설정 창에서 변경

---

## Phase별 완성 내역

| Phase | 내용 | 상태 |
|-------|------|------|
| 1 | 롤 프로세스 감지 | ✅ |
| 2 | 감지 + 3초 카운트다운 + 강제 종료 | ✅ |
| 3 | 마우스 접근 시 도망다니는 아이콘 UI | ✅ |
| 4 | 전체 통합 (감지→아이콘→면제/종료) | ✅ |
| 5 | config.json 설정 저장 + 설정 UI | ✅ |
| 6 | 트레이 아이콘 상주 + 시작 프로그램 등록 | ✅ |
| 7 | SMS 책임 시스템 (솔라피 API) | ⏳ |
| 8 | .exe 패키징 (PyInstaller) | ✅ |

---

## 실행 파일

```
dist/탈출금지.exe   ← 배포용 단일 실행 파일 (18.5 MB)
```

더블클릭으로 바로 실행. Python 설치 불필요.

---

## 남은 작업

### Phase 7 — SMS 책임 시스템
- 솔라피(https://solapi.com) 회원가입 + API 키 발급 필요 (1~3일)
- 설치 시 → "게임 끊겠습니다" SMS 자동 발송
- 앱 삭제 감지 → "실패했습니다" SMS 발송

---

## 다음 세션 재개

Claude에게 **"탈출금지 Phase 7 SMS 이어서"** 라고 하면 됨.
