#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, Menu
import signal
import sys
import platform
import time
import threading
import os
from subprocess import PIPE

def resource_path(relative_path):
    """ Get absolute path to resource, works for PyInstaller or normal run """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class CustomDialog:
    def __init__(self, parent, title="Set Timer", initialvalue="6.0"):
        self.top = tk.Toplevel(parent)
        self.top.configure(bg='#222222')
        self.top.resizable(False, False)
        self.top.overrideredirect(True)
        self.top.attributes('-topmost', True)
        self.top.transient(parent)

        self.top.geometry('200x100')
        self.top.update_idletasks()
        x = parent.winfo_x()
        y = parent.winfo_y() + parent.winfo_height()
        self.top.geometry(f'200x100+{x}+{y}')

        frame = tk.Frame(self.top, bg='#222222', bd=2, relief='ridge')
        frame.pack(fill='both', expand=True, padx=5, pady=5)

        tk.Label(frame, text="Enter duration (seconds):", bg='#222222', fg='#FFFFFF',
                 font=('Arial', 10)).pack(pady=(5, 2))

        self.entry = tk.Entry(frame, bg='#333333', fg='#FFFFFF', insertbackground='#4CAF50',
                              font=('Arial', 10), justify='center', width=10)
        self.entry.pack(pady=(2, 5))
        self.entry.insert(0, initialvalue)

        button_frame = tk.Frame(frame, bg='#222222')
        button_frame.pack()

        tk.Button(button_frame, text="OK", width=8, command=self.on_ok,
                  bg='#4CAF50', fg='#FFFFFF', activebackground='#66BB6A',
                  font=('Arial', 10)).pack(side=tk.LEFT, padx=3)

        tk.Button(button_frame, text="Cancel", width=8, command=self.on_cancel,
                  bg='#555555', fg='#FFFFFF', activebackground='#777777',
                  font=('Arial', 10)).pack(side=tk.LEFT, padx=3)

        self.result = None

        def set_focus_and_grab():
            try:
                self.top.deiconify()
                self.top.lift()
                self.top.focus_force()
                self.top.grab_set_global()
                self.entry.focus_force()
                self.entry.select_range(0, tk.END)
                self.entry.icursor(tk.END)

            except tk.TclError:
                try:
                    self.top.grab_set()
                    self.entry.focus_set()
                    self.entry.select_range(0, tk.END)

                except tk.TclError:...


        self.top.after(50, set_focus_and_grab)
        self.top.after(150, set_focus_and_grab)
        self.top.bind("<Return>", lambda event: self.on_ok())
        self.top.bind("<Escape>", lambda event: self.on_cancel())
        self.top.bind("<FocusIn>", lambda event: print("Dialog window gained focus"))
        self.entry.bind("<FocusIn>", lambda event: print("Entry gained focus"))

        parent.wait_window(self.top)

    def on_ok(self):
        try:
            self.result = float(self.entry.get())
        except ValueError:
            self.result = None
            print("Invalid value entered")
        self.top.destroy()

    def on_cancel(self):
        self.result = None
        self.top.destroy()

class HUDApp:
    def __init__(self, root):
        self.root = root
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self.default_width = 226
        self.default_height = 26
        self.min_width = self.default_width
        self.min_height = self.default_height
        self.max_width = self.default_width * 2
        self.max_height = self.default_height * 2

        mon_x, mon_y, mon_width, mon_height = self.get_primary_monitor_geometry()
        x = mon_x + (mon_width - self.default_width) // 2
        y = mon_y + (mon_height - self.default_height) // 2
        self.base_x = x
        self.base_y = y
        self.root.geometry(f'{self.default_width}x{self.default_height}+{x}+{y}')
        self.root.configure(bg='#222222')
        self.sound_enabled_var = tk.BooleanVar(value=True)

        if platform.system() == "Linux":
            try:
                self.root.tk.call('tk', 'scaling', 1.0)
            except Exception as e:
                print(f"Scaling error: {e}")
        elif platform.system() == "Windows":
            try:
                from ctypes import windll
                windll.shcore.SetProcessDpiAwareness(1)
            except Exception as e:
                print(f"Windows DPI error: {e}")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('green.Horizontal.TProgressbar', troughcolor='#222222', background='#4CAF50',
                            bordercolor='#777777', borderwidth=1)
        self.progress = ttk.Progressbar(root, mode='determinate', maximum=100,
                                        style='green.Horizontal.TProgressbar', orient='horizontal')
        self.progress.place(relx=0, rely=0, relwidth=1.0, relheight=1.0, anchor='nw')

        self.text_canvas = tk.Canvas(self.root, highlightthickness=0, bd=0)
        self.text_canvas.place_forget()

        if platform.system() == "Windows":
            self.menu = None
            self.custom_menu_window = None
        else:
            self.menu = Menu(root, tearoff=0, bg='#222222', fg='#FFFFFF',
                             activebackground='#4CAF50', activeforeground='#FFFFFF',
                             borderwidth=0, relief='flat')
            self.menu.configure(selectcolor='#4CAF50')
            self.menu.add_command(label="Set Timer (seconds)", command=self.set_timer)
            self.menu.add_checkbutton(label="Enable Sound", variable=self.sound_enabled_var, onvalue=True, offvalue=False)
            self.menu.add_command(label="Close", command=self.quit)

        self.progress.bind('<Button-1>', self.start_potential_action)
        self.progress.bind('<ButtonRelease-1>', self.toggle_progress)
        self.progress.bind('<B1-Motion>', self.on_motion)
        self.progress.bind('<Button-3>', self.show_menu)
        self.progress.bind('<Motion>', self.update_cursor)
        self.root.bind('<Button-1>', self.dismiss_menu)
        self.root.bind('<Escape>', lambda e: self.quit())
        self.root.bind('<Configure>', self.on_resize)
        if platform.system() == "Windows":
            self.root.bind_all('<Button-1>', self.global_dismiss_menu)

        self.drag_start_x = 0
        self.drag_start_y = 0
        self.is_dragging = False
        self.is_resizing = False
        self.resize_edge = None
        self.click_x = 0
        self.click_y = 0
        self.resize_margin = 4
        self.menu_is_open = False
        self.menu_was_open_on_click = False

        self.is_running = False
        self.progress_duration = 6.0
        self.update_interval = 8
        self.start_time = None
        self.last_tick_number = -1

        self.root.after(1000, self.ensure_on_top)
        self.startup_effect()

        try:
            signal.signal(signal.SIGINT, self.signal_handler)
        except AttributeError:
            pass

    def play_tick_sound(self):
        if not self.sound_enabled_var.get():
            return
        try:
            sound_file = resource_path('tick.wav')
            if platform.system() == 'Windows':
                import winsound
                winsound.PlaySound(sound_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                if not hasattr(self, 'tick_sound'):
                    os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
                    import contextlib
                    with contextlib.redirect_stdout(open(os.devnull, 'w')):
                        with contextlib.redirect_stderr(open(os.devnull, 'w')):
                            import pygame
                            pygame.mixer.pre_init(frequency=22050, size=-16, channels=2, buffer=512)
                            pygame.mixer.init()
                    self.tick_sound = pygame.mixer.Sound(sound_file)
                self.tick_sound.play()
        except Exception as e:
            print(f"Sound error: {e}")

    def get_primary_monitor_geometry(self):
        if platform.system() == "Windows":
            try:
                from ctypes import windll, Structure, c_long
                class RECT(Structure):
                    _fields_ = [('left', c_long), ('top', c_long), ('right', c_long), ('bottom', c_long)]
                rect = RECT()
                if windll.user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
                    width = rect.right - rect.left
                    height = rect.bottom - rect.top
                    return rect.left, rect.top, width, height
            except Exception as e:
                print(f"Windows monitor detection error: {e}")
        elif platform.system() == "Linux":
            try:
                import subprocess
                result = subprocess.run(['xrandr', '--query'], stdout=PIPE, stderr=PIPE, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if ' connected primary' in line:
                        parts = line.split()
                        for part in parts:
                            if '+' in part and 'x' in part:
                                size, x_offset, y_offset = part.split('+')
                                width, height = map(int, size.split('x'))
                                x = int(x_offset)
                                y = int(y_offset)
                                return x, y, width, height
            except Exception as e:
                print(f"Linux monitor detection error: {e}")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        return 0, 0, screen_width, screen_height

    def signal_handler(self, sig, frame):

        self.quit()

    def quit(self):
        self.is_running = False
        self.dismiss_menu()
        self.root.destroy()
        sys.exit(0)

    def ensure_on_top(self):
        if platform.system() == "Windows" and self.menu_is_open:
            pass
        else:
            self.root.attributes('-topmost', True)
        self.root.after(1000, self.ensure_on_top)

    def show_menu(self, event):
        if self.menu_is_open:
            self.dismiss_menu()
        self.menu_is_open = True
        self.click_x = event.x_root
        self.click_y = event.y_root
        if platform.system() == "Windows":
            self.create_custom_menu(event.x_root, event.y_root)
        else:
            self.menu.post(event.x_root, event.y_root)

    def create_custom_menu(self, x, y):
        if self.custom_menu_window:
            self.custom_menu_window.destroy()
            self.custom_menu_window = None

        self.custom_menu_window = tk.Toplevel(self.root)
        self.custom_menu_window.overrideredirect(True)
        self.custom_menu_window.configure(bg='#222222', highlightthickness=0, bd=0, relief='flat')
        self.custom_menu_window.attributes('-topmost', True)
        self.root.attributes('-topmost', False)
        self.custom_menu_window.lift()

        items = [
            ("Set Timer (seconds)", self.set_timer),
            ("Enable Sound", self.toggle_sound),
            ("Close", self.quit)
        ]

        for i, (label, command) in enumerate(items):
            text = label
            if label == "Enable Sound":
                text = "✓ Enable Sound" if self.sound_enabled_var.get() else "  Enable Sound"

            btn = tk.Label(self.custom_menu_window, text=text, bg='#222222', fg='#FFFFFF',
                           font=('Arial', 9), padx=10, pady=4, anchor='w')
            btn.pack(fill='x')

            if label == "Enable Sound":
                def on_click_sound(e):
                    self.toggle_sound()
                    self.dismiss_menu()
                btn.bind('<Button-1>', on_click_sound)
            else:
                def on_click(e, cmd=command):
                    self.dismiss_menu()
                    cmd()
                btn.bind('<Button-1>', on_click)

            def on_enter(e, btn=btn):
                btn.configure(bg='#4CAF50', fg='#FFFFFF')
            def on_leave(e, btn=btn):
                btn.configure(bg='#222222', fg='#FFFFFF')
            btn.bind('<Enter>', on_enter)
            btn.bind('<Leave>', on_leave)

        self.custom_menu_window.update_idletasks()
        self.custom_menu_window.geometry(f'+{x}+{y}')


    def toggle_sound(self):
        self.sound_enabled_var.set(not self.sound_enabled_var.get())
        if platform.system() == "Windows" and self.menu_is_open:
            self.dismiss_menu()
            self.menu_is_open = True
            self.create_custom_menu(self.click_x, self.click_y)

    def dismiss_menu(self, event=None):
        if not self.menu_is_open:
            return
        self.menu_is_open = False
        if platform.system() == "Windows":
            self.menu_was_open_on_click = True
            if self.custom_menu_window:
                self.custom_menu_window.destroy()
                self.custom_menu_window = None
            self.root.attributes('-topmost', True)
            self.root.after(200, lambda: setattr(self, 'menu_was_open_on_click', False))
        else:
            self.menu.unpost()
            self.menu_was_open_on_click = False  # Reset immediately for Linux


    def global_dismiss_menu(self, event):
        if self.menu_is_open and platform.system() == "Windows":
            self.dismiss_menu()


    def set_timer(self):
        self.menu_was_open_on_click = False
        dialog = CustomDialog(self.root, initialvalue=str(self.progress_duration))
        if dialog.result is not None and 1.0 <= dialog.result <= 10.0:
            self.progress_duration = dialog.result
            print(f"Set duration: {dialog.result} seconds")
            if self.is_running:
                now = time.perf_counter()
                self.start_time = now - (now % self.progress_duration)
                self.progress['value'] = 0
                self.animate_progress()
        else:
            print("Invalid or cancelled input.")

    def update_cursor(self, event):
        x, y = event.x, event.y
        w, h = self.root.winfo_width(), self.root.winfo_height()
        margin = self.resize_margin

        if x < margin and y < margin:
            self.root.config(cursor='top_left_corner')
        elif x > w - margin and y < margin:
            self.root.config(cursor='top_right_corner')
        elif x < margin and y > h - margin:
            self.root.config(cursor='bottom_left_corner')
        elif x > w - margin and y > h - margin:
            self.root.config(cursor='bottom_right_corner')
        elif x < margin:
            self.root.config(cursor='left_side')
        elif x > w - margin:
            self.root.config(cursor='right_side')
        elif y < margin:
            self.root.config(cursor='top_side')
        elif y > h - margin:
            self.root.config(cursor='bottom_side')
        else:
            self.root.config(cursor='')

    def start_potential_action(self, event):
        if self.menu_is_open:
            self.dismiss_menu()
            self.menu_was_open_on_click = True
            return

        self.menu_was_open_on_click = False
        self.click_x = event.x_root
        self.click_y = event.y_root
        self.drag_start_x = event.x_root - self.root.winfo_x()
        self.drag_start_y = event.y_root - self.root.winfo_y()
        self.is_dragging = False
        self.is_resizing = False
        self.resize_edge = None

        x, y = event.x, event.y
        w, h = self.root.winfo_width(), self.root.winfo_height()
        margin = self.resize_margin

        if x < margin and y < margin:
            self.resize_edge = 'nw'
        elif x > w - margin and y < margin:
            self.resize_edge = 'ne'
        elif x < margin and y > h - margin:
            self.resize_edge = 'sw'
        elif x > w - margin and y > h - margin:
            self.resize_edge = 'se'
        elif x < margin:
            self.resize_edge = 'w'
        elif x > w - margin:
            self.resize_edge = 'e'
        elif y < margin:
            self.resize_edge = 'n'
        elif y > h - margin:
            self.resize_edge = 's'

        if self.resize_edge:
            self.is_resizing = True

    def on_motion(self, event):
        if self.menu_was_open_on_click:
            return
        if self.is_resizing:
            self.handle_resize(event)
        elif abs(event.x_root - self.click_x) > 5 or abs(event.y_root - self.click_y) > 5:
            self.handle_drag(event)

    def handle_drag(self, event):
        try:
            self.is_dragging = True
            x = event.x_root - self.drag_start_x
            y = event.y_root - self.drag_start_y
            self.root.geometry(f'+{x}+{y}')
        except Exception as e:
            print(f"Drag error: {e}")

    def handle_resize(self, event):
        try:
            x, y = event.x_root, event.y_root
            curr_x, curr_y = self.root.winfo_x(), self.root.winfo_y()
            curr_w, curr_h = self.root.winfo_width(), self.root.winfo_height()

            new_w = curr_w
            new_h = curr_h
            new_x = curr_x
            new_y = curr_y

            if 'e' in self.resize_edge:
                new_w = max(self.min_width, min(self.max_width, x - curr_x))
            elif 'w' in self.resize_edge:
                new_w = max(self.min_width, min(self.max_width, curr_w + curr_x - x))
                new_x = x if new_w < self.max_width else curr_x
            if 's' in self.resize_edge:
                new_h = max(self.min_height, min(self.max_height, y - curr_y))
            elif 'n' in self.resize_edge:
                new_h = max(self.min_height, min(self.max_height, curr_h + curr_y - y))
                new_y = y if new_h < self.max_height else curr_y

            self.root.geometry(f'{new_w}x{new_h}+{new_x}+{new_y}')
        except Exception as e:
            print(f"Resize error: {e}")

    def on_resize(self, event):
        self.progress.place_configure(relwidth=1.0, relheight=1.0)
        if self.text_canvas.winfo_ismapped():
            self.text_canvas.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)

    def toggle_progress(self, event):
        if not self.is_dragging and not self.is_resizing and not self.is_animating and not self.menu_is_open and not self.menu_was_open_on_click:
            self.root.config(cursor='')
            if not self.is_running:
                self.is_running = True
                self.start_time = time.perf_counter()
                self.progress['value'] = 0
                self.last_tick_number = -1
                self.animate_progress()
            else:
                self.is_running = False
                self.progress['value'] = 0

    def animate_progress(self):
        if not self.is_running:
            return
        try:
            now = time.perf_counter()
            elapsed = now - self.start_time
            progress = (elapsed % self.progress_duration) / self.progress_duration * 100
            self.progress['value'] = progress
            current_tick_number = int(elapsed // self.progress_duration)
            if current_tick_number != self.last_tick_number:
                self.last_tick_number = current_tick_number
                if self.sound_enabled_var.get():
                    self.play_tick_sound()
            self.root.after(self.update_interval, self.animate_progress)
        except Exception as e:
            print(f"Animation error: {e}")
            self.is_running = False
            self.progress['value'] = 0

    def startup_effect(self):
        import math
        self.animation_step = 0
        self.max_steps = 240
        self.effect_interval = 16
        self.progress['value'] = 0
        self.is_animating = True
        self.original_width = self.default_width
        self.original_height = self.default_height
        self.original_x = self.base_x
        self.original_y = self.base_y
        self.expanded_width = int(self.default_width * 1.5)
        self.expanded_height = int(self.default_height * 1.5)
        self.expanded_x = self.base_x - (self.expanded_width - self.default_width) // 2
        self.expanded_y = self.base_y - (self.expanded_height - self.default_height) // 2
        self.wave_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', '#DDA0DD', '#98D8C8', '#4CAF50']

        def wave_animation():
            if self.animation_step < self.max_steps:
                if self.animation_step < 30:
                    expand_progress = self.animation_step / 30
                    ease_progress = 1 - (1 - expand_progress) ** 3
                    current_width = int(self.original_width + (self.expanded_width - self.original_width) * ease_progress)
                    current_height = int(self.original_height + (self.expanded_height - self.original_height) * ease_progress)
                    current_x = int(self.original_x + (self.expanded_x - self.original_x) * ease_progress)
                    current_y = int(self.original_y + (self.expanded_y - self.original_y) * ease_progress)
                    self.root.geometry(f'{current_width}x{current_height}+{current_x}+{current_y}')
                elif self.animation_step > self.max_steps - 60:
                    shrink_start = self.max_steps - 60
                    shrink_progress = (self.animation_step - shrink_start) / 60
                    ease_progress = shrink_progress ** 2
                    current_width = int(self.expanded_width - (self.expanded_width - self.original_width) * ease_progress)
                    current_height = int(self.expanded_height - (self.expanded_height - self.original_height) * ease_progress)
                    current_x = int(self.expanded_x - (self.expanded_x - self.original_x) * ease_progress)
                    current_y = int(self.expanded_y - (self.expanded_y - self.original_y) * ease_progress)
                    self.root.geometry(f'{current_width}x{current_height}+{current_x}+{current_y}')

                wave_progress = (math.sin(self.animation_step * 0.1) + 1) / 2
                linear_progress = min(1.0, self.animation_step / (self.max_steps - 80))
                combined_progress = (wave_progress * 0.1 + linear_progress * 1) * 100
                color_index = int((self.animation_step / 25) % len(self.wave_colors))
                self.style.configure('green.Horizontal.TProgressbar', background=self.wave_colors[color_index])
                self.progress['value'] = min(combined_progress, 100)

                if self.animation_step > self.max_steps - 80:
                    if self.animation_step == self.max_steps - 79:
                        self.progress['value'] = 100
                        self.style.configure('green.Horizontal.TProgressbar', background=self.wave_colors[-1])
                        self.text_canvas.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
                        self.play_tick_sound()

                    chars_to_show = min(9, (self.animation_step - (self.max_steps - 80)) // 8)
                    text = "T I C K B A R"[:chars_to_show * 2 - 1] if chars_to_show > 0 else ""
                    self.text_canvas.delete("all")
                    if text:
                        window_width = self.root.winfo_width()
                        window_height = self.root.winfo_height()
                        self.text_canvas.create_text(window_width//2, window_height//2,
                                                    text=text, fill='#000000',
                                                    font=('Arial', 10, 'bold'), anchor='center')

                self.animation_step += 1
                self.root.after(self.effect_interval, wave_animation)
            else:
                self.root.geometry(f'{self.original_width}x{self.original_height}+{self.original_x}+{self.original_y}')
                self.text_canvas.place_forget()
                self.progress['value'] = 0
                self.style.configure('green.Horizontal.TProgressbar', background='#4CAF50')
                self.is_animating = False

        self.root.after(0, wave_animation)

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = HUDApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Error starting app: {e}")
        sys.exit(1)