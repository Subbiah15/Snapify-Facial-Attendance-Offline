"""
Face Recognition Attendance System — Unified Launcher
A modern dark-themed GUI that provides one-click access to all workflow steps.
Includes Sign In / Sign Up for teacher accounts with per-teacher data isolation.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
import subprocess
import threading
import os
import sys
import webbrowser
import time
import logging
import sqlite3
import hashlib
import json

# ─── Color Palette ────────────────────────────────────────────────
BG_DARK       = "#0f1117"
BG_CARD       = "#1a1d27"
BG_CARD_HOVER = "#242836"
ACCENT        = "#0078D7"
ACCENT_HOVER  = "#005b9f"
ACCENT_GLOW   = "#0078D7"
SUCCESS       = "#2ea043"
WARNING       = "#f39c12"
ERROR         = "#e74c3c"
TEXT_PRIMARY   = "#e8e8f0"
TEXT_SECONDARY = "#8b8da3"
TEXT_DIM       = "#555770"
BORDER_COLOR   = "#2a2d3a"

# ─── Fonts ────────────────────────────────────────────────────────
FONT_TITLE     = ("Segoe UI", 22, "bold")
FONT_SUBTITLE  = ("Segoe UI", 10)
FONT_STEP_NUM  = ("Segoe UI", 28, "bold")
FONT_STEP_TITLE = ("Segoe UI", 13, "bold")
FONT_STEP_DESC = ("Segoe UI", 9)
FONT_BUTTON    = ("Segoe UI", 10, "bold")
FONT_LOG       = ("Consolas", 9)
FONT_STATUS    = ("Segoe UI", 9)
FONT_AUTH_TITLE = ("Segoe UI", 20, "bold")
FONT_AUTH_LABEL = ("Segoe UI", 11)
FONT_AUTH_BTN   = ("Segoe UI", 11, "bold")
FONT_AUTH_LINK  = ("Segoe UI", 10)

# ─── Database helpers ─────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "attendance.db")


def _init_teachers_table():
    """Create the teachers table if it doesn't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            phone TEXT DEFAULT ''
        )
    """)
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


_init_teachers_table()


class StepCard(tk.Frame):
    """A styled card widget representing one workflow step."""

    def __init__(self, master, step_num, title, description, icon_char, button_text,
                 command, accent_color=ACCENT, **kwargs):
        super().__init__(master, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                         highlightthickness=1, **kwargs)

        self.accent_color = accent_color
        self.command = command
        self.is_running = False

        # ── Left accent bar ──
        accent_bar = tk.Frame(self, bg=accent_color, width=4)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        # ── Main content ──
        content = tk.Frame(self, bg=BG_CARD, padx=18, pady=14)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Top row: step number + title
        top_row = tk.Frame(content, bg=BG_CARD)
        top_row.pack(fill=tk.X)

        step_label = tk.Label(top_row, text=f"0{step_num}", font=FONT_STEP_NUM,
                              fg=accent_color, bg=BG_CARD)
        step_label.pack(side=tk.LEFT, padx=(0, 12))

        title_block = tk.Frame(top_row, bg=BG_CARD)
        title_block.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=4)

        tk.Label(title_block, text=title, font=FONT_STEP_TITLE,
                 fg=TEXT_PRIMARY, bg=BG_CARD, anchor="w").pack(fill=tk.X)
        tk.Label(title_block, text=description, font=FONT_STEP_DESC,
                 fg=TEXT_SECONDARY, bg=BG_CARD, anchor="w", wraplength=320).pack(fill=tk.X)

        # ── Right: button + status ──
        right_frame = tk.Frame(self, bg=BG_CARD, padx=16, pady=14)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.btn = tk.Button(
            right_frame, text=f"  {icon_char}  {button_text}  ",
            font=FONT_BUTTON, fg="white", bg=accent_color,
            activebackground=ACCENT_HOVER, activeforeground="white",
            bd=0, cursor="hand2", padx=16, pady=8,
            command=self._on_click
        )
        self.btn.pack(pady=(4, 6))

        self.status_label = tk.Label(right_frame, text="Ready", font=FONT_STATUS,
                                     fg=TEXT_DIM, bg=BG_CARD)
        self.status_label.pack()

        # Hover effects
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        for widget in [content, top_row, title_block, right_frame]:
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, e):
        self.configure(bg=BG_CARD_HOVER)
        for w in self.winfo_children():
            try:
                w.configure(bg=BG_CARD_HOVER)
                for child in w.winfo_children():
                    try:
                        child.configure(bg=BG_CARD_HOVER)
                        for grandchild in child.winfo_children():
                            try:
                                grandchild.configure(bg=BG_CARD_HOVER)
                            except tk.TclError:
                                pass
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass

    def _on_leave(self, e):
        self.configure(bg=BG_CARD)
        for w in self.winfo_children():
            try:
                w.configure(bg=BG_CARD)
                for child in w.winfo_children():
                    try:
                        child.configure(bg=BG_CARD)
                        for grandchild in child.winfo_children():
                            try:
                                grandchild.configure(bg=BG_CARD)
                            except tk.TclError:
                                pass
                    except tk.TclError:
                        pass
            except tk.TclError:
                pass

    def _on_click(self):
        if not self.is_running:
            self.command(self)

    def set_status(self, text, color=TEXT_DIM):
        self.status_label.configure(text=text, fg=color)

    def set_running(self, running=True):
        self.is_running = running
        if running:
            self.btn.configure(state="disabled", bg=TEXT_DIM)
            self.set_status("⏳ Running...", WARNING)
        else:
            self.btn.configure(state="normal", bg=self.accent_color)


class LauncherApp:
    """Main launcher application."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Face Recognition Attendance System")
        self.root.configure(bg=BG_DARK)
        self.root.geometry("720x820")
        self.root.minsize(680, 740)
        self.root.resizable(True, True)

        # Try to set window icon
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.flask_process = None
        self.project_dir = os.path.dirname(os.path.abspath(__file__))
        self.teacher_email = None  # Set after login

        # Container that holds either auth screens or main UI
        self.main_container = tk.Frame(self.root, bg=BG_DARK)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self._show_signin()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═══════════════════════════════════════════════════════════════
    #  AUTH SCREENS
    # ═══════════════════════════════════════════════════════════════

    def _clear_container(self):
        for w in self.main_container.winfo_children():
            w.destroy()

    def _make_auth_entry(self, parent, label_text, show_char="", row=0):
        """Helper: create a label + entry pair and return the entry."""
        tk.Label(parent, text=label_text, font=FONT_AUTH_LABEL,
                 fg=TEXT_SECONDARY, bg=BG_CARD, anchor="w").grid(
            row=row, column=0, sticky="w", padx=30, pady=(14, 0))
        entry = tk.Entry(parent, font=FONT_AUTH_LABEL, width=30,
                         bg="#12122a", fg=TEXT_PRIMARY, insertbackground=TEXT_PRIMARY,
                         relief="flat", bd=0, highlightthickness=1,
                         highlightcolor=ACCENT, highlightbackground=BORDER_COLOR)
        if show_char:
            entry.configure(show=show_char)
        entry.grid(row=row + 1, column=0, padx=30, pady=(4, 0), ipady=8)
        return entry

    # ── Sign In ───────────────────────────────────────────────────

    def _add_logo(self, parent, size=(120, 120), pady=(40, 0)):
        try:
            logo_path = os.path.join(self.project_dir, "static", "Snapify_Logo.jpeg")
            img = Image.open(logo_path)
            img = img.resize(size, Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            logo_label = tk.Label(parent, image=photo, bg=BG_DARK)
            logo_label.image = photo  # Keep a reference
            logo_label.pack(pady=pady)
        except Exception as e:
            # Fallback
            tk.Label(parent, text="🎯", font=("Segoe UI", 48), bg=BG_DARK).pack(pady=pady)

    def _show_signin(self):
        self._clear_container()
        frame = tk.Frame(self.main_container, bg=BG_DARK)
        frame.pack(expand=True)

        # Logo + title
        self._add_logo(frame, size=(120, 120), pady=(30, 0))
        tk.Label(frame, text="Welcome Back", font=FONT_AUTH_TITLE,
                 fg=TEXT_PRIMARY, bg=BG_DARK).pack(pady=(10, 2))
        tk.Label(frame, text="Sign in to your teacher account", font=FONT_SUBTITLE,
                 fg=TEXT_SECONDARY, bg=BG_DARK).pack(pady=(0, 20))

        # Card
        card = tk.Frame(frame, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                        highlightthickness=1, padx=10, pady=20)
        card.pack(padx=40)

        email_entry = self._make_auth_entry(card, "Email", row=0)
        pass_entry = self._make_auth_entry(card, "Password", show_char="•", row=2)

        self.signin_error = tk.Label(card, text="", font=("Segoe UI", 9),
                                     fg=ERROR, bg=BG_CARD)
        self.signin_error.grid(row=4, column=0, padx=30, pady=(10, 0))

        def do_signin():
            email = email_entry.get().strip()
            pw = pass_entry.get()
            if not email or not pw:
                self.signin_error["text"] = "Please fill in all fields."
                return
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT password_hash FROM teachers WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            if not row:
                self.signin_error["text"] = "No account found with this email."
                return
            if row[0] != _hash_password(pw):
                self.signin_error["text"] = "Incorrect password."
                return
            # Success
            self.teacher_email = email
            self._write_teacher_file()
            self._build_main_ui()

        btn = tk.Button(card, text="  Sign In  ", font=FONT_AUTH_BTN,
                        fg="white", bg=ACCENT, activebackground=ACCENT_HOVER,
                        bd=0, cursor="hand2", padx=20, pady=10,
                        command=do_signin)
        btn.grid(row=5, column=0, padx=30, pady=(20, 10))

        # Bind Enter key
        pass_entry.bind("<Return>", lambda e: do_signin())
        email_entry.bind("<Return>", lambda e: pass_entry.focus())

        # Link to sign up
        link_frame = tk.Frame(card, bg=BG_CARD)
        link_frame.grid(row=6, column=0, pady=(0, 10))
        tk.Label(link_frame, text="Don't have an account?", font=FONT_AUTH_LINK,
                 fg=TEXT_DIM, bg=BG_CARD).pack(side=tk.LEFT)
        signup_link = tk.Label(link_frame, text=" Create Account", font=FONT_AUTH_LINK,
                               fg=ACCENT, bg=BG_CARD, cursor="hand2")
        signup_link.pack(side=tk.LEFT)
        signup_link.bind("<Button-1>", lambda e: self._show_signup())

    # ── Sign Up ───────────────────────────────────────────────────

    def _show_signup(self):
        self._clear_container()
        frame = tk.Frame(self.main_container, bg=BG_DARK)
        frame.pack(expand=True)

        self._add_logo(frame, size=(100, 100), pady=(20, 0))
        tk.Label(frame, text="Create Account", font=FONT_AUTH_TITLE,
                 fg=TEXT_PRIMARY, bg=BG_DARK).pack(pady=(10, 2))
        tk.Label(frame, text="Register as a new teacher", font=FONT_SUBTITLE,
                 fg=TEXT_SECONDARY, bg=BG_DARK).pack(pady=(0, 16))

        card = tk.Frame(frame, bg=BG_CARD, highlightbackground=BORDER_COLOR,
                        highlightthickness=1, padx=10, pady=20)
        card.pack(padx=40)

        email_entry = self._make_auth_entry(card, "Email", row=0)
        phone_entry = self._make_auth_entry(card, "Phone Number", row=2)
        pass_entry = self._make_auth_entry(card, "Password", show_char="•", row=4)
        confirm_entry = self._make_auth_entry(card, "Confirm Password", show_char="•", row=6)

        self.signup_error = tk.Label(card, text="", font=("Segoe UI", 9),
                                     fg=ERROR, bg=BG_CARD)
        self.signup_error.grid(row=8, column=0, padx=30, pady=(10, 0))

        def do_signup():
            email = email_entry.get().strip()
            phone = phone_entry.get().strip()
            pw = pass_entry.get()
            confirm = confirm_entry.get()

            if not email or not pw or not confirm:
                self.signup_error["text"] = "Please fill in all fields."
                return
            if "@" not in email:
                self.signup_error["text"] = "Please enter a valid email."
                return
            if pw != confirm:
                self.signup_error["text"] = "Passwords do not match."
                return
            if len(pw) < 4:
                self.signup_error["text"] = "Password must be at least 4 characters."
                return

            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM teachers WHERE email = ?", (email,))
            if cursor.fetchone():
                conn.close()
                self.signup_error["text"] = "An account with this email already exists."
                return

            cursor.execute("INSERT INTO teachers (email, password_hash, phone) VALUES (?, ?, ?)",
                           (email, _hash_password(pw), phone))
            conn.commit()
            conn.close()

            messagebox.showinfo("Account Created",
                                f"✅ Account created successfully!\n\nEmail: {email}\n\nYou will now be redirected to Sign In.")
            self._show_signin()

        btn = tk.Button(card, text="  Create Account  ", font=FONT_AUTH_BTN,
                        fg="white", bg=SUCCESS, activebackground="#27ae60",
                        bd=0, cursor="hand2", padx=20, pady=10,
                        command=do_signup)
        btn.grid(row=9, column=0, padx=30, pady=(20, 10))

        # Link back to sign in
        link_frame = tk.Frame(card, bg=BG_CARD)
        link_frame.grid(row=10, column=0, pady=(0, 10))
        tk.Label(link_frame, text="Already have an account?", font=FONT_AUTH_LINK,
                 fg=TEXT_DIM, bg=BG_CARD).pack(side=tk.LEFT)
        signin_link = tk.Label(link_frame, text=" Sign In", font=FONT_AUTH_LINK,
                               fg=ACCENT, bg=BG_CARD, cursor="hand2")
        signin_link.pack(side=tk.LEFT)
        signin_link.bind("<Button-1>", lambda e: self._show_signin())

    # ═══════════════════════════════════════════════════════════════
    #  MAIN UI (after login)
    # ═══════════════════════════════════════════════════════════════

    def _build_main_ui(self):
        self._clear_container()

        # ── Header ──
        header = tk.Frame(self.main_container, bg=BG_DARK, pady=20)
        header.pack(fill=tk.X)

        # Title with gradient-like feel
        title_frame = tk.Frame(header, bg=BG_DARK)
        title_frame.pack()

        # Add Logo
        logo_container = tk.Frame(title_frame, bg=BG_DARK)
        logo_container.pack(side=tk.LEFT, padx=(0, 15))
        self._add_logo(logo_container, size=(60, 60), pady=0)

        title_text = tk.Frame(title_frame, bg=BG_DARK)
        title_text.pack(side=tk.LEFT)

        tk.Label(title_text, text="Snapify", font=FONT_TITLE,
                 fg=ACCENT, bg=BG_DARK).pack(anchor="w")
        tk.Label(title_text, text="Webcam-Based Attendance System", font=FONT_SUBTITLE,
                 fg=TEXT_SECONDARY, bg=BG_DARK).pack(anchor="w")

        # Logged-in info bar
        info_bar = tk.Frame(header, bg=BG_DARK)
        info_bar.pack(fill=tk.X, padx=30, pady=(10, 0))

        tk.Label(info_bar, text=f"👤 {self.teacher_email}", font=("Segoe UI", 10),
                 fg=TEXT_SECONDARY, bg=BG_DARK).pack(side=tk.LEFT)

        logout_btn = tk.Label(info_bar, text="🚪 Logout", font=("Segoe UI", 10),
                              fg=ERROR, bg=BG_DARK, cursor="hand2")
        logout_btn.pack(side=tk.RIGHT)
        logout_btn.bind("<Button-1>", lambda e: self._logout())

        # Separator
        tk.Frame(self.main_container, bg=BORDER_COLOR, height=1).pack(fill=tk.X, padx=30)

        # ── Steps Container ──
        steps_frame = tk.Frame(self.main_container, bg=BG_DARK, padx=30, pady=16)
        steps_frame.pack(fill=tk.BOTH, expand=False)

        tk.Label(steps_frame, text="WORKFLOW STEPS", font=("Segoe UI", 9, "bold"),
                 fg=TEXT_DIM, bg=BG_DARK).pack(anchor="w", pady=(0, 10))

        # Step 1
        self.card1 = StepCard(
            steps_frame, 1,
            "Register Faces",
            "Open webcam to capture and save face images for recognition",
            "📷", "Launch Camera",
            self._run_face_register,
            accent_color="#0078D7"
        )
        self.card1.pack(fill=tk.X, pady=(0, 8))

        # Step 2
        self.card2 = StepCard(
            steps_frame, 2,
            "Extract Features",
            "Process saved face images and generate 128D feature vectors",
            "⚙️", "Extract",
            self._run_feature_extraction,
            accent_color="#005b9f"
        )
        self.card2.pack(fill=tk.X, pady=(0, 8))

        # Step 3
        self.card3 = StepCard(
            steps_frame, 3,
            "Take Attendance",
            "Start real-time face recognition to mark attendance automatically",
            "✅", "Start",
            self._run_attendance,
            accent_color="#f39c12"
        )
        self.card3.pack(fill=tk.X, pady=(0, 8))

        # Step 4
        self.card4 = StepCard(
            steps_frame, 4,
            "View Attendance Records",
            "Open the web dashboard to browse and search attendance history",
            "📊", "Open Dashboard",
            self._run_dashboard,
            accent_color="#2ea043"
        )
        self.card4.pack(fill=tk.X, pady=(0, 8))

        # ── Log Output ──
        log_frame = tk.Frame(self.main_container, bg=BG_DARK, padx=30)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 16))

        log_header = tk.Frame(log_frame, bg=BG_DARK)
        log_header.pack(fill=tk.X, pady=(0, 6))

        tk.Label(log_header, text="OUTPUT LOG", font=("Segoe UI", 9, "bold"),
                 fg=TEXT_DIM, bg=BG_DARK).pack(side=tk.LEFT)

        clear_btn = tk.Button(log_header, text="Clear", font=("Segoe UI", 8),
                              fg=TEXT_SECONDARY, bg=BG_CARD, bd=0, cursor="hand2",
                              activebackground=BG_CARD_HOVER, padx=8, pady=2,
                              command=self._clear_log)
        clear_btn.pack(side=tk.RIGHT)

        # Log text widget with scrollbar
        log_container = tk.Frame(log_frame, bg=BORDER_COLOR, highlightthickness=0)
        log_container.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_container, bg=BG_CARD, fg=TEXT_SECONDARY,
            font=FONT_LOG, wrap=tk.WORD, bd=0, padx=12, pady=10,
            insertbackground=TEXT_PRIMARY, selectbackground=ACCENT,
            height=8
        )
        scrollbar = ttk.Scrollbar(log_container, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.log_text.configure(state="disabled")

        # Configure text tags for colored log messages
        self.log_text.tag_configure("info", foreground=TEXT_SECONDARY)
        self.log_text.tag_configure("success", foreground=SUCCESS)
        self.log_text.tag_configure("warning", foreground=WARNING)
        self.log_text.tag_configure("error", foreground=ERROR)
        self.log_text.tag_configure("accent", foreground=ACCENT)

        self._log(f"Logged in as {self.teacher_email}. Follow steps 1 → 2 → 3 → 4.", "accent")

    def _logout(self):
        if self.flask_process and self.flask_process.poll() is None:
            self.flask_process.terminate()
        self.flask_process = None
        self.teacher_email = None
        # Clear the teacher file
        teacher_file = os.path.join(self.project_dir, "current_teacher.json")
        if os.path.exists(teacher_file):
            os.remove(teacher_file)
        self._show_signin()

    def _write_teacher_file(self):
        """Write current teacher email to a shared file for Flask to read."""
        teacher_file = os.path.join(self.project_dir, "current_teacher.json")
        with open(teacher_file, "w") as f:
            json.dump({"teacher_email": self.teacher_email}, f)

    # ─── Logging ──────────────────────────────────────────────────

    def _log(self, message, tag="info"):
        self.log_text.configure(state="normal")
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}]  {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    # ─── Step Runners ─────────────────────────────────────────────

    def _run_face_register(self, card):
        """Step 1: Launch the face registration tkinter app."""
        card.set_running(True)
        self._log("Launching Face Registration window...", "accent")
        self._log("Register faces: enter a name → click Input → click Save Current Face", "info")

        def run():
            try:
                proc = subprocess.Popen(
                    [sys.executable, "get_faces_from_camera_tkinter.py",
                     "--teacher", self.teacher_email],
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                # Stream output
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        self.root.after(0, self._log, line)
                proc.wait()
                self.root.after(0, card.set_running, False)
                if proc.returncode == 0:
                    self.root.after(0, card.set_status, "✓ Completed", SUCCESS)
                    self.root.after(0, self._log, "Face registration completed successfully!", "success")
                else:
                    self.root.after(0, card.set_status, "✗ Error", ERROR)
                    self.root.after(0, self._log, f"Face registration exited with code {proc.returncode}", "error")
            except Exception as e:
                self.root.after(0, card.set_running, False)
                self.root.after(0, card.set_status, "✗ Error", ERROR)
                self.root.after(0, self._log, f"Error: {str(e)}", "error")

        threading.Thread(target=run, daemon=True).start()

    def _run_feature_extraction(self, card):
        """Step 2: Extract features to CSV."""
        # Check if face data exists for this teacher
        faces_dir = os.path.join(self.project_dir, "data", "data_faces_from_camera", self.teacher_email)
        if not os.path.isdir(faces_dir) or not os.listdir(faces_dir):
            self._log("⚠ No face data found! Please complete Step 1 first.", "warning")
            card.set_status("⚠ No face data", WARNING)
            return

        card.set_running(True)
        self._log("Extracting face features to CSV...", "accent")

        def run():
            try:
                proc = subprocess.Popen(
                    [sys.executable, "features_extraction_to_csv.py",
                     "--teacher", self.teacher_email],
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        self.root.after(0, self._log, line)
                proc.wait()
                self.root.after(0, card.set_running, False)
                if proc.returncode == 0:
                    self.root.after(0, card.set_status, "✓ Features saved", SUCCESS)
                    self.root.after(0, self._log, "Feature extraction completed!", "success")
                else:
                    self.root.after(0, card.set_status, "✗ Error", ERROR)
                    self.root.after(0, self._log, f"Feature extraction failed (code {proc.returncode})", "error")
            except Exception as e:
                self.root.after(0, card.set_running, False)
                self.root.after(0, card.set_status, "✗ Error", ERROR)
                self.root.after(0, self._log, f"Error: {str(e)}", "error")

        threading.Thread(target=run, daemon=True).start()

    def _run_attendance(self, card):
        """Step 3: Start real-time attendance taking."""
        features_csv = os.path.join(self.project_dir, "data", f"features_{self.teacher_email}.csv")
        if not os.path.isfile(features_csv):
            self._log("⚠ Features CSV not found! Please complete Step 2 first.", "warning")
            card.set_status("⚠ No features", WARNING)
            return

        # Ask for class/period name
        from tkinter import simpledialog
        class_name = simpledialog.askstring(
            "Class / Period",
            "Enter the class or period name\n(e.g. Maths, English, Science):",
            parent=self.root
        )
        if not class_name or not class_name.strip():
            self._log("⚠ Attendance cancelled — no class name entered.", "warning")
            return
        class_name = class_name.strip()

        card.set_running(True)
        self._log(f"Starting attendance for: {class_name}", "accent")
        self._log("Press 'Q' in the camera window to stop.", "info")

        def run():
            try:
                proc = subprocess.Popen(
                    [sys.executable, "attendance_taker.py",
                     "--class_name", class_name,
                     "--teacher", self.teacher_email],
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        self.root.after(0, self._log, line)
                proc.wait()
                self.root.after(0, card.set_running, False)
                if proc.returncode == 0:
                    self.root.after(0, card.set_status, "✓ Completed", SUCCESS)
                    self.root.after(0, self._log, f"Attendance session for '{class_name}' ended.", "success")
                else:
                    self.root.after(0, card.set_status, "✗ Error", ERROR)
                    self.root.after(0, self._log, f"Attendance taker exited with code {proc.returncode}", "error")
            except Exception as e:
                self.root.after(0, card.set_running, False)
                self.root.after(0, card.set_status, "✗ Error", ERROR)
                self.root.after(0, self._log, f"Error: {str(e)}", "error")

        threading.Thread(target=run, daemon=True).start()

    def _run_dashboard(self, card):
        """Step 4: Launch Flask dashboard and open browser."""
        # Write current teacher to file so Flask picks it up
        self._write_teacher_file()

        if self.flask_process and self.flask_process.poll() is None:
            # Flask already running — just open browser (it reads teacher per-request)
            self._log("Dashboard running — opening browser...", "info")
            webbrowser.open("http://127.0.0.1:5000")
            return

        card.set_running(True)
        self._log("Starting attendance dashboard server...", "accent")

        def run():
            try:
                self.flask_process = subprocess.Popen(
                    [sys.executable, "app.py", "--teacher", self.teacher_email],
                    cwd=self.project_dir,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace"
                )
                # Wait a moment for Flask to start
                time.sleep(2)

                if self.flask_process.poll() is None:
                    # Server started successfully
                    self.root.after(0, card.set_running, False)
                    self.root.after(0, card.set_status, "🟢 Server running", SUCCESS)
                    self.root.after(0, self._log,
                                   "Dashboard running at http://127.0.0.1:5000", "success")
                    webbrowser.open(f"http://127.0.0.1:5000")

                    # Continue reading output
                    for line in self.flask_process.stdout:
                        line = line.strip()
                        if line:
                            self.root.after(0, self._log, line)
                else:
                    self.root.after(0, card.set_running, False)
                    self.root.after(0, card.set_status, "✗ Error", ERROR)
                    output = self.flask_process.stdout.read()
                    self.root.after(0, self._log, f"Flask server failed to start: {output}", "error")
            except Exception as e:
                self.root.after(0, card.set_running, False)
                self.root.after(0, card.set_status, "✗ Error", ERROR)
                self.root.after(0, self._log, f"Error: {str(e)}", "error")

        threading.Thread(target=run, daemon=True).start()

    # ─── Cleanup ──────────────────────────────────────────────────

    def _on_close(self):
        """Clean up Flask server on exit."""
        if self.flask_process and self.flask_process.poll() is None:
            self.flask_process.terminate()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = LauncherApp()
    app.run()
