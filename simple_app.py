from __future__ import annotations

import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core.io_utils import read_text, write_text, write_json
from core.master_registry import (
    CHANNEL_LABELS,
    DEFAULT_REGISTRY_PATH,
    read_registered_master,
    register_master,
)
from core.workflows import (
    GENRE_CHOICES,
    load_json_text,
    detect_source_profile,
    validate_master_compatibility,
    build_existing_json_upgrade_instruction,
    build_haru_txt_instruction,
    finalize_existing_upgrade,
    finalize_haru_result,
)

CHANNEL_OPTIONS = {label: channel_id for channel_id, label in CHANNEL_LABELS.items()}


class SimpleApp(tk.Tk):
    """Two-workflow UI for actual day-to-day Suno production."""

    def __init__(self):
        super().__init__()
        self.title("Suno Master Prompt Studio v0.5 - Simple Workflow")
        self.geometry("1320x900")
        self.minsize(1080, 720)

        self.existing_source_text = ""
        self.existing_master_text = ""
        self.existing_instruction = ""
        self.existing_final = None
        self.existing_channel_id = "custom"

        self.haru_text = ""
        self.haru_master_text = ""
        self.haru_instruction = ""
        self.haru_final = None
        self.registry_path = DEFAULT_REGISTRY_PATH

        self._build()

    def _build(self):
        header = ttk.Frame(self, padding=(14, 12))
        header.pack(fill="x")
        ttk.Label(header, text="Suno Master Prompt Studio", font=("Segoe UI", 18, "bold")).pack(side="left")
        ttk.Label(header, text="  실제 작업은 2가지만 사용합니다.", font=("Segoe UI", 10)).pack(side="left", padx=8)

        ttk.Label(
            self,
            text=(
                "① 기존 JSON → 최신 마스터로 음악 프롬프트 업그레이드  |  "
                "② Haru Studio TXT → 최신 마스터로 신규 15곡 제작\n"
                "중간 Track Plan은 내부 처리용입니다. 최종 목표는 title + lyrics + stylePrompt가 모두 들어 있는 완성형 Suno JSON입니다."
            ),
            padding=(14, 0, 14, 10),
            justify="left",
        ).pack(fill="x")

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.simple_nb = nb

        self.existing_tab = ttk.Frame(nb, padding=12)
        self.haru_tab = ttk.Frame(nb, padding=12)
        nb.add(self.existing_tab, text="1. 기존 JSON 업그레이드")
        nb.add(self.haru_tab, text="2. Haru Studio TXT → 신규 제작")

        self._build_existing_tab()
        self._build_haru_tab()

    @staticmethod
    def _put_text(widget, text):
        widget.delete("1.0", "end")
        widget.insert("1.0", text)

    def _copy_widget(self, widget, label="내용"):
        text = widget.get("1.0", "end").strip()
        if not text:
            messagebox.showwarning("복사", f"{label}이 없습니다.")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        messagebox.showinfo("복사", f"{label}을 클립보드에 복사했습니다.")

    def _build_existing_tab(self):
        step1 = ttk.Labelframe(self.existing_tab, text="STEP 1  원본 JSON + 최신 마스터", padding=10)
        step1.pack(fill="x")

        row = ttk.Frame(step1)
        row.pack(fill="x")
        ttk.Button(row, text="원본 JSON 불러오기", command=self.load_existing_json).pack(side="left")
        self.existing_source_var = tk.StringVar(value="선택 안 됨")
        ttk.Label(row, textvariable=self.existing_source_var).pack(side="left", padx=10)
        ttk.Button(row, text="마스터 변경/관리", command=self.manage_existing_master).pack(side="left", padx=(20, 0))
        self.existing_master_var = tk.StringVar(value="선택 안 됨")
        ttk.Label(row, textvariable=self.existing_master_var).pack(side="left", padx=10)

        self.existing_detect_var = tk.StringVar(value="원본 JSON을 불러오면 15곡/남성/여성/두사람 여부를 자동 확인합니다.")
        ttk.Label(step1, textvariable=self.existing_detect_var, foreground="#444").pack(anchor="w", pady=(8, 0))

        genre_row = ttk.Frame(step1)
        genre_row.pack(fill="x", pady=(8, 0))
        ttk.Label(genre_row, text="장르 선택").pack(side="left")
        self.existing_genre_var = tk.StringVar(value="자동(원본 유지)")
        self.existing_genre_cb = ttk.Combobox(
            genre_row,
            textvariable=self.existing_genre_var,
            state="readonly",
            width=25,
            values=list(GENRE_CHOICES),
        )
        self.existing_genre_cb.pack(side="left", padx=8)
        self.existing_genre_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_existing_master_label())
        self.existing_active_master_var = tk.StringVar(value="사용 마스터: 미등록")
        ttk.Label(genre_row, textvariable=self.existing_active_master_var, foreground="#333").pack(side="left", padx=16)

        step2 = ttk.Labelframe(self.existing_tab, text="STEP 2  ChatGPT 업그레이드 지시문", padding=10)
        step2.pack(fill="both", expand=True, pady=(10, 0))

        bar = ttk.Frame(step2)
        bar.pack(fill="x")
        ttk.Button(bar, text="최신 마스터 반영 → 업그레이드 지시문 만들기", command=self.make_existing_instruction).pack(side="left")
        ttk.Button(bar, text="지시문 복사", command=lambda: self._copy_widget(self.existing_output, "업그레이드 지시문")).pack(side="left", padx=5)
        ttk.Button(bar, text="지시문 TXT 저장", command=self.save_existing_instruction).pack(side="left")
        ttk.Label(bar, text="→ ChatGPT에 붙여넣고 완성 JSON을 받은 뒤 STEP 3에서 불러오세요.", foreground="#555").pack(side="left", padx=14)

        self.existing_output = tk.Text(step2, wrap="word", font=("Consolas", 9), height=18)
        self.existing_output.pack(fill="both", expand=True, pady=(8, 0))

        step3 = ttk.Labelframe(self.existing_tab, text="STEP 3  ChatGPT 결과 → 최종 Suno JSON", padding=10)
        step3.pack(fill="x", pady=(10, 0))
        row3 = ttk.Frame(step3)
        row3.pack(fill="x")
        ttk.Button(row3, text="ChatGPT 결과 JSON 불러오기", command=self.load_existing_result).pack(side="left")
        ttk.Button(row3, text="최종 JSON 저장", command=self.save_existing_final).pack(side="left", padx=5)
        self.existing_result_var = tk.StringVar(value="아직 결과 JSON을 검증하지 않았습니다.")
        ttk.Label(row3, textvariable=self.existing_result_var).pack(side="left", padx=12)
        ttk.Label(
            step3,
            text=(
                "안전장치: ChatGPT가 제목/가사/훅/스토리/YouTube 메타를 바꿔도 최종 저장 시 원본으로 강제 복원합니다. "
                "BPM/장르/보컬/stylePrompt 등 허용된 음악 필드만 새 결과에서 가져옵니다."
            ),
            foreground="#444",
            wraplength=1180,
        ).pack(anchor="w", pady=(8, 0))

    def _build_haru_tab(self):
        step1 = ttk.Labelframe(self.haru_tab, text="STEP 1  Haru Studio TXT + 최신 마스터", padding=10)
        step1.pack(fill="x")
        row = ttk.Frame(step1)
        row.pack(fill="x")
        ttk.Button(row, text="Haru Studio TXT 불러오기", command=self.load_haru_txt).pack(side="left")
        self.haru_source_var = tk.StringVar(value="선택 안 됨")
        ttk.Label(row, textvariable=self.haru_source_var).pack(side="left", padx=10)
        options = ttk.Frame(step1)
        options.pack(fill="x", pady=(8, 0))
        ttk.Label(options, text="채널/보컬 타입").pack(side="left")
        self.haru_channel_var = tk.StringVar(value="시니어")
        self.haru_channel_cb = ttk.Combobox(
            options, textvariable=self.haru_channel_var, state="readonly", width=18,
            values=list(CHANNEL_OPTIONS),
        )
        self.haru_channel_cb.pack(side="left", padx=8)
        self.haru_channel_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_haru_master())
        ttk.Label(options, text="장르").pack(side="left", padx=(16, 0))
        self.haru_genre_var = tk.StringVar(value="Soft Old Pop Ballad")
        self.haru_genre_cb = ttk.Combobox(
            options, textvariable=self.haru_genre_var, state="readonly", width=25,
            values=[x for x in GENRE_CHOICES if not x.startswith("자동")],
        )
        self.haru_genre_cb.pack(side="left", padx=8)
        self.haru_genre_cb.bind("<<ComboboxSelected>>", lambda _e: self._refresh_haru_master())
        ttk.Button(options, text="마스터 변경/관리", command=self.manage_haru_master).pack(side="left", padx=(16, 0))
        self.haru_master_var = tk.StringVar(value="사용 마스터: 미등록")
        ttk.Label(options, textvariable=self.haru_master_var).pack(side="left", padx=10)

        step2 = ttk.Labelframe(self.haru_tab, text="STEP 2  신규 15곡 제작 지시문", padding=10)
        step2.pack(fill="both", expand=True, pady=(10, 0))
        bar = ttk.Frame(step2)
        bar.pack(fill="x")
        ttk.Button(bar, text="신규 제작 지시문 만들기", command=self.make_haru_instruction).pack(side="left")
        ttk.Button(bar, text="지시문 복사", command=lambda: self._copy_widget(self.haru_output, "신규 제작 지시문")).pack(side="left", padx=5)
        ttk.Button(bar, text="지시문 TXT 저장", command=self.save_haru_instruction).pack(side="left")
        ttk.Label(bar, text="→ ChatGPT가 title + lyrics + stylePrompt를 포함한 완성형 15곡 JSON을 생성합니다.", foreground="#555").pack(side="left", padx=14)

        self.haru_output = tk.Text(step2, wrap="word", font=("Consolas", 9), height=20)
        self.haru_output.pack(fill="both", expand=True, pady=(8, 0))

        step3 = ttk.Labelframe(self.haru_tab, text="STEP 3  ChatGPT 결과 검증/저장", padding=10)
        step3.pack(fill="x", pady=(10, 0))
        row3 = ttk.Frame(step3)
        row3.pack(fill="x")
        ttk.Button(row3, text="ChatGPT 결과 JSON 불러오기", command=self.load_haru_result).pack(side="left")
        ttk.Button(row3, text="최종 JSON 저장", command=self.save_haru_final).pack(side="left", padx=5)
        self.haru_result_var = tk.StringVar(value="아직 결과 JSON을 검증하지 않았습니다.")
        ttk.Label(row3, textvariable=self.haru_result_var).pack(side="left", padx=12)
        self._refresh_haru_master()

    def _registered_master(self, channel_id):
        text, path = read_registered_master(channel_id, self.registry_path)
        return text, path

    def _refresh_existing_master_label(self):
        label = CHANNEL_LABELS[self.existing_channel_id]
        registered = bool(self.existing_master_text)
        self.existing_active_master_var.set(
            f"사용 마스터: {label} 최신 마스터 + {self.existing_genre_var.get()} Genre Master"
            if registered else f"사용 마스터: {label} 미등록 + {self.existing_genre_var.get()} Genre Master"
        )

    def _choose_and_register_master(self, channel_id, source_text=""):
        label = CHANNEL_LABELS[channel_id]
        p = filedialog.askopenfilename(
            title=f"{label} 최신 마스터 TXT 선택",
            filetypes=[("Text", "*.txt"), ("Markdown", "*.md"), ("All", "*.*")],
        )
        if not p:
            return "", None
        text = read_text(p)
        if source_text:
            compat = validate_master_compatibility(load_json_text(source_text), text)
            if not compat["ok"]:
                messagebox.showerror("마스터 불일치", "\n".join(compat["errors"]))
                return "", None
        register_master(channel_id, p, self.registry_path)
        return text, Path(p)

    def _ensure_master(self, channel_id, source_text=""):
        text, path = self._registered_master(channel_id)
        if text:
            return text, path
        label = CHANNEL_LABELS[channel_id]
        messagebox.showinfo(
            "최신 마스터 등록 필요",
            f"{label} 최신 마스터가 아직 등록되지 않았습니다.\n\n"
            "최신 마스터 TXT를 한 번 선택해주세요.\n다음부터 자동으로 사용합니다.",
        )
        return self._choose_and_register_master(channel_id, source_text)

    def load_existing_json(self):
        p = filedialog.askopenfilename(title="기존 15곡 JSON 선택", filetypes=[("JSON", "*.json"), ("All", "*.*")])
        if not p:
            return
        try:
            text = read_text(p)
            obj = load_json_text(text)
            profile = detect_source_profile(obj)
        except Exception as exc:
            messagebox.showerror("원본 JSON 오류", str(exc))
            return
        self.existing_source_text = text
        self.existing_final = None
        self.existing_source_var.set(Path(p).name)
        self.existing_channel_id = profile["channelId"]
        if profile["genreHint"] in GENRE_CHOICES:
            self.existing_genre_var.set(profile["genreHint"])
        self.existing_master_text, master_path = self._registered_master(self.existing_channel_id)
        label = CHANNEL_LABELS[self.existing_channel_id]
        self.existing_master_var.set(master_path.name if master_path else "미등록")
        self.existing_active_master_var.set(
            f"사용 마스터: {label} 최신 마스터 + {self.existing_genre_var.get()} Genre Master"
        )
        self.existing_detect_var.set(
            f"감지: {profile['sourceType']} / {profile['trackCount']}곡 / vocal={profile['vocalMode']} / genre={profile['genreHint'] or '미확인'} / episode={profile['episodeTitle'] or '-'}"
        )

    def manage_existing_master(self):
        text, path = self._choose_and_register_master(self.existing_channel_id, self.existing_source_text)
        if not text:
            return
        self.existing_master_text = text
        self.existing_master_var.set(path.name)
        self.existing_active_master_var.set(
            f"사용 마스터: {CHANNEL_LABELS[self.existing_channel_id]} 최신 마스터 + {self.existing_genre_var.get()} Genre Master"
        )
        if self.existing_source_text:
            try:
                result = validate_master_compatibility(load_json_text(self.existing_source_text), text)
                if result["ok"]:
                    msg = f"마스터 호환 확인: source={result['source']['vocalMode']} / master={result['master']['vocalMode']}"
                    if result["warnings"]:
                        msg += " / 경고: " + " | ".join(result["warnings"])
                    self.existing_detect_var.set(msg)
                else:
                    self.existing_detect_var.set("마스터 불일치: " + " | ".join(result["errors"]))
            except Exception as exc:
                self.existing_detect_var.set(f"마스터 확인 오류: {exc}")

    def make_existing_instruction(self):
        if not self.existing_source_text:
            messagebox.showwarning("순서 확인", "원본 JSON을 먼저 불러오세요.")
            return
        if not self.existing_master_text:
            self.existing_master_text, path = self._ensure_master(self.existing_channel_id, self.existing_source_text)
            if not self.existing_master_text:
                return
            self.existing_master_var.set(path.name)
        try:
            inst, compat = build_existing_json_upgrade_instruction(
                self.existing_source_text,
                self.existing_master_text,
                self.existing_genre_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("지시문 생성 실패", str(exc))
            return
        self.existing_instruction = inst
        self._put_text(self.existing_output, inst)
        warn = " / ".join(compat.get("warnings") or [])
        self.existing_detect_var.set(
            f"READY: {compat['source']['sourceType']} / {compat['source']['trackCount']}곡 / genre={self.existing_genre_var.get()} / master={compat['master']['vocalMode']}" +
            (f" / {warn}" if warn else "")
        )
        self.existing_active_master_var.set(
            f"사용 마스터: {CHANNEL_LABELS[self.existing_channel_id]} 최신 마스터 + {self.existing_genre_var.get()} Genre Master"
        )
        messagebox.showinfo(
            "생성 완료",
            f"업그레이드 지시문 생성 완료\n{CHANNEL_LABELS[self.existing_channel_id]} + {self.existing_genre_var.get()}",
        )

    def save_existing_instruction(self):
        if not self.existing_instruction:
            self.make_existing_instruction()
        if not self.existing_instruction:
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="01_EXISTING_JSON_UPGRADE_PROMPT.txt", filetypes=[("Text", "*.txt")])
        if p:
            write_text(p, self.existing_instruction)

    def load_existing_result(self):
        if not self.existing_source_text:
            messagebox.showwarning("순서 확인", "먼저 원본 JSON을 불러오세요.")
            return
        p = filedialog.askopenfilename(title="ChatGPT 업그레이드 결과 JSON", filetypes=[("JSON", "*.json"), ("Text", "*.txt"), ("All", "*.*")])
        if not p:
            return
        try:
            final, issues = finalize_existing_upgrade(self.existing_source_text, read_text(p))
        except Exception as exc:
            messagebox.showerror("결과 검증 실패", str(exc))
            return
        self.existing_final = final
        fails = [x for x in issues if x.get("level") == "FAIL"]
        if fails:
            self.existing_result_var.set(f"FAIL {len(fails)}건: " + " | ".join(x.get("code", "") for x in fails[:5]))
            messagebox.showerror("검증 실패", "\n".join(str(x) for x in fails[:12]))
        else:
            size = len(json.dumps(final, ensure_ascii=False).encode("utf-8"))
            self.existing_result_var.set(f"PASS / 15곡 / 원본 콘텐츠 강제보존 / 최종 JSON 약 {size/1024:.1f} KB")
            messagebox.showinfo("검증 완료", "최종 Suno JSON을 저장할 수 있습니다.\n제목/가사/훅/스토리는 원본으로 강제 보존되었습니다.")

    def save_existing_final(self):
        if not self.existing_final:
            messagebox.showwarning("저장", "먼저 ChatGPT 결과 JSON을 불러와 검증하세요.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="UPGRADED_FINAL_SUNO_15TRACKS.json", filetypes=[("JSON", "*.json")])
        if p:
            write_json(p, self.existing_final)
            messagebox.showinfo("저장 완료", f"최종 Suno JSON 저장 완료\n{p}")

    def load_haru_txt(self):
        p = filedialog.askopenfilename(title="Haru Studio TXT 선택", filetypes=[("Text", "*.txt"), ("Markdown", "*.md"), ("JSON", "*.json"), ("All", "*.*")])
        if not p:
            return
        self.haru_text = read_text(p)
        self.haru_final = None
        self.haru_source_var.set(Path(p).name)

    def _refresh_haru_master(self):
        channel_id = CHANNEL_OPTIONS[self.haru_channel_var.get()]
        self.haru_master_text, path = self._registered_master(channel_id)
        self.haru_master_var.set(
            f"사용 마스터: {CHANNEL_LABELS[channel_id]} 최신 마스터 + {self.haru_genre_var.get()} Genre Master"
            if path else f"사용 마스터: {CHANNEL_LABELS[channel_id]} 미등록"
        )

    def manage_haru_master(self):
        channel_id = CHANNEL_OPTIONS[self.haru_channel_var.get()]
        text, path = self._choose_and_register_master(channel_id)
        if text:
            self.haru_master_text = text
            self.haru_master_var.set(
                f"사용 마스터: {CHANNEL_LABELS[channel_id]} 최신 마스터 + {self.haru_genre_var.get()} Genre Master"
            )

    def make_haru_instruction(self):
        if not self.haru_text:
            messagebox.showwarning("순서 확인", "Haru Studio TXT를 먼저 불러오세요.")
            return
        channel_id = CHANNEL_OPTIONS[self.haru_channel_var.get()]
        if not self.haru_master_text:
            self.haru_master_text, _path = self._ensure_master(channel_id)
            if not self.haru_master_text:
                return
            self._refresh_haru_master()
        try:
            inst = build_haru_txt_instruction(
                self.haru_text, self.haru_master_text, 15,
                channel_id, self.haru_genre_var.get(),
            )
        except Exception as exc:
            messagebox.showerror("지시문 생성 실패", str(exc))
            return
        self.haru_instruction = inst
        self._put_text(self.haru_output, inst)
        messagebox.showinfo(
            "생성 완료",
            f"신규 15곡 제작 지시문 생성 완료\n{CHANNEL_LABELS[channel_id]} + {self.haru_genre_var.get()}",
        )

    def save_haru_instruction(self):
        if not self.haru_instruction:
            self.make_haru_instruction()
        if not self.haru_instruction:
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="02_HARU_TXT_NEW_15TRACK_PROMPT.txt", filetypes=[("Text", "*.txt")])
        if p:
            write_text(p, self.haru_instruction)

    def load_haru_result(self):
        p = filedialog.askopenfilename(title="ChatGPT 신규 15곡 결과 JSON", filetypes=[("JSON", "*.json"), ("Text", "*.txt"), ("All", "*.*")])
        if not p:
            return
        try:
            final, issues = finalize_haru_result(read_text(p), 15)
        except Exception as exc:
            messagebox.showerror("결과 검증 실패", str(exc))
            return
        self.haru_final = final
        fails = [x for x in issues if x.get("level") == "FAIL"]
        if fails:
            self.haru_result_var.set(f"FAIL {len(fails)}건: " + " | ".join(x.get("code", "") for x in fails[:5]))
            messagebox.showerror("검증 실패", "\n".join(str(x) for x in fails[:12]))
        else:
            size = len(json.dumps(final, ensure_ascii=False).encode("utf-8"))
            self.haru_result_var.set(f"PASS / 15곡 / title+lyrics+stylePrompt 확인 / 약 {size/1024:.1f} KB")
            messagebox.showinfo("검증 완료", "15곡 완성형 Suno JSON 검증을 통과했습니다.")

    def save_haru_final(self):
        if not self.haru_final:
            messagebox.showwarning("저장", "먼저 ChatGPT 결과 JSON을 불러와 검증하세요.")
            return
        p = filedialog.asksaveasfilename(defaultextension=".json", initialfile="HARU_NEW_FINAL_SUNO_15TRACKS.json", filetypes=[("JSON", "*.json")])
        if p:
            write_json(p, self.haru_final)
            messagebox.showinfo("저장 완료", f"최종 Suno JSON 저장 완료\n{p}")
