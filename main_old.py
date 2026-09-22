import os
import json
import time
import random
import tkinter as tk
from tkinter import messagebox

import pygame
from PIL import Image, ImageTk

import sys
import subprocess
import platform


def _is_windows():
    return platform.system() == "Windows"


def shutdown_pc(delay_sec=60):
    """Выключает ПК через delay_sec секунд."""
    if not _is_windows():
        return False
    try:
        subprocess.run(
            ["shutdown", "/s", "/t", str(int(delay_sec))],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception as e:
        print(f"shutdown error: {e}")
        return False


def cancel_shutdown():
    """Отменяет запланированное выключение."""
    if not _is_windows():
        return False
    try:
        subprocess.run(
            ["shutdown", "/a"],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def restart_pc(delay_sec=60):
    """Перезагрузка через delay_sec секунд."""
    if not _is_windows():
        return False
    try:
        subprocess.run(
            ["shutdown", "/r", "/t", str(int(delay_sec))],
            check=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False

def resource_path(filename):
    """Возвращает путь к файлу — работает и в PyCharm, и внутри exe."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return filename

pygame.mixer.init()

# ---------- Палитра ----------
COLOR_BORDER       = "#e0a13c"
COLOR_BORDER_HOVER = "#ffcb6b"
COLOR_PANEL        = "#150b06"
COLOR_TEXT         = "#f4ead8"
COLOR_TEXT_DIM     = "#a89578"
COLOR_ACCENT       = "#ff7a55"

TRANSPARENT_KEY    = "#010101"

UI_FONT       = ("Courier New", 11, "bold")
UI_FONT_SMALL = ("Courier New", 9, "bold")

# ---- Тайминги ----
DEBUG_FAST = False

if DEBUG_FAST:
    T_IDLE_TO_YAWN   = 1500
    T_LOOK_INTERVAL  = 4000
    T_TO_UPSET       = 12000
    T_TO_SLEEP       = 8000
    T_LOOK_DURATION  = 700
    T_YAWN_DURATION  = 800
else:
    T_IDLE_TO_YAWN   = 5000
    T_LOOK_INTERVAL  = 60000
    T_TO_UPSET       = 300000
    T_TO_SLEEP       = 60000
    T_LOOK_DURATION  = 1000
    T_YAWN_DURATION  = 1500


class NicoClickerWidget:
    def __init__(self, root):
        self.root = root
        self.root.title("Nico Clicker Widget")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg='black')
        self.root.wm_attributes('-transparentcolor', 'black')

        self.save_file = "nico_save.json"
        self.click_count = self.load_save()
        self.drag_data = {"x": 0, "y": 0}
        self.menu_open = False
        self.bsod_active = False
        self.ui_visible = False
        self._hide_timer = None
        self.timer_sleep = None
        self.sleeping = False
        self.speech_window = None
        self.speech_timer = None

        self.timer_5s = None
        self.timer_look = None
        self.timer_upset = None

        self.click_times = []
        self.wtf_active = False
        self.wtf_timer = None
        self.pancake_active = False
        self.pancake_timer = None

        self.minigame = None

        self.check_files([
            resource_path("Niko_83c.png"),
            resource_path("Niko_speak.png"),
            resource_path("Niko_wtf2.png"),
            resource_path("Niko_yawn.png"),
            resource_path("Niko.png"),
            resource_path("Niko_eyeclosed.png"),
            resource_path("Niko_upset_meow.png"),
            resource_path("Niko_pancakes.png"),
            resource_path("oneshot-meow-2 (1).mp3"),
        ])

        self.img_active = ImageTk.PhotoImage(Image.open(resource_path("Niko_83c.png")))
        self.img_speak = ImageTk.PhotoImage(Image.open(resource_path("Niko_speak.png")))
        self.img_yawn = ImageTk.PhotoImage(Image.open(resource_path("Niko_yawn.png")))
        self.img_default = ImageTk.PhotoImage(Image.open(resource_path("Niko.png")))
        self.img_pancakes = ImageTk.PhotoImage(Image.open(resource_path("Niko_pancakes.png")))
        self.img_sleep = ImageTk.PhotoImage(Image.open(resource_path("Niko_eyeclosed.png")))
        self.img_wtf = ImageTk.PhotoImage(Image.open(resource_path("Niko_wtf2.png")))
        self.img_default_flip = ImageTk.PhotoImage(
            Image.open(resource_path("Niko.png")).transpose(Image.FLIP_LEFT_RIGHT))
        self.img_upset = ImageTk.PhotoImage(Image.open(resource_path("Niko_upset_meow.png")))

        self.sound = pygame.mixer.Sound(resource_path("oneshot-meow-2 (1).mp3"))

        # ----- Основное окно: только Нико -----
        self.label_image = tk.Label(self.root, image=self.img_active, bg='black')
        self.label_image.pack()

        # ----- Окно UI: фон прозрачный -----
        self.ui_window = tk.Toplevel(self.root)
        self.ui_window.overrideredirect(True)
        self.ui_window.attributes("-topmost", True)
        self.ui_window.config(bg=TRANSPARENT_KEY)
        self.ui_window.wm_attributes('-transparentcolor', TRANSPARENT_KEY)
        self._build_ui(self.ui_window)
        self.ui_window.withdraw()

        # ----- Hover с задержкой -----
        for w in (self.root, self.ui_window):
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

        self.start_idle_timers()

        self.label_image.bind("<Button-1>", self.on_click)
        self.label_image.bind("<ButtonPress-3>", self.start_drag)
        self.label_image.bind("<B3-Motion>", self.drag)
        self.label_image.bind("<Double-Button-3>", lambda e: self.quit_app())

        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)

    # ================= UI =================
    def _build_ui(self, parent):
        row = tk.Frame(parent, bg=TRANSPARENT_KEY)
        row.pack(padx=4, pady=(4, 2))
        row.bind("<ButtonPress-3>", self.start_drag)
        row.bind("<B3-Motion>", self.drag)

        counter_outer, counter_inner = self._make_panel(row, pad_x=7, pad_y=2)
        counter_outer.pack(side="left")
        self.label_counter = tk.Label(
            counter_inner, text=f"{self.click_count}",
            font=UI_FONT, fg=COLOR_TEXT, bg=COLOR_PANEL,
            width=4, anchor="e"
        )
        self.label_counter.pack()

        self.btn_outer, btn_inner = self._make_panel(row, pad_x=4, pad_y=3)
        self.btn_outer.pack(side="left", padx=(5, 0))
        self.menu_button = tk.Canvas(
            btn_inner, width=16, height=12, bg=COLOR_PANEL,
            highlightthickness=0, cursor="hand2"
        )
        self.menu_button.pack()
        self._draw_hamburger(COLOR_BORDER)
        self._bind_menu_hover(self.btn_outer, self.menu_button, btn_inner)

        for w in (self.btn_outer, btn_inner, self.menu_button):
            w.bind("<Button-1>", self.toggle_menu)
            w.bind("<ButtonPress-3>", self.start_drag)
            w.bind("<B3-Motion>", self.drag)

        # Поле ввода
        entry_outer, entry_inner = self._make_panel(parent, pad_x=5, pad_y=2)
        entry_outer.pack(padx=4, pady=(0, 4))
        self.entry_command = tk.Entry(
            entry_inner, font=UI_FONT_SMALL,
            bg=COLOR_PANEL, fg=COLOR_TEXT,
            insertbackground=COLOR_BORDER,
            relief="flat", bd=0, width=13,
            highlightthickness=0
        )
        self.entry_command.pack()
        self.entry_command.bind("<Return>", self.process_command)
        self.entry_command.bind("<Escape>", lambda e: self.entry_command.delete(0, tk.END))
        self.entry_command.bind("<ButtonPress-3>", self.start_drag)
        self.entry_command.bind("<B3-Motion>", self.drag)

        # Меню команд
        self.menu_frame = tk.Frame(parent, bg=COLOR_BORDER, padx=2, pady=2)
        menu_inner = tk.Frame(self.menu_frame, bg=COLOR_PANEL)
        menu_inner.pack(fill="both", expand=True)

        tk.Label(menu_inner, text="ДОСТУПНЫЕ КОМАНДЫ",
                 font=UI_FONT_SMALL, bg=COLOR_PANEL, fg=COLOR_BORDER,
                 pady=5, padx=8, anchor="w").pack(fill="x")
        tk.Frame(menu_inner, bg=COLOR_BORDER, height=1).pack(fill="x", padx=6)

        for cmd in [
            "привет / hi / hello", "как дела / как ты", "пока / bye",
            "спасибо / thanks", "кто ты / who are you", "что делаешь",
            "скучно", "люблю / love", "мяу / meow", "панкейк / pancake",
            "выключи пк", "перезагрузка", "отмена",
        ]:
            tk.Label(menu_inner, text=f"· {cmd}",
                     font=UI_FONT_SMALL, bg=COLOR_PANEL, fg=COLOR_TEXT_DIM,
                     anchor="w", padx=10, pady=0).pack(fill="x")

        tk.Frame(menu_inner, bg=COLOR_BORDER, height=1).pack(fill="x", padx=6, pady=(5, 0))

        # ---- Кнопка мини-игры ----
        game_btn = tk.Label(
            menu_inner, text="🎮  Мини-игра",
            font=UI_FONT_SMALL, bg=COLOR_PANEL, fg=COLOR_BORDER,
            cursor="hand2", pady=5, anchor="center"
        )
        game_btn.pack(fill="x")
        game_btn.bind("<Button-1>", lambda e: self.start_minigame())
        game_btn.bind("<Enter>", lambda e, b=game_btn: b.config(fg=COLOR_BORDER_HOVER))
        game_btn.bind("<Leave>", lambda e, b=game_btn: b.config(fg=COLOR_BORDER))

        tk.Frame(menu_inner, bg=COLOR_BORDER, height=1).pack(fill="x", padx=6, pady=(0, 5))

        close_btn = tk.Label(menu_inner, text="✕  ЗАКРЫТЬ",
                             font=UI_FONT_SMALL, bg=COLOR_PANEL, fg=COLOR_ACCENT,
                             cursor="hand2", pady=5, anchor="center")
        close_btn.pack(fill="x")
        close_btn.bind("<Button-1>", self.toggle_menu)
        close_btn.bind("<Enter>", lambda e, b=close_btn: b.config(fg=COLOR_BORDER_HOVER))
        close_btn.bind("<Leave>", lambda e, b=close_btn: b.config(fg=COLOR_ACCENT))

    def _make_panel(self, parent, pad_x=0, pad_y=0, border=2):
        outer = tk.Frame(parent, bg=COLOR_BORDER, padx=border, pady=border)
        inner = tk.Frame(outer, bg=COLOR_PANEL, padx=pad_x, pady=pad_y)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def _draw_hamburger(self, color):
        self.menu_button.delete("all")
        for y in (1, 5, 9):
            self.menu_button.create_rectangle(1, y, 15, y + 2, fill=color, outline="")

    def _bind_menu_hover(self, outer, canvas, inner):
        def enter(_=None):
            outer.config(bg=COLOR_BORDER_HOVER)
            self._draw_hamburger(COLOR_BORDER_HOVER)
        def leave(_=None):
            outer.config(bg=COLOR_BORDER)
            self._draw_hamburger(COLOR_BORDER)
        for w in (outer, canvas, inner):
            w.bind("<Enter>", enter)
            w.bind("<Leave>", leave)

    # ================= Показ / скрытие UI =================
    def _on_enter(self, event=None):
        if self._hide_timer:
            self.root.after_cancel(self._hide_timer)
            self._hide_timer = None
        self._show_ui()

    def _on_leave(self, event=None):
        if self._hide_timer:
            self.root.after_cancel(self._hide_timer)
        self._hide_timer = self.root.after(350, self._hide_ui)

    def _reposition_ui(self):
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rh = self.root.winfo_height()
        self.ui_window.geometry(f"+{rx}+{ry + rh - 4}")

    def _show_ui(self):
        if self.ui_visible:
            return
        self._reposition_ui()
        self.ui_window.deiconify()
        self.ui_visible = True

    def _hide_ui(self):
        self._hide_timer = None
        if not self.ui_visible:
            return
        if self.menu_open:
            self.menu_frame.pack_forget()
            self.menu_open = False
        self.ui_window.withdraw()
        self.ui_visible = False

    # ================= Меню команд =================
    def toggle_menu(self, event=None):
        if self.menu_open:
            self.menu_frame.pack_forget()
            self.menu_open = False
        else:
            self.menu_frame.pack(pady=2, before=self.entry_command)
            self.menu_open = True
        self.ui_window.update_idletasks()
        self._reposition_ui()

    # ================= Сохранение =================
    def load_save(self):
        try:
            if os.path.exists(self.save_file):
                with open(self.save_file, 'r') as f:
                    return json.load(f).get("click_count", 0)
        except (json.JSONDecodeError, IOError):
            pass
        return 0

    def save_game(self):
        try:
            with open(self.save_file, 'w') as f:
                json.dump({"click_count": self.click_count, "last_saved": "auto"}, f, indent=4)
            return True
        except IOError:
            return False

    def quit_app(self):
        self._hide_speech_bubble()
        if self.minigame:
            self.minigame.close()
        if self.save_game():
            print(f"Прогресс сохранён: {self.click_count} кликов")
        self.root.destroy()

    def check_files(self, files):
        missing = [f for f in files if not os.path.exists(f)]
        if missing:
            messagebox.showerror("Ошибка", f"Не найдены файлы:\n{', '.join(missing)}")
            self.root.destroy()
            exit()

    # ================= Бездействие =================
    def _cancel_idle_timers(self):
        for name in ("timer_5s", "timer_look", "timer_upset", "timer_sleep"):
            t = getattr(self, name)
            if t:
                self.root.after_cancel(t)
                setattr(self, name, None)

    def start_idle_timers(self):
        self._cancel_idle_timers()
        self.timer_5s = self.root.after(T_IDLE_TO_YAWN, self.go_to_yawn_state)

    def go_to_yawn_state(self):
        self.label_counter.config(fg=COLOR_TEXT, text=f"{self.click_count}")
        self.label_image.config(image=self.img_yawn)
        self.timer_5s = None
        self.root.after(T_YAWN_DURATION, self.start_default_idle)

    def start_default_idle(self):
        self.label_image.config(image=self.img_default)
        self.timer_look = self.root.after(T_LOOK_INTERVAL, self.look_right)
        self.timer_upset = self.root.after(T_TO_UPSET, self.go_to_upset_state)

    def look_right(self):
        self.label_image.config(image=self.img_default_flip)
        self.timer_look = self.root.after(T_LOOK_DURATION, self.look_left)

    def look_left(self):
        self.label_image.config(image=self.img_default)
        self.timer_look = self.root.after(T_LOOK_INTERVAL, self.look_right)

    def go_to_upset_state(self):
        if self.timer_look:
            self.root.after_cancel(self.timer_look)
            self.timer_look = None
        self.label_image.config(image=self.img_upset)
        self.timer_upset = None
        if self.timer_sleep:
            self.root.after_cancel(self.timer_sleep)
        self.timer_sleep = self.root.after(T_TO_SLEEP, self.go_to_sleep_state)

    def go_to_sleep_state(self):
        self.sleeping = True
        self.label_image.config(image=self.img_sleep)
        self.timer_sleep = None

    # ================= Мини-игра =================
    def start_minigame(self):
        if self.minigame is not None:
            return
        self._hide_ui()
        self.ui_window.withdraw()

        # Запоминаем позицию (пригодится, если будем двигать)
        self._nico_saved_pos = (self.root.winfo_x(), self.root.winfo_y())

        # Просто убираем Нико с глаз — окно остаётся, но полностью прозрачное
        self.root.attributes("-alpha", 0.0)

        self.minigame = PancakeMinigame(self.root, self, on_close=self._end_minigame)

    def _end_minigame(self):
        self.minigame = None
        if hasattr(self, "_nico_saved_pos"):
            x, y = self._nico_saved_pos
            self.root.geometry(f"+{x}+{y}")
        self.root.attributes("-alpha", 1.0)
        self.root.deiconify()
        self.root.attributes("-topmost", True)
        self.save_game()

    # ================= BSOD =================
    def show_bsod(self):
        if self.bsod_active:
            return
        self.bsod_active = True
        self.bsod_window = tk.Toplevel(self.root)
        self.bsod_window.attributes("-fullscreen", True)
        self.bsod_window.attributes("-topmost", True)
        self.bsod_window.config(bg='#0000AA')

        main_frame = tk.Frame(self.bsod_window, bg='#0000AA')
        main_frame.pack(expand=True, fill='both')

        texts = [
            ("A problem has been detected and Niko has been shut down to prevent damage to your computer.",
             ("Consolas", 16, "bold"), (40, 20)),
            ("NIKO_IRREVERSIBLE_ERROR",
             ("Consolas", 20, "bold"), (10, 10)),
            ("Technical information:\n\n*** STOP: 0x000000FE (0x00000001, 0x00000002, 0x00000003, 0x00000004)\n\n"
             "*** NIKO.sys - Address F7A8B5C0 base at F7A00000, DateStamp 4a5b1c2d",
             ("Consolas", 14), (10, 10)),
            ("Physical memory dump:\n  Contact your system administrator or technical support group for further assistance.",
             ("Consolas", 14), (10, 10)),
        ]
        for text, font, pady in texts:
            tk.Label(main_frame, text=text, font=font, fg="white", bg='#0000AA',
                     justify="left", wraplength=800).pack(anchor='w', padx=50, pady=pady)

        progress_frame = tk.Frame(main_frame, bg='#0000AA')
        progress_frame.pack(anchor='w', padx=50, pady=20)
        tk.Label(progress_frame, text="Dumping physical memory to disk:",
                 font=("Consolas", 14), fg="white", bg='#0000AA').pack(side='left')
        self.progress_value = 0
        self.progress_text = tk.Label(progress_frame, text=" 0%",
                                      font=("Consolas", 14, "bold"),
                                      fg="white", bg='#0000AA')
        self.progress_text.pack(side='left', padx=(10, 0))
        self.animate_bsod_progress()

        tk.Label(main_frame,
                 text="Contact your system administrator or technical support group for further assistance.",
                 font=("Consolas", 14), fg="white", bg='#0000AA',
                 justify="left", wraplength=800).pack(anchor='w', padx=50, pady=(20, 10))
        tk.Label(main_frame, text="Press any key or click to restart Niko...",
                 font=("Consolas", 14, "bold"), fg="#FFFFFF", bg='#0000AA',
                 justify="left", wraplength=800).pack(anchor='w', padx=50, pady=10)

        for w in (self.bsod_window, main_frame):
            w.bind("<Button-1>", self.close_bsod)
            w.bind("<Key>", self.close_bsod)
        self.root.after(15000, self.close_bsod)

    def close_bsod(self, event=None):
        if not self.bsod_active:
            return
        self.bsod_active = False
        if hasattr(self, 'bsod_window') and self.bsod_window.winfo_exists():
            self.bsod_window.destroy()
        self.root.focus_force()

    def animate_bsod_progress(self):
        if not self.bsod_active:
            return
        self.progress_value = min(100, self.progress_value + random.randint(2, 8))
        self.progress_text.config(text=f"{self.progress_value:3d}%")
        if self.progress_value < 100:
            self.root.after(random.randint(100, 300), self.animate_bsod_progress)

    # ================= Команды =================
    # ================= Команды =================
    # ================= Команды =================
    def process_command(self, event):
        command = self.entry_command.get().strip().lower()
        self.entry_command.delete(0, tk.END)
        if not command:
            return

        if self._handle_system_command(command):
            return

        bad_words = [
            "хуй", "хуя", "хую", "хуем", "хуе",
            "пизда", "пизду", "пиздой", "пизде",
            "блядь", "блять", "бля",
            "ебать", "ебаный", "ебанный", "ебаться",
            "сука", "суки", "суке",
            "гандон", "гандона",
            "мудак", "мудака", "мудаку",
            "ублюдок", "ублюдка",
            "тварь", "твари",
            "шлюха", "шлюху", "шлюхой",
            "курва", "курвы",
            "залупа", "залупой",
            "манда", "манду",
            "fuck", "fucking", "fucker",
            "shit", "shitty", "asshole", "bastard",
            "bitch", "bitching", "cunt", "dick", "cock",
            "pussy", "motherfucker",
        ]
        if any(bw in command for bw in bad_words):
            self.show_bsod()
            return

        responses = {
            "привет": "Привет!",
            "hi": "Hi there!",
            "hello": "Hello!",
            "пока": "Пока!",
            "bye": "Bye!",
            "спасибо": "Пожалуйста!",
            "thanks": "Welcome!",
            "thank you": "Anytime!",
            "кто ты": "Я Нико из OneShot!",
            "who are you": "I'm Niko from OneShot!",
            "что делаешь": "Жду кликов!",
            "скучно": "Покликай меня!",
            "люблю": "Люблю тебя! ❤",
            "love": "Love you! ❤",
            "мяу": "Мяу! 🐱",
            "meow": "Meow! 🐱",
            "панкейк": "Обожаю панкейки! 🥞",
            "pancake": "I love pancakes! 🥞",

            "как дела": {
                "text": "Хорошо! А у тебя?",
                "replies": ["тоже хорошо", "не очень", "нормально"]
            },
            "как ты": {
                "text": "Я в порядке! А ты как?",
                "replies": ["тоже хорошо", "не очень", "нормально"]
            },
            "тоже хорошо": {
                "text": "Ура! Тогда давай кликать!",
                "replies": ["давай", "дай панкейк"]
            },
            "не очень": {
                "text": "Ой... Хочешь, я тебя обниму?",
                "replies": ["да", "нет"]
            },
            "нормально": {
                "text": "Ну, тоже неплохо. Расскажешь что-нибудь?",
                "replies": ["да", "нет"]
            },
            "давай": "Тогда кликай меня! 🐾",
            "дай панкейк": "Лови! 🥞",
            "да": "Я так и знал! ❤",
            "нет": "Ну ладно...",
        }

        matched = None
        for key, value in responses.items():
            if key in command:
                matched = value
                break

        if matched is None:
            self.niko_speak(random.choice([
                "Хм...", "Расскажи!", "Не понимаю...",
                "Покликаем!", "Загадочно!", "Давай другое!"
            ]))
            return

        if isinstance(matched, dict):
            self.niko_speak(matched["text"], replies=matched.get("replies"))
        else:
            self.niko_speak(matched)

    def niko_speak(self, text, replies=None):
        self.label_image.config(image=self.img_speak)
        self._show_speech_bubble(text, replies=replies)
        self.sound.play()
        ms = int(self.sound.get_length() * 1000)
        if ms > 0:
            self.root.after(ms, self.reset_to_active)
        self.start_idle_timers()

    # ================= Речевое облако =================
    def _show_speech_bubble(self, text, duration_ms=4000, replies=None):
        self._hide_speech_bubble()

        self.speech_window = tk.Toplevel(self.root)
        self.speech_window.overrideredirect(True)
        self.speech_window.attributes("-topmost", True)
        self.speech_window.config(bg=TRANSPARENT_KEY)
        self.speech_window.wm_attributes('-transparentcolor', TRANSPARENT_KEY)

        border = tk.Frame(self.speech_window, bg=COLOR_BORDER, padx=2, pady=2)
        border.pack()
        bubble = tk.Frame(border, bg=COLOR_PANEL, padx=10, pady=7)
        bubble.pack()

        label = tk.Label(
            bubble, text=text,
            font=("Courier New", 10, "bold"),
            fg=COLOR_TEXT, bg=COLOR_PANEL,
            justify="left", wraplength=200
        )
        label.pack()

        if replies:
            sep = tk.Frame(bubble, bg=COLOR_BORDER, height=1)
            sep.pack(fill="x", pady=(7, 6))
            for rep in replies:
                btn = tk.Label(
                    bubble, text=f"▶ {rep}",
                    font=("Courier New", 9, "bold"),
                    fg=COLOR_TEXT_DIM, bg=COLOR_PANEL,
                    cursor="hand2", anchor="w", padx=4, pady=2
                )
                btn.pack(fill="x")
                btn.bind("<Enter>", lambda e, b=btn: b.config(fg=COLOR_BORDER_HOVER))
                btn.bind("<Leave>", lambda e, b=btn: b.config(fg=COLOR_TEXT_DIM))
                btn.bind("<Button-1>", lambda e, r=rep: self._on_reply_clicked(r))
            duration_ms = max(duration_ms, 8000)

        self.speech_window.update_idletasks()
        bw = self.speech_window.winfo_reqwidth()
        bh = self.speech_window.winfo_reqheight()

        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()

        screen_w = self.root.winfo_screenwidth()
        place_right = (rx + rw + bw + 10) < screen_w

        if place_right:
            tail_text = "◀"
        else:
            tail_text = "▶"

        by = ry + 10
        if by + bh > self.root.winfo_screenheight():
            by = self.root.winfo_screenheight() - bh - 10

        tail = tk.Label(
            self.speech_window, text=tail_text,
            font=("Courier New", 14, "bold"),
            fg=COLOR_BORDER, bg=TRANSPARENT_KEY
        )
        tail.pack(side="left" if place_right else "right", anchor="n", pady=(20, 0))

        self.speech_window.update_idletasks()
        bw = self.speech_window.winfo_reqwidth()
        bx = rx + rw - 5 if place_right else rx - bw + 5

        self.speech_window.geometry(f"+{bx}+{by}")

        if not replies:
            self.speech_timer = self.root.after(duration_ms, self._hide_speech_bubble)

    def _on_reply_clicked(self, reply_text):
        self._hide_speech_bubble()
        self.entry_command.delete(0, tk.END)
        self.entry_command.insert(0, reply_text)
        self.process_command(None)

    # ================= Системные команды =================
    def _handle_system_command(self, command):
        """Обработка команд выключения/перезагрузки/отмены.
        Возвращает True, если команда распознана."""

        # --- Отмена ---
        if command in ("отмена", "отменить", "cancel", "стоп"):
            if getattr(self, "_shutdown_pending", False):
                self._shutdown_pending = False
                if cancel_shutdown():
                    self.niko_speak("Отменил выключение! 😌")
                else:
                    self.niko_speak("Хм, нечего отменять...")
                return True
            if getattr(self, "_restart_pending", False):
                self._restart_pending = False
                if cancel_shutdown():
                    self.niko_speak("Отменил перезагрузку! 😌")
                else:
                    self.niko_speak("Хм, нечего отменять...")
                return True
            return False

        # --- Подтверждение выключения ---
        if getattr(self, "_shutdown_pending", False) and command in (
            "да, выключай", "да выключай", "да", "yes"
        ):
            self._shutdown_pending = False
            self.save_game()
            self.niko_speak("Спокойной ночи! 🌙")
            self.root.after(2500, lambda: shutdown_pc(60))
            return True

        # --- Подтверждение перезагрузки ---
        if getattr(self, "_restart_pending", False) and command in (
            "да, перезагружай", "да перезагружай", "да", "yes"
        ):
            self._restart_pending = False
            self.save_game()
            self.niko_speak("Перезагружаюсь! 🔄")
            self.root.after(2500, lambda: restart_pc(60))
            return True

        # --- Запрос выключения ---
        if command in ("выключи пк", "выключи компьютер", "shutdown", "выключение"):
            self._shutdown_pending = True
            self.niko_speak(
                "Точно выключить компьютер?\nНапиши 'да, выключай' или 'отмена'"
            )
            self.root.after(15000, lambda: setattr(self, "_shutdown_pending", False))
            return True

        # --- Запрос перезагрузки ---
        if command in ("перезагрузка", "перезагрузи", "reboot", "restart"):
            self._restart_pending = True
            self.niko_speak(
                "Перезагрузить компьютер?\nНапиши 'да, перезагружай' или 'отмена'"
            )
            self.root.after(15000, lambda: setattr(self, "_restart_pending", False))
            return True

        return False

    def _hide_speech_bubble(self):
        if self.speech_timer:
            self.root.after_cancel(self.speech_timer)
            self.speech_timer = None
        if self.speech_window is not None and self.speech_window.winfo_exists():
            self.speech_window.destroy()
        self.speech_window = None

    # ================= Клик =================
    def on_click(self, event):
        if self.wtf_active or self.pancake_active:
            return

        if self.sleeping:
            self.sleeping = False
            if self.timer_sleep:
                self.root.after_cancel(self.timer_sleep)
                self.timer_sleep = None

        now = time.time()
        self.click_times.append(now)
        self.click_times = [t for t in self.click_times if now - t <= 1.0]

        if len(self.click_times) >= 6:
            self.trigger_wtf()
            return

        self.click_count += 1
        self.label_counter.config(text=f"{self.click_count}", fg=COLOR_TEXT)
        self.sound.play()

        if self.click_count % 50 == 0:
            self.save_game()
            self.trigger_pancakes()
            return

        self.label_image.config(image=self.img_speak)
        self.start_idle_timers()
        ms = int(self.sound.get_length() * 1000)
        if ms > 0:
            self.root.after(ms, self.reset_to_active)

    def trigger_wtf(self):
        self.wtf_active = True
        self._cancel_idle_timers()
        if self.wtf_timer:
            self.root.after_cancel(self.wtf_timer)
        self.label_image.config(image=self.img_wtf)
        self.wtf_timer = self.root.after(2000, self.end_wtf)

    def end_wtf(self):
        self.wtf_active = False
        self.wtf_timer = None
        self.click_times.clear()
        self.label_image.config(image=self.img_active)
        self.start_idle_timers()

    def trigger_pancakes(self):
        self.pancake_active = True
        self._cancel_idle_timers()
        if self.pancake_timer:
            self.root.after_cancel(self.pancake_timer)
        self.label_image.config(image=self.img_pancakes)
        self.pancake_timer = self.root.after(2000, self.end_pancakes)

    def end_pancakes(self):
        self.pancake_active = False
        self.pancake_timer = None
        self.label_image.config(image=self.img_active)
        self.start_idle_timers()

    # ================= Всплывающий текст =================
    def create_floating_text(self, text, color, size):
        if len(text) > 15: size = 10
        if len(text) > 25: size = 8
        if len(text) > 35: size = 7

        if len(text) > 20:
            words = text.split()
            lines, cur = [], ""
            for w in words:
                if len(cur) + len(w) + 1 <= 20:
                    cur = f"{cur} {w}".strip()
                else:
                    lines.append(cur); cur = w
            if cur: lines.append(cur)
            text = "\n".join(lines)

        pop_label = tk.Label(
            self.root, text=text, font=("Courier New", size, "bold"),
            fg=color, bg="black", justify="center", wraplength=180
        )
        self.root.update_idletasks()
        x = max(5, (self.root.winfo_width() - pop_label.winfo_reqwidth()) // 2)
        y = max(5, (self.root.winfo_height() - pop_label.winfo_reqheight()) // 2)
        pop_label.place(x=x, y=y)
        self.animate_floating_text(pop_label, y, 0)

    def animate_floating_text(self, label, current_y, step):
        if step < 60:
            label.place(y=current_y - 2)
            if step == 40:
                label.config(fg="#666666")
            self.root.after(35, self.animate_floating_text, label, current_y - 2, step + 1)
        else:
            label.destroy()

    def reset_to_active(self):
        if self.wtf_active or self.pancake_active or self.sleeping:
            return
        self.label_image.config(image=self.img_active)

    # ================= Перетаскивание =================
    def start_drag(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def drag(self, event):
        dx = event.x - self.drag_data["x"]
        dy = event.y - self.drag_data["y"]
        new_x = self.root.winfo_x() + dx
        new_y = self.root.winfo_y() + dy
        self.root.geometry(f"+{new_x}+{new_y}")
        if self.ui_visible:
            self._reposition_ui()


# ================= ОКНО МИНИ-ИГРЫ =================
# ================= ОКНО МИНИ-ИГРЫ =================
class PancakeMinigame:
    def __init__(self, master, main_app, on_close=None):
        self.master = master
        self.main_app = main_app
        self.on_close = on_close

        self.W = 480
        self.H = 360
        self.niko_x = self.W // 2
        self.niko_base_y = self.H - 40       # середина Нико по вертикали
        self.niko_speed = 6                  # px за кадр (60 FPS → ~360 px/сек)

        self.score = 0
        self.caught = 0
        self.lives = 3
        self.running = True
        self.pancakes = []
        self.spawn_timer = None
        self.update_timer = None
        self.left_pressed = False
        self.right_pressed = False

        # ---- уменьшенный спрайт Нико ----
        niko_img = Image.open(resource_path("Niko_speak.png")).resize((64, 64))
        self.niko_sprite = ImageTk.PhotoImage(niko_img)

        # ---- Окно ----
        self.win = tk.Toplevel(master)
        self.win.title("Ловим панкейки")
        self.win.overrideredirect(False)
        self.win.attributes("-topmost", True)
        self.win.config(bg=COLOR_PANEL)
        self.win.geometry(f"{self.W + 4}x{self.H + 60}+500+300")

        self.win.deiconify()
        self.win.lift()
        self.win.focus_force()

        outer = tk.Frame(self.win, bg=COLOR_BORDER, padx=2, pady=2)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=COLOR_PANEL)
        inner.pack(fill="both", expand=True)

        # ---- Заголовок с крестиком ----
        top = tk.Frame(inner, bg=COLOR_PANEL)
        top.pack(fill="x", padx=6, pady=(6, 2))

        self.score_label = tk.Label(
            top, text="Счёт: 0   Жизни: 3",
            font=UI_FONT_SMALL, bg=COLOR_PANEL, fg=COLOR_TEXT
        )
        self.score_label.pack(side="left")

        close_btn = tk.Label(
            top, text="✕", font=("Courier New", 12, "bold"),
            bg=COLOR_PANEL, fg=COLOR_ACCENT, cursor="hand2", padx=6
        )
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.close())
        close_btn.bind("<Enter>", lambda e, b=close_btn: b.config(fg=COLOR_BORDER_HOVER))
        close_btn.bind("<Leave>", lambda e, b=close_btn: b.config(fg=COLOR_ACCENT))

        # ---- Игровое поле ----
        self.canvas = tk.Canvas(
            inner, width=self.W, height=self.H,
            bg="#0b0603", highlightthickness=0
        )
        self.canvas.pack(padx=6, pady=(0, 6))

        # Нико внизу по центру
        self.niko_id = self.canvas.create_image(
            self.niko_x, self.niko_base_y,
            image=self.niko_sprite, anchor="center"
        )

        # ---- Клавиши (с удержанием) ----
        self.win.bind("<KeyPress-Left>",   self._on_left_press)
        self.win.bind("<KeyRelease-Left>", self._on_left_release)
        self.win.bind("<KeyPress-Right>",   self._on_right_press)
        self.win.bind("<KeyRelease-Right>", self._on_right_release)
        self.win.bind("<Escape>", lambda e: self.close())

        # ---- Запуск ----
        self.spawn_timer = self.win.after(800, self._spawn_pancake)
        self.update_timer = self.win.after(30, self._update)
        self.win.after(16, self._move_loop)

    # ---- Клавиши ----
    def _on_left_press(self, event):
        self.left_pressed = True

    def _on_left_release(self, event):
        self.left_pressed = False

    def _on_right_press(self, event):
        self.right_pressed = True

    def _on_right_release(self, event):
        self.right_pressed = False

    def _move_loop(self):
        if not self.running:
            return
        if self.left_pressed:
            self.move_niko(-self.niko_speed)
        if self.right_pressed:
            self.move_niko(self.niko_speed)
        self.win.after(16, self._move_loop)

    def move_niko(self, dx):
        if not self.running:
            return
        self.niko_x = max(32, min(self.W - 32, self.niko_x + dx))
        self.canvas.coords(self.niko_id, self.niko_x, self.niko_base_y)

    # ---- Панкейки ----
    def _spawn_pancake(self):
        if not self.running:
            return
        x = random.randint(30, self.W - 30)
        speed = random.randint(3, 6) + min(4, self.caught // 5)
        pid = self.canvas.create_text(
            x, 20, text="🥞",
            font=("Courier New", 22, "bold"), fill=COLOR_BORDER
        )
        self.pancakes.append({"id": pid, "x": x, "y": 20, "speed": speed})

        interval = max(400, 900 - self.caught * 20)
        self.spawn_timer = self.win.after(interval, self._spawn_pancake)

    def _update(self):
        if not self.running:
            return

        for p in self.pancakes[:]:
            p["y"] += p["speed"]
            self.canvas.coords(p["id"], p["x"], p["y"])

            # поймали
            if (p["y"] >= self.niko_base_y - 20
                    and abs(p["x"] - self.niko_x) < 32):
                self.canvas.delete(p["id"])
                self.pancakes.remove(p)
                self.caught += 1
                self.score += 10
                self.main_app.click_count += 1
                self.main_app.label_counter.config(
                    text=f"{self.main_app.click_count}"
                )
                self._refresh_score()
                continue

            # упал
            if p["y"] > self.H + 20:
                self.canvas.delete(p["id"])
                self.pancakes.remove(p)
                self.lives -= 1
                self._refresh_score()
                if self.lives <= 0:
                    self._game_over()
                    return

        self.update_timer = self.win.after(30, self._update)

    def _refresh_score(self):
        self.score_label.config(
            text=f"Счёт: {self.score}   Жизни: {self.lives}"
        )

    def _game_over(self):
        self.running = False
        self.canvas.create_text(
            self.W // 2, self.H // 2,
            text=f"Игра окончена!\nПоймано: {self.caught}\nСчёт: {self.score}",
            font=("Courier New", 16, "bold"),
            fill=COLOR_TEXT, justify="center"
        )

    def close(self):
        self.running = False
        if self.spawn_timer:
            try:
                self.win.after_cancel(self.spawn_timer)
            except Exception:
                pass
            self.spawn_timer = None
        if self.update_timer:
            try:
                self.win.after_cancel(self.update_timer)
            except Exception:
                pass
            self.update_timer = None
        try:
            self.win.destroy()
        except Exception:
            pass
        if self.on_close:
            self.on_close()


if __name__ == "__main__":
    root = tk.Tk()
    app = NicoClickerWidget(root)
    root.geometry("+500+300")
    root.mainloop()

