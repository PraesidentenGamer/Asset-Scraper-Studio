import os
import re
import csv
import json
import time
import queue
import ctypes
import shutil
import zipfile
import threading
import urllib.parse
import urllib.request
import urllib.error
from html.parser import HTMLParser
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog


APP_NAME = "Asset Scraper Studio v18"
USER_AGENT = "Mozilla/5.0 AssetScraperStudio/18.0"
CONFIG_FILE = Path.home() / "Downloads" / "AssetScraper" / "app_config.json"

DEFAULT_EXTENSIONS = [
    ".7z",
    ".as",
    ".bin",
    ".cfg",
    ".css",
    ".csv",
    ".dat",
    ".gif",
    ".ini",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mp3",
    ".ogg",
    ".png",
    ".rar",
    ".svg",
    ".swf",
    ".txt",
    ".wav",
    ".webp",
    ".xml",
    ".zip",
]

DEFAULT_PROJECTS = [
    "BigPoint Farmerama",
    "BigPoint Rising Cities",
    "Seafight",
    "DarkOrbit"
]

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}
SOUND_EXTS = {".mp3", ".ogg", ".wav"}
TEXT_EXTS = {".as", ".xml", ".json", ".txt", ".csv", ".js", ".css"}
HTML_EXTS = {"", ".html", ".htm", ".php", ".asp", ".aspx"}

PROFILES = {
    "Rising Cities": [
        "architect", "building", "buildings", "house", "factory", "bridge",
        "field", "object", "map", "city", "resident", "residential",
        "commercial", "industrial", "quest", "mission", "assets", "data",
        "config", "flash", "swf"
    ],
    "Farmerama": [
        "farm", "farmerama", "field", "barn", "animal", "tree",
        "crop", "market", "quest", "event", "asset", "assets",
        "data", "config", "flash", "swf"
    ],
    "General": [
        "assets", "data", "config", "flash", "swf", "xml",
        "json", "images", "sound", "script"
    ]
}

CATEGORY_RULES = {
    "Buildings": ["building", "house", "factory", "residential", "commercial", "industrial", "architect"],
    "Bridge/Map": ["bridge", "map", "zone", "area"],
    "Quests": ["quest", "mission", "task"],
    "Events": ["event", "season", "special"],
    "UI": ["button", "menu", "interface", "gui", "hud", "icon"],
    "Sounds": ["sound", "music", "audio", "sfx"],
}


TR = {
    "de": {
        "ready": "Bereit",
        "hits": "Treffer",
        "duplicates": "Duplikate",
        "database": "Datenbank",
        "saved_files": "Dateien gespeichert",
        "total_size": "Gesamtgröße",
        "images": "Bilder",
        "sounds": "Sounds",
        "saved": "gespeichert",
        "existing": "vorhanden",
        "found": "gefunden",
        "already_db": "bereits in DB",
        "error": "Fehler",
        "all": "Alle",
        "search_started": "Suche gestartet",
        "search_finished": "Suche fertig.",
        "download_started": "Download gestartet",
        "download_finished": "Download fertig.",
        "need_url": "Bitte zuerst mindestens einen Start-Link eingeben.",
        "need_project": "Bitte zuerst ein Projekt auswählen oder anlegen.",
        "no_results": "Keine Treffer vorhanden.",
        "project_exists": "Projekt existiert schon.",
        "project_name": "Projektname:",
        "new_project_name": "Neuer Projektname:",
        "remove_project_question": "Projekt aus der Liste entfernen?\nDer Ordner wird NICHT gelöscht.",
        "language_changed": "Sprache wurde umgeschaltet.",
        "about": """Asset Scraper Studio V18

Entwickelt von:
CodeMajorX

GitHub:
https://github.com/PraesidentenGamer

Copyright © 2026 CodeMajorX

Zweck:
Ein Archiv- und Analyse-Tool für öffentlich erreichbare Web-/Flash-Assets.

Enthalten:
- Projektverwaltung
- mehrere Start-Links
- Projekt-Datenbank
- Suchverlauf
- Duplikat-Erkennung
- Favoriten
- Tags/Kategorien
- Notizen pro Projekt
- Explorer-Ansicht
- Dashboard
- TXT/CSV/JSON Export
- ZIP-Export
- Deutsch/Englisch

Hinweis:
Das Tool findet nur Dateien, die öffentlich erreichbar sind. Es umgeht keine Logins, Sperren oder Rechte.
"""
    },
    "en": {
        "ready": "Ready",
        "hits": "Results",
        "duplicates": "Duplicates",
        "database": "Database",
        "saved_files": "Saved files",
        "total_size": "Total size",
        "images": "Images",
        "sounds": "Sounds",
        "saved": "saved",
        "existing": "existing",
        "found": "found",
        "already_db": "already in DB",
        "error": "Error",
        "all": "All",
        "search_started": "Search started",
        "search_finished": "Search finished.",
        "download_started": "Download started",
        "download_finished": "Download finished.",
        "need_url": "Please enter at least one start URL first.",
        "need_project": "Please select or create a project first.",
        "no_results": "No results available.",
        "project_exists": "Project already exists.",
        "project_name": "Project name:",
        "new_project_name": "New project name:",
        "remove_project_question": "Remove project from list?\nThe folder will NOT be deleted.",
        "language_changed": "Language switched.",
        "about": """Asset Scraper Studio v17

Developed by:
CodeMajorX

GitHub:
https://github.com/PraesidentenGamer

Copyright © 2026 CodeMajorX

Purpose:
An archive and analysis tool for publicly reachable web/Flash assets.

Included:
- Project management
- Multiple start URLs
- Project database
- Search history
- Duplicate detection
- Favorites
- Tags/categories
- Project notes
- Explorer view
- Dashboard
- TXT/CSV/JSON export
- ZIP export
- German/English

Notice:
The tool only finds publicly reachable files. It does not bypass logins, blocks, or permissions.
"""
    }
}


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key.lower() in ("href", "src", "data", "poster") and value:
                self.links.add(value)


def load_app_config():
    try:
        if CONFIG_FILE.exists():
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {"ui_scale": "Auto", "language": "Deutsch"}


def save_app_config(data):
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def clean_folder_name(name):
    name = (name or "").strip() or "Unbenanntes Projekt"
    return re.sub(r'[<>:"/\\|?*]+', "_", name).strip(" ._")


def normalize_url(base_url, link):
    if not link:
        return None
    link = link.strip().strip("\"'")
    if link.startswith(("javascript:", "mailto:", "tel:", "#")):
        return None
    return urllib.parse.urljoin(base_url, link)


def same_host(url_a, url_b):
    return urllib.parse.urlparse(url_a).netloc.lower() == urllib.parse.urlparse(url_b).netloc.lower()


def get_ext(url):
    return os.path.splitext(urllib.parse.urlparse(url).path.lower())[1]


def type_folder_for_ext(ext):
    ext = ext.lower()
    if ext in IMAGE_EXTS:
        return "images"
    if ext in SOUND_EXTS:
        return "sounds"
    return ext.lstrip(".") or "ohne_endung"


def safe_filename(url):
    parsed = urllib.parse.urlparse(url)
    name = os.path.basename(parsed.path)
    if name:
        return name
    fallback = parsed.netloc + parsed.path
    fallback = re.sub(r"[^a-zA-Z0-9._-]+", "_", fallback).strip("_")
    return fallback or "downloaded_file"


def format_bytes(num):
    try:
        num = float(num)
    except Exception:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num < 1024:
            return f"{num:.1f} {unit}" if unit != "B" else f"{int(num)} {unit}"
        num /= 1024
    return f"{num:.1f} PB"


def format_time(seconds):
    seconds = int(max(0, seconds or 0))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def fetch_text(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read(3_000_000)
    allowed = ("text", "html", "json", "xml", "javascript", "css")
    if not any(x in content_type.lower() for x in allowed):
        return ""
    return raw.decode("utf-8", errors="ignore")


def find_urls(base_url, text):
    found = set()
    parser = LinkParser()
    try:
        parser.feed(text)
        for link in parser.links:
            url = normalize_url(base_url, link)
            if url:
                found.add(url)
    except Exception:
        pass

    pattern = r"""["'(\s]([^"'()\s<>]+?\.(?:swf|as|xml|json|txt|csv|js|css|png|jpg|jpeg|gif|svg|webp|mp3|ogg|wav|zip|rar|7z|bin|dat|cfg|ini|html|htm|php|asp|aspx)(?:\?[^"'()\s<>]*)?)"""
    for match in re.findall(pattern, text, flags=re.IGNORECASE):
        url = normalize_url(base_url, match)
        if url:
            found.add(url)
    return found


def auto_category(url):
    low = url.lower()
    for category, words in CATEGORY_RULES.items():
        if any(w in low for w in words):
            return category
    ext = get_ext(url)
    if ext in IMAGE_EXTS:
        return "Images"
    if ext in SOUND_EXTS:
        return "Sounds"
    if ext == ".swf":
        return "SWF"
    if ext in (".xml", ".json"):
        return "Data"
    if ext in (".as", ".js", ".css"):
        return "Code"
    return "Other"


class AssetScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)

        self.app_config = load_app_config()
        self.language_var = tk.StringVar(value=self.app_config.get("language", "Deutsch"))
        self.ui_scale_var = tk.StringVar(value=self.app_config.get("ui_scale", "Auto"))
        self.ui_scale = 1.0

        self.log_queue = queue.Queue()
        self.ui_queue = queue.Queue()
        self.projects = []
        self.results = {}
        self.database = {}
        self.stop_requested = False

        self.base_folder_var = tk.StringVar(value=str(Path.home() / "Downloads" / "AssetScraper"))
        self.current_project = tk.StringVar()
        self.depth_var = tk.IntVar(value=1)
        self.same_host_var = tk.BooleanVar(value=True)
        self.keep_structure_var = tk.BooleanVar(value=False)
        self.skip_existing_var = tk.BooleanVar(value=True)
        self.delay_var = tk.DoubleVar(value=0.3)
        self.profile_var = tk.StringVar(value="Rising Cities")
        self.filter_var = tk.StringVar(value="All")
        self.search_text_var = tk.StringVar()

        self.status_var = tk.StringVar()
        self.stats_top_var = tk.StringVar()
        self.search_eta_var = tk.StringVar()
        self.download_eta_var = tk.StringVar()
        self.counter_var = tk.StringVar()
        self.size_var = tk.StringVar()
        self.project_info_var = tk.StringVar()
        self.dashboard_var = tk.StringVar()
        self.selected_info_var = tk.StringVar(value="No asset selected.")

        self.ext_vars = {}

        self.apply_ui_scale_value(self.ui_scale_var.get())
        self.setup_window()
        self.setup_style()
        self.build_ui()
        self.load_projects()
        self.reset_text_vars()
        self.root.after(150, self.process_queues)

    def lang_code(self):
        return "en" if self.language_var.get() == "English" else "de"

    def t(self, key):
        return TR[self.lang_code()].get(key, key)

    def l(self, de, en):
        return en if self.lang_code() == "en" else de

    def setup_window(self):
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{min(1750, int(screen_w * 0.98))}x{min(1000, int(screen_h * 0.95))}")
        self.root.minsize(1180, 730)

    def detect_auto_scale(self):
        w = self.root.winfo_screenwidth()
        h = self.root.winfo_screenheight()
        if w >= 1900 and h >= 1000:
            return 1.12
        if w >= 1600 and h >= 900:
            return 1.06
        if w <= 1366 or h <= 768:
            return 1.00
        return 1.03

    def scale_value(self, value):
        return max(1, int(value * self.ui_scale))

    def apply_ui_scale_value(self, value):
        if value == "Auto":
            self.ui_scale = self.detect_auto_scale()
        else:
            try:
                self.ui_scale = float(value.replace("%", "")) / 100.0
            except Exception:
                self.ui_scale = 1.0
        try:
            self.root.tk.call("tk", "scaling", self.ui_scale)
        except Exception:
            pass

    def setup_style(self):
        self.colors = {
            "bg": "#1E1E1E",
            "panel": "#252526",
            "panel2": "#333333",
            "panel3": "#2D2D30",
            "border": "#5A5A5A",
            "text": "#FFFFFF",
            "muted": "#D0D0D0",
            "accent": "#0098FF",
            "accent2": "#00B894",
            "entry": "#2D2D30",
            "tree": "#252526",
            "tree_alt": "#2A2A2A",
            "select": "#006CB8"
        }
        self.root.configure(bg=self.colors["bg"])
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"], fieldbackground=self.colors["entry"])
        style.configure("TFrame", background=self.colors["bg"])
        style.configure("Panel.TFrame", background=self.colors["panel"])
        style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Panel.TLabel", background=self.colors["panel"], foreground=self.colors["text"])
        style.configure("Muted.TLabel", background=self.colors["panel"], foreground=self.colors["muted"])
        style.configure("Title.TLabel", background=self.colors["panel"], foreground=self.colors["text"], font=("Segoe UI", self.scale_value(13), "bold"))
        style.configure("TLabelframe", background=self.colors["bg"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        style.configure("TLabelframe.Label", background=self.colors["bg"], foreground=self.colors["text"], font=("Segoe UI", self.scale_value(11), "bold"))
        style.configure("TButton", background=self.colors["panel3"], foreground=self.colors["text"], borderwidth=0, padding=6)
        style.map("TButton", background=[("active", "#1688D3"), ("pressed", self.colors["accent2"])])
        style.configure("Accent.TButton", background=self.colors["accent"], foreground="#FFFFFF", padding=7)
        style.configure("Green.TButton", background=self.colors["accent2"], foreground="#FFFFFF", padding=7)
        style.map("Accent.TButton", background=[("active", self.colors["accent2"])])
        style.configure("TCheckbutton", background=self.colors["bg"], foreground=self.colors["text"])
        style.map("TCheckbutton", background=[("active", self.colors["bg"])])
        style.configure("TEntry", fieldbackground=self.colors["entry"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        style.configure("TSpinbox", fieldbackground=self.colors["entry"], foreground=self.colors["text"], bordercolor=self.colors["border"])
        style.configure("TCombobox", fieldbackground="#3C3C3C", foreground="#FFFFFF", background="#3C3C3C")
        style.map("TCombobox", fieldbackground=[("readonly", "#3C3C3C")], foreground=[("readonly", "#FFFFFF")])
        style.configure("Horizontal.TProgressbar", troughcolor=self.colors["entry"], background=self.colors["accent"], bordercolor=self.colors["border"])
        style.configure("Treeview", background=self.colors["tree"], foreground=self.colors["text"], fieldbackground=self.colors["tree"], rowheight=self.scale_value(28), bordercolor=self.colors["border"])
        style.configure("Treeview.Heading", background=self.colors["panel3"], foreground=self.colors["text"], font=("Segoe UI", self.scale_value(10), "bold"))
        style.map("Treeview", background=[("selected", self.colors["select"])], foreground=[("selected", "#FFFFFF")])
        style.configure("TNotebook", background=self.colors["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=self.colors["panel3"], foreground=self.colors["text"], padding=(14, 7))
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])], foreground=[("selected", "#FFFFFF")])

    def lf(self, parent, text):
        return ttk.LabelFrame(parent, text=text)

    def txt(self, parent, height=3, font="Consolas"):
        return tk.Text(
            parent,
            height=height,
            bg=self.colors["entry"],
            fg=self.colors["text"],
            insertbackground=self.colors["text"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors["border"],
            wrap="word",
            font=(font, self.scale_value(10))
        )

    def build_ui(self):
        for child in self.root.winfo_children():
            child.destroy()

        self.ext_vars = {}

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=6, pady=6)

        scraper_tab = ttk.Frame(notebook)
        explorer_tab = ttk.Frame(notebook)
        dashboard_tab = ttk.Frame(notebook)
        notes_tab = ttk.Frame(notebook)
        about_tab = ttk.Frame(notebook)

        notebook.add(scraper_tab, text="Scraper")
        notebook.add(explorer_tab, text=self.l("Explorer", "Explorer"))
        notebook.add(dashboard_tab, text=self.l("Übersicht", "Dashboard"))
        notebook.add(notes_tab, text=self.l("Notizen", "Notes"))
        notebook.add(about_tab, text=self.l("Info / Über", "Info / About"))

        self.build_scraper_tab(scraper_tab)
        self.build_explorer_tab(explorer_tab)
        self.build_dashboard_tab(dashboard_tab)
        self.build_notes_tab(notes_tab)
        self.build_about_tab(about_tab)

    def build_scraper_tab(self, tab):
        main = ttk.PanedWindow(tab, orient="horizontal")
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main, padding=5)
        right = ttk.Frame(main, padding=5)
        main.add(left, weight=1)
        main.add(right, weight=6)

        header = ttk.Frame(left, style="Panel.TFrame", padding=10)
        header.pack(fill="x", pady=(0, 8))
        ttk.Label(header, text="Asset Scraper Studio", style="Title.TLabel").pack(anchor="w")
        ttk.Label(header, text=self.l("Projektarchiv + Datenbank", "Project archive + database"), style="Muted.TLabel").pack(anchor="w", pady=(2, 0))

        project_frame = self.lf(left, self.l("Projekte", "Projects"))
        project_frame.pack(fill="both", expand=True)

        self.project_list = tk.Listbox(project_frame, height=12, bg=self.colors["tree"], fg=self.colors["text"], selectbackground=self.colors["select"], selectforeground="#FFFFFF", relief="flat", highlightthickness=1, highlightbackground=self.colors["border"], font=("Segoe UI", self.scale_value(10)))
        self.project_list.pack(fill="both", expand=True, padx=5, pady=5)
        self.project_list.bind("<<ListboxSelect>>", self.on_project_select)

        ttk.Button(project_frame, text=self.l("＋ Neues Projekt", "＋ New project"), command=self.new_project, style="Accent.TButton").pack(fill="x", padx=5, pady=2)
        ttk.Button(project_frame, text=self.l("Umbenennen", "Rename"), command=self.rename_project).pack(fill="x", padx=5, pady=2)
        ttk.Button(project_frame, text=self.l("Entfernen", "Remove"), command=self.delete_project).pack(fill="x", padx=5, pady=2)
        ttk.Button(project_frame, text=self.l("Ordner öffnen", "Open folder"), command=self.open_project_folder).pack(fill="x", padx=5, pady=2)

        base_frame = self.lf(left, self.l("Basisordner", "Base folder"))
        base_frame.pack(fill="x", pady=8)
        ttk.Entry(base_frame, textvariable=self.base_folder_var).pack(fill="x", padx=5, pady=5)
        ttk.Button(base_frame, text=self.l("Durchsuchen", "Browse"), command=self.choose_base_folder).pack(fill="x", padx=5, pady=4)

        info_frame = self.lf(left, self.l("Projektinfo", "Project info"))
        info_frame.pack(fill="x", pady=8)
        ttk.Label(info_frame, textvariable=self.project_info_var, justify="left").pack(fill="x", padx=8, pady=8)

        top = ttk.Frame(right, style="Panel.TFrame", padding=10)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, textvariable=self.status_var, style="Title.TLabel").pack(side="left")
        ttk.Label(top, text="   v18 CodeMajorX Asset Recovery Edition", style="Muted.TLabel").pack(side="left")
        ttk.Label(top, textvariable=self.stats_top_var, style="Muted.TLabel").pack(side="right")

        ttk.Label(top, text=self.l("Sprache:", "Language:"), style="Muted.TLabel").pack(side="right", padx=(12, 4))
        lang_box = ttk.Combobox(top, textvariable=self.language_var, values=["Deutsch", "English"], width=10, state="readonly")
        lang_box.pack(side="right")
        lang_box.bind("<<ComboboxSelected>>", self.change_language)

        ttk.Label(top, text=self.l("Skalierung:", "Scale:"), style="Muted.TLabel").pack(side="right", padx=(12, 4))
        scale_box = ttk.Combobox(top, textvariable=self.ui_scale_var, values=["Auto", "100%", "110%", "120%", "125%", "135%", "150%", "160%", "175%"], width=9, state="readonly")
        scale_box.pack(side="right")
        scale_box.bind("<<ComboboxSelected>>", self.change_ui_scale)

        start_frame = self.lf(right, "Start")
        start_frame.pack(fill="x")
        ttk.Label(start_frame, text=self.l("Aktuelles Projekt:", "Current project:")).grid(row=0, column=0, sticky="w", padx=6, pady=5)
        ttk.Label(start_frame, textvariable=self.current_project).grid(row=0, column=1, sticky="w", padx=6, pady=5)

        ttk.Label(start_frame, text=self.l("Start-Links:", "Start URLs:")).grid(row=1, column=0, sticky="nw", padx=6, pady=5)
        self.urls_text = self.txt(start_frame, height=4)
        self.urls_text.grid(row=1, column=1, sticky="ew", padx=6, pady=5)

        ttk.Label(start_frame, text="Profil:" if self.lang_code()=="de" else "Profile:").grid(row=1, column=2, sticky="nw", padx=6, pady=5)
        profile_box = ttk.Combobox(start_frame, textvariable=self.profile_var, values=list(PROFILES.keys()), width=20, state="readonly")
        profile_box.grid(row=1, column=3, sticky="nw", padx=6, pady=5)
        ttk.Button(start_frame, text=self.l("Laden", "Load"), command=self.apply_profile).grid(row=1, column=4, sticky="nw", padx=6, pady=5)
        start_frame.columnconfigure(1, weight=1)

        options = self.lf(right, self.l("Optionen", "Options"))
        options.pack(fill="x", pady=6)
        ttk.Label(options, text=self.l("Such-Tiefe:", "Search depth:")).grid(row=0, column=0, sticky="w", padx=6, pady=5)
        ttk.Spinbox(options, from_=0, to=5, textvariable=self.depth_var, width=5).grid(row=0, column=1, sticky="w", padx=6)
        ttk.Checkbutton(options, text=self.l("Nur gleicher Host", "Same host only"), variable=self.same_host_var).grid(row=0, column=2, sticky="w", padx=6)
        ttk.Checkbutton(options, text=self.l("Struktur behalten", "Keep structure"), variable=self.keep_structure_var).grid(row=0, column=3, sticky="w", padx=6)
        ttk.Checkbutton(options, text=self.l("Vorhandene überspringen", "Skip existing"), variable=self.skip_existing_var).grid(row=0, column=4, sticky="w", padx=6)
        ttk.Label(options, text=self.l("Pause:", "Delay:")).grid(row=1, column=0, sticky="w", padx=6, pady=5)
        ttk.Spinbox(options, from_=0.0, to=5.0, increment=0.1, textvariable=self.delay_var, width=5).grid(row=1, column=1, sticky="w", padx=6)

        ext_frame = self.lf(right, self.l("Dateitypen", "File types"))
        ext_frame.pack(fill="x", pady=6)
        for i, ext in enumerate(sorted(set(DEFAULT_EXTENSIONS), key=lambda x: x.lower())):
            var = tk.BooleanVar(value=True)
            self.ext_vars[ext] = var
            ttk.Checkbutton(ext_frame, text=ext, variable=var).grid(row=i // 10, column=i % 10, sticky="w", padx=8, pady=2)

        keyword_frame = self.lf(right, self.l("Suchbegriffe", "Keywords"))
        keyword_frame.pack(fill="x", pady=6)
        self.keyword_text = self.txt(keyword_frame, height=3)
        self.keyword_text.pack(fill="x", padx=6, pady=5)
        self.keyword_text.insert("1.0", "\n".join(PROFILES.get(self.profile_var.get(), PROFILES["General"])))

        buttons = ttk.Frame(right)
        buttons.pack(fill="x", pady=4)
        ttk.Button(buttons, text=self.l("🔎 Suche", "🔎 Search"), command=self.start_search, style="Accent.TButton").pack(side="left", padx=3)
        ttk.Button(buttons, text="⬇ Download", command=self.start_download).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("🔁 Fehler erneut", "🔁 Retry errors"), command=self.retry_failed_downloads).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("🆕 Nur neue", "🆕 New only"), command=self.download_new_only).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("📂 DB laden", "📂 Load DB"), command=self.load_database_to_results).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("💾 DB speichern", "💾 Save DB"), command=self.save_database).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("⭐ Favorit", "⭐ Favorite"), command=self.mark_selected_favorite).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("🏷 Tag", "🏷 Tag"), command=self.tag_selected).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("📦 ZIP Export", "📦 ZIP Export"), command=self.export_project_zip).pack(side="left", padx=3)
        ttk.Button(buttons, text="📊 CSV", command=self.export_csv).pack(side="left", padx=3)
        ttk.Button(buttons, text="📄 TXT", command=self.export_txt).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("📥 URL-Liste", "📥 URLs"), command=self.import_url_list).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("⛔ Stop", "⛔ Stop"), command=self.request_stop).pack(side="left", padx=3)
        ttk.Button(buttons, text=self.l("🧹 Leeren", "🧹 Clear"), command=self.clear_results).pack(side="left", padx=3)

        progress_frame = self.lf(right, self.l("Fortschritt", "Progress"))
        progress_frame.pack(fill="x", pady=5)
        self.search_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.search_progress.pack(fill="x", padx=6, pady=(5, 2))
        ttk.Label(progress_frame, textvariable=self.search_eta_var).pack(anchor="w", padx=6, pady=1)
        self.download_progress = ttk.Progressbar(progress_frame, mode="determinate")
        self.download_progress.pack(fill="x", padx=6, pady=(4, 2))
        ttk.Label(progress_frame, textvariable=self.download_eta_var).pack(anchor="w", padx=6, pady=1)
        ttk.Label(progress_frame, textvariable=self.counter_var).pack(anchor="w", padx=6, pady=1)
        ttk.Label(progress_frame, textvariable=self.size_var).pack(anchor="w", padx=6, pady=(1, 5))

        filter_frame = ttk.Frame(right)
        filter_frame.pack(fill="x", pady=(3, 0))
        ttk.Label(filter_frame, text="Filter:").pack(side="left", padx=4)
        self.filter_values = ["All", "swf", "as", "xml", "json", "css", "js", "images", "sounds", "zip", "rar", "7z", "favorite", "saved", "found", "Error", "Duplicates"]
        self.filter_var.set("All")
        filter_box = ttk.Combobox(filter_frame, textvariable=self.filter_var, values=self.filter_values, width=14, state="readonly")
        filter_box.pack(side="left", padx=4)
        filter_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_tree())
        ttk.Label(filter_frame, text=self.l("Suche:", "Search:")).pack(side="left", padx=(16, 4))
        ttk.Entry(filter_frame, textvariable=self.search_text_var, width=30).pack(side="left", padx=4)
        ttk.Button(filter_frame, text=self.l("Anwenden", "Apply"), command=self.refresh_tree).pack(side="left", padx=4)
        ttk.Button(filter_frame, text=self.l("Alle Projekte suchen", "Search all projects"), command=self.search_all_projects).pack(side="left", padx=4)

        split = ttk.PanedWindow(right, orient="vertical")
        split.pack(fill="both", expand=True, pady=6)

        result_frame = self.lf(split, self.l("Gefundene Dateien", "Found files"))
        split.add(result_frame, weight=5)

        self.tree = ttk.Treeview(result_frame, columns=("url", "type", "size", "status", "category", "favorite"), show="headings", selectmode="extended")
        headings = [
            ("url", "URL", 700),
            ("type", self.l("Typ", "Type"), 80),
            ("size", self.l("Größe", "Size"), 95),
            ("status", "Status", 110),
            ("category", self.l("Kategorie", "Category"), 130),
            ("favorite", "★", 45),
        ]
        for col, title, width in headings:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width)
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.tag_configure("odd", background=self.colors["tree"])
        self.tree.tag_configure("even", background=self.colors["tree_alt"])
        self.tree.tag_configure("error", foreground="#FF6B6B")
        self.tree.tag_configure("saved", foreground="#7CFFB2")
        self.tree.tag_configure("db", foreground="#FFD166")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_asset_select)

        self.context_menu = tk.Menu(self.root, tearoff=0, bg=self.colors["panel2"], fg=self.colors["text"])
        self.context_menu.add_command(label="Copy link", command=self.copy_selected_link)
        self.context_menu.add_command(label="Open in browser", command=self.open_selected_in_browser)
        self.context_menu.add_command(label="Download selected", command=self.download_selected_only)
        self.context_menu.add_command(label="Favorite / Favorit", command=self.mark_selected_favorite)
        self.context_menu.add_command(label="Tag / Kategorie", command=self.tag_selected)
        self.tree.bind("<Button-3>", self.show_context_menu)

        log_frame = self.lf(split, "Log")
        split.add(log_frame, weight=1)
        self.log_text = self.txt(log_frame, height=8)
        self.log_text.pack(fill="both", expand=True)

    def build_explorer_tab(self, tab):
        main = ttk.PanedWindow(tab, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=8)

        left = ttk.Frame(main, padding=5)
        right = ttk.Frame(main, padding=5)
        main.add(left, weight=1)
        main.add(right, weight=4)

        ttk.Label(left, text=self.l("Asset Explorer", "Asset Explorer"), font=("Segoe UI", self.scale_value(14), "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Button(left, text=self.l("Aktualisieren", "Refresh"), command=self.refresh_explorer).pack(fill="x", pady=3)
        ttk.Button(left, text=self.l("Projektordner öffnen", "Open project folder"), command=self.open_project_folder).pack(fill="x", pady=3)

        self.explorer_tree = ttk.Treeview(left, columns=("count",), show="tree headings", height=18)
        self.explorer_tree.heading("#0", text=self.l("Typ", "Type"))
        self.explorer_tree.heading("count", text=self.l("Anzahl", "Count"))
        self.explorer_tree.column("#0", width=160)
        self.explorer_tree.column("count", width=70)
        self.explorer_tree.pack(fill="both", expand=True, pady=8)
        self.explorer_tree.bind("<<TreeviewSelect>>", self.on_explorer_select)

        self.preview_text = self.txt(right, height=20, font="Consolas")
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.insert("1.0", self.l("Wähle eine Kategorie oder ein Asset aus.", "Select a category or asset in the scraper list."))

    def build_dashboard_tab(self, tab):
        wrapper = ttk.Frame(tab, padding=16)
        wrapper.pack(fill="both", expand=True)
        ttk.Label(wrapper, text=self.l("Übersicht", "Dashboard"), font=("Segoe UI", self.scale_value(18), "bold")).pack(anchor="w", pady=(0, 10))
        self.dashboard_text = self.txt(wrapper, height=28, font="Consolas")
        self.dashboard_text.pack(fill="both", expand=True)
        ttk.Button(wrapper, text=self.l("Übersicht aktualisieren", "Refresh Dashboard"), command=self.update_dashboard).pack(anchor="w", pady=8)

    def build_notes_tab(self, tab):
        wrapper = ttk.Frame(tab, padding=12)
        wrapper.pack(fill="both", expand=True)
        ttk.Label(wrapper, text=self.l("Projekt-Notizen", "Project Notes"), font=("Segoe UI", self.scale_value(16), "bold")).pack(anchor="w", pady=(0, 8))
        self.notes_text = self.txt(wrapper, height=25, font="Segoe UI")
        self.notes_text.pack(fill="both", expand=True)
        btns = ttk.Frame(wrapper)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text=self.l("Notizen laden", "Load notes"), command=self.load_notes).pack(side="left", padx=4)
        ttk.Button(btns, text=self.l("Notizen speichern", "Save notes"), command=self.save_notes, style="Green.TButton").pack(side="left", padx=4)

    def build_about_tab(self, tab):
        wrapper = ttk.Frame(tab, padding=18)
        wrapper.pack(fill="both", expand=True)
        ttk.Label(wrapper, text=APP_NAME, font=("Segoe UI", self.scale_value(18), "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Label(wrapper, text="v18 ABC Dateitypen Fix: archive, database, repair, validation, explorer, notes, favorites, tags.", foreground=self.colors["muted"], font=("Segoe UI", self.scale_value(11))).pack(anchor="w", pady=(0, 16))
        about = self.txt(wrapper, height=25, font="Segoe UI")
        about.pack(fill="both", expand=True)
        about.insert("1.0", self.t("about"))
        about.configure(state="disabled")

        btns = ttk.Frame(wrapper)
        btns.pack(fill="x", pady=10)
        ttk.Button(btns, text="GitHub: CodeMajorX / PraesidentenGamer", command=self.open_github_profile, style="Accent.TButton").pack(side="left", padx=4)
        ttk.Button(btns, text="Open project folder / Projektordner öffnen", command=self.open_project_folder).pack(side="left", padx=4)

    def reset_text_vars(self):
        self.status_var.set(self.t("ready"))
        self.update_top_stats()
        if self.lang_code() == "de":
            self.search_eta_var.set("Suchzeit: --:-- | geprüft: 0 | Warteschlange: 0 | Treffer: 0")
            self.download_eta_var.set("Downloadzeit: --:-- | Dateien: 0/0 | Daten: 0 B")
            self.size_var.set("Gespeichert: 0 B")
        else:
            self.search_eta_var.set("Search time: --:-- | checked: 0 | queue: 0 | results: 0")
            self.download_eta_var.set("Download time: --:-- | files: 0/0 | data: 0 B")
            self.size_var.set("Saved: 0 B")
        self.counter_var.set(f"{self.t('hits')}: {len(self.results)}")

    def change_language(self, event=None):
        self.app_config["language"] = self.language_var.get()
        save_app_config(self.app_config)

        urls = ""
        keywords = ""
        notes = ""
        try:
            urls = self.urls_text.get("1.0", "end")
        except Exception:
            pass
        try:
            keywords = self.keyword_text.get("1.0", "end")
        except Exception:
            pass
        try:
            notes = self.notes_text.get("1.0", "end")
        except Exception:
            pass

        self.build_ui()
        self.refresh_project_list()
        self.refresh_tree()
        self.update_project_info()
        self.update_dashboard()
        self.refresh_explorer()

        try:
            self.urls_text.delete("1.0", "end")
            self.urls_text.insert("1.0", urls)
        except Exception:
            pass
        try:
            self.keyword_text.delete("1.0", "end")
            self.keyword_text.insert("1.0", keywords)
        except Exception:
            pass
        try:
            self.notes_text.delete("1.0", "end")
            self.notes_text.insert("1.0", notes)
        except Exception:
            pass

        self.log(self.t("language_changed"))

    def change_ui_scale(self, event=None):
        self.app_config["ui_scale"] = self.ui_scale_var.get()
        self.app_config["language"] = self.language_var.get()
        save_app_config(self.app_config)
        messagebox.showinfo(APP_NAME, "Scale saved. Restart recommended for perfect layout.\nSkalierung gespeichert. Neustart empfohlen.")

    def base_dir(self):
        return Path(self.base_folder_var.get())

    def projects_file(self):
        return self.base_dir() / "projects.json"

    def project_dir(self, name=None):
        return self.base_dir() / clean_folder_name(name or self.current_project.get())

    def database_file(self):
        return self.project_dir() / "database.json"

    def notes_file(self):
        return self.project_dir() / "notes.txt"

    def history_file(self):
        return self.project_dir() / "logs" / "search_history.json"

    def ensure_project_folders(self, name):
        p = self.project_dir(name)
        for folder in ["swf", "as", "xml", "json", "css", "js", "txt", "csv", "images", "sounds", "zip", "rar", "7z", "logs", "exports"]:
            (p / folder).mkdir(parents=True, exist_ok=True)
        return p

    def refresh_project_list(self):
        if not hasattr(self, "project_list"):
            return
        self.project_list.delete(0, "end")
        for p in self.projects:
            self.project_list.insert("end", p)
        if self.current_project.get() in self.projects:
            self.project_list.selection_set(self.projects.index(self.current_project.get()))
        elif self.projects:
            self.current_project.set(self.projects[0])
            self.project_list.selection_set(0)

    def load_projects(self):
        self.base_dir().mkdir(parents=True, exist_ok=True)
        pf = self.projects_file()
        if pf.exists():
            try:
                self.projects = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                self.projects = DEFAULT_PROJECTS[:]
        else:
            self.projects = DEFAULT_PROJECTS[:]
            self.save_projects()

        for p in self.projects:
            self.ensure_project_folders(p)
        if self.projects and not self.current_project.get():
            self.current_project.set(self.projects[0])
        self.load_database()
        self.refresh_project_list()
        self.update_project_info()
        self.update_dashboard()
        self.refresh_explorer()
        self.load_notes()

    def save_projects(self):
        self.base_dir().mkdir(parents=True, exist_ok=True)
        self.projects_file().write_text(json.dumps(self.projects, indent=2, ensure_ascii=False), encoding="utf-8")

    def on_project_select(self, event=None):
        sel = self.project_list.curselection()
        if sel:
            self.current_project.set(self.projects[sel[0]])
            self.ensure_project_folders(self.current_project.get())
            self.load_database()
            self.update_project_info()
            self.update_dashboard()
            self.refresh_explorer()
            self.load_notes()

    def load_database(self):
        self.database = {}
        db = self.database_file()
        if db.exists():
            try:
                data = json.loads(db.read_text(encoding="utf-8"))
                self.database = data.get("assets", {})
            except Exception:
                self.database = {}
        self.update_top_stats()


    def backup_database(self):
        """Erstellt vor dem Speichern ein Backup der bisherigen database.json."""
        try:
            db = self.database_file()
            if not db.exists():
                return
            backup_dir = self.project_dir() / "logs" / "backups"
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            backup_file = backup_dir / f"database_backup_{stamp}.json"
            shutil.copy2(db, backup_file)
            self.log(f"Database backup: {backup_file}")
        except Exception as e:
            self.log(f"Backup error: {e}")

    def validate_downloaded_file(self, path):
        """Prüft grob, ob eine geladene Datei verdächtig/kaputt wirkt."""
        try:
            p = Path(path)
            if not p.exists():
                return False, "missing"
            size = p.stat().st_size
            if size == 0:
                return False, "0 KB"

            head = p.read_bytes()[:512]
            low = head.lower()

            # Häufiger Fall: statt Asset kam HTML-Fehlerseite.
            if low.lstrip().startswith(b"<!doctype html") or low.lstrip().startswith(b"<html"):
                return False, "HTML instead of asset"

            ext = p.suffix.lower()
            if ext == ".swf":
                if not (head.startswith(b"FWS") or head.startswith(b"CWS") or head.startswith(b"ZWS")):
                    return False, "invalid SWF header"

            return True, "ok"
        except Exception as e:
            return False, str(e)

    def save_database(self):
        if not self.current_project.get():
            return
        self.ensure_project_folders(self.current_project.get())
        self.backup_database()
        data = {
            "project": self.current_project.get(),
            "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "count": len(self.database),
            "assets": self.database
        }
        self.database_file().write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        self.log(f"Database saved: {self.database_file()}")

    def load_database_to_results(self):
        self.results = {url: dict(info) for url, info in self.database.items()}
        self.refresh_tree()
        self.update_top_stats()

    def update_project_info(self):
        if not self.current_project.get():
            self.project_info_var.set("")
            return

        p = self.ensure_project_folders(self.current_project.get())
        count = 0
        total_size = 0
        counts = {}

        for file in p.rglob("*"):
            if file.is_file() and file.parent.name not in ("logs", "exports") and file.name not in ("database.json", "notes.txt"):
                count += 1
                total_size += file.stat().st_size
                counts[file.parent.name] = counts.get(file.parent.name, 0) + 1

        self.project_info_var.set(
            f"{self.current_project.get()}\n\n"
            f"{self.l('Gespeicherte Dateien', 'Saved files')}: {count}\n"
            f"{self.l('Gesamtgröße', 'Total size')}: {format_bytes(total_size)}\n"
            f"Database: {len(self.database)}\n\n"
            f"SWF: {counts.get('swf', 0)}\n"
            f"AS: {counts.get('as', 0)}\n"
            f"XML: {counts.get('xml', 0)}\n"
            f"JSON: {counts.get('json', 0)}\n"
            f"Images: {counts.get('images', 0)}\n"
            f"Sounds: {counts.get('sounds', 0)}"
        )

    def update_top_stats(self):
        duplicates = sum(1 for i in self.results.values() if i.get("duplicate"))
        if self.lang_code() == "de":
            self.stats_top_var.set(f"Treffer: {len(self.results)}   |   DB: {len(self.database)}   |   Duplikate: {duplicates}")
        else:
            self.stats_top_var.set(f"Results: {len(self.results)}   |   DB: {len(self.database)}   |   Duplicates: {duplicates}")

    def choose_base_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.base_folder_var.set(folder)
            self.load_projects()

    def open_base_folder(self):
        self.base_dir().mkdir(parents=True, exist_ok=True)
        os.startfile(self.base_dir())

    def new_project(self):
        name = simpledialog.askstring(APP_NAME, self.t("project_name"))
        if not name:
            return
        name = clean_folder_name(name)
        if name in self.projects:
            messagebox.showinfo(APP_NAME, self.t("project_exists"))
            return
        self.projects.append(name)
        self.save_projects()
        self.current_project.set(name)
        self.load_projects()

    def rename_project(self):
        sel = self.project_list.curselection()
        if not sel:
            return
        old = self.projects[sel[0]]
        new = simpledialog.askstring(APP_NAME, self.t("new_project_name"), initialvalue=old)
        if not new:
            return
        new = clean_folder_name(new)
        old_dir = self.project_dir(old)
        new_dir = self.project_dir(new)
        if old_dir.exists() and not new_dir.exists():
            old_dir.rename(new_dir)
        self.projects[sel[0]] = new
        self.current_project.set(new)
        self.save_projects()
        self.load_projects()

    def delete_project(self):
        sel = self.project_list.curselection()
        if not sel:
            return
        if not messagebox.askyesno(APP_NAME, self.t("remove_project_question")):
            return
        self.projects.pop(sel[0])
        self.current_project.set(self.projects[0] if self.projects else "")
        self.save_projects()
        self.load_projects()

    def open_project_folder(self):
        folder = self.project_dir()
        self.ensure_project_folders(self.current_project.get())
        os.startfile(folder)

    def apply_profile(self):
        words = PROFILES.get(self.profile_var.get(), PROFILES["General"])
        self.keyword_text.delete("1.0", "end")
        self.keyword_text.insert("1.0", "\n".join(words))

    def log(self, msg):
        stamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{stamp}] {msg}")

    def process_queues(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_text.insert("end", msg + "\n")
            self.log_text.see("end")
        while not self.ui_queue.empty():
            self.handle_ui_event(self.ui_queue.get())
        self.root.after(150, self.process_queues)

    def handle_ui_event(self, event):
        if event.get("kind") == "search_progress":
            checked = event.get("checked", 0)
            queue_len = event.get("queue", 0)
            found = event.get("found", 0)
            elapsed = event.get("elapsed", 0)
            estimate_total = max(checked + queue_len, 1)
            percent = min(100, int((checked / estimate_total) * 100))
            self.search_progress["maximum"] = 100
            self.search_progress["value"] = percent
            speed = checked / elapsed if elapsed > 0 else 0
            eta = queue_len / speed if speed > 0 else 0
            if self.lang_code() == "de":
                self.search_eta_var.set(f"Suchzeit: {format_time(elapsed)} | Rest: {format_time(eta)} | geprüft: {checked} | Warteschlange: {queue_len} | Treffer: {found}")
            else:
                self.search_eta_var.set(f"Search time: {format_time(elapsed)} | ETA: {format_time(eta)} | checked: {checked} | queue: {queue_len} | results: {found}")
        elif event.get("kind") == "download_progress":
            done = event.get("done", 0)
            total = event.get("total", 1)
            bytes_done = event.get("bytes_done", 0)
            elapsed = event.get("elapsed", 0)
            self.download_progress["maximum"] = total
            self.download_progress["value"] = done
            remaining = max(total - done, 0)
            speed_files = done / elapsed if elapsed > 0 else 0
            eta = remaining / speed_files if speed_files > 0 else 0
            if self.lang_code() == "de":
                self.download_eta_var.set(f"Downloadzeit: {format_time(elapsed)} | Rest: {format_time(eta)} | Dateien: {done}/{total} | Daten: {format_bytes(bytes_done)}")
                self.size_var.set(f"Gespeichert in diesem Lauf: {format_bytes(bytes_done)}")
            else:
                self.download_eta_var.set(f"Download time: {format_time(elapsed)} | ETA: {format_time(eta)} | files: {done}/{total} | data: {format_bytes(bytes_done)}")
                self.size_var.set(f"Saved this run: {format_bytes(bytes_done)}")
        elif event.get("kind") == "status":
            self.status_var.set(event.get("text", self.t("ready")))

    def selected_extensions(self):
        return {ext for ext, var in self.ext_vars.items() if var.get()}

    def start_urls(self):
        urls = []
        for line in self.urls_text.get("1.0", "end").splitlines():
            line = line.strip()
            if not line:
                continue
            if not line.startswith(("http://", "https://")):
                line = "https://" + line
            urls.append(line)
        return urls

    def clear_results(self):
        self.results.clear()
        self.refresh_tree()
        self.reset_text_vars()
        self.search_progress["value"] = 0
        self.download_progress["value"] = 0

    def add_result(self, url, source_url=""):
        if url in self.results:
            self.results[url]["duplicate"] = True
            return

        ext = get_ext(url)
        info = {
            "url": url,
            "ext": ext,
            "type": type_folder_for_ext(ext),
            "size": "",
            "size_bytes": None,
            "status": self.t("already_db") if url in self.database else self.t("found"),
            "source_url": source_url,
            "duplicate": url in self.database,
            "favorite": self.database.get(url, {}).get("favorite", False),
            "category": self.database.get(url, {}).get("category", auto_category(url)),
            "tags": self.database.get(url, {}).get("tags", []),
            "first_seen": self.database.get(url, {}).get("first_seen", time.strftime("%Y-%m-%d %H:%M:%S")),
            "last_seen": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.results[url] = info
        self.database[url] = dict(info)
        self.refresh_tree()
        self.update_top_stats()

    def refresh_tree(self):
        if not hasattr(self, "tree"):
            return
        for item in self.tree.get_children():
            self.tree.delete(item)

        selected_filter = self.filter_var.get()
        text_filter = self.search_text_var.get().strip().lower()

        for url, info in self.results.items():
            if selected_filter not in ("", "All"):
                if selected_filter == "Duplicates":
                    if not info.get("duplicate"):
                        continue
                elif selected_filter == "favorite":
                    if not info.get("favorite"):
                        continue
                elif selected_filter in ("saved", "found", "Error"):
                    if info.get("status") != selected_filter:
                        continue
                elif info.get("type") != selected_filter:
                    continue

            if text_filter and text_filter not in url.lower() and text_filter not in str(info.get("tags", [])).lower() and text_filter not in info.get("category", "").lower():
                continue

            row_index = len(self.tree.get_children())
            tags = ["even" if row_index % 2 == 0 else "odd"]
            status = info.get("status", "")
            if status == self.t("error") or status == "Error":
                tags.append("error")
            elif status in (self.t("saved"), self.t("existing"), "saved", "existing"):
                tags.append("saved")
            elif status == self.t("already_db") or status == "already in DB":
                tags.append("db")

            self.tree.insert("", "end", values=(
                url,
                info.get("type", ""),
                info.get("size", ""),
                status,
                info.get("category", ""),
                "★" if info.get("favorite") else ""
            ), tags=tuple(tags))

        self.counter_var.set(f"{self.t('hits')}: {len(self.results)}")
        self.update_top_stats()

    def selected_urls(self):
        if not hasattr(self, "tree"):
            return []
        sel = self.tree.selection()
        return [self.tree.item(item, "values")[0] for item in sel]

    def selected_url(self):
        urls = self.selected_urls()
        return urls[0] if urls else None

    def request_stop(self):
        self.stop_requested = True
        self.log("Stop requested")

    def start_search(self):
        urls = self.start_urls()
        if not urls:
            messagebox.showwarning(APP_NAME, self.t("need_url"))
            return
        if not self.current_project.get():
            messagebox.showwarning(APP_NAME, self.t("need_project"))
            return

        self.stop_requested = False
        self.clear_results()
        self.ensure_project_folders(self.current_project.get())
        self.status_var.set(self.t("search_started"))
        threading.Thread(target=self.search_worker, args=(urls,), daemon=True).start()

    def search_worker(self, start_urls):
        selected_exts = self.selected_extensions()
        max_depth = max(0, int(self.depth_var.get()))
        only_same_host = self.same_host_var.get()
        delay = max(0.0, float(self.delay_var.get()))

        visited = set()
        queue_urls = [(url, 0, url) for url in start_urls]
        checked = 0
        start_time = time.time()

        self.log(f"Search started: {len(start_urls)} URL(s)")

        history = {
            "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "start_urls": start_urls,
            "depth": max_depth
        }

        while queue_urls and not self.stop_requested:
            current, depth, root_url = queue_urls.pop(0)
            if current in visited:
                continue
            visited.add(current)

            if only_same_host and not same_host(root_url, current):
                continue

            try:
                text = fetch_text(current)
                checked += 1

                if text:
                    for link in find_urls(current, text):
                        if only_same_host and not same_host(root_url, link):
                            continue
                        ext = get_ext(link)
                        if ext in selected_exts:
                            self.root.after(0, self.add_result, link, current)
                        if depth < max_depth and ext in HTML_EXTS and link not in visited:
                            queue_urls.append((link, depth + 1, root_url))

                self.ui_queue.put({"kind": "search_progress", "checked": checked, "queue": len(queue_urls), "found": len(self.results), "elapsed": time.time() - start_time})
                time.sleep(delay)
            except Exception as e:
                checked += 1
                self.log(f"Error: {current} -> {e}")

        history["finished_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        history["results"] = len(self.results)
        self.save_history_entry(history)

        self.save_database()
        self.save_results_json()
        self.ui_queue.put({"kind": "status", "text": self.t("search_finished")})
        self.log(self.t("search_finished"))
        self.root.after(0, self.update_dashboard)
        self.root.after(0, self.refresh_explorer)

    def save_history_entry(self, entry):
        try:
            self.history_file().parent.mkdir(parents=True, exist_ok=True)
            history = []
            if self.history_file().exists():
                history = json.loads(self.history_file().read_text(encoding="utf-8"))
            history.append(entry)
            self.history_file().write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            self.log(f"History save error: {e}")

    def save_results_json(self):
        if not self.current_project.get():
            return
        out = self.project_dir() / "logs" / "search_results_latest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"project": self.current_project.get(), "results": list(self.results.values())}, indent=2, ensure_ascii=False), encoding="utf-8")

    def export_csv(self):
        if not self.results:
            messagebox.showinfo(APP_NAME, self.t("no_results"))
            return
        out = self.project_dir() / "logs" / "search_results.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=";")
            writer.writerow(["URL", "Type", "Size", "Status", "Category", "Favorite", "Tags", "Source"])
            for info in self.results.values():
                writer.writerow([info["url"], info["type"], info.get("size", ""), info.get("status", ""), info.get("category", ""), info.get("favorite", ""), ",".join(info.get("tags", [])), info.get("source_url", "")])
        messagebox.showinfo(APP_NAME, str(out))

    def export_txt(self):
        if not self.results:
            messagebox.showinfo(APP_NAME, self.t("no_results"))
            return
        out = self.project_dir() / "logs" / "search_results.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(self.results.keys()), encoding="utf-8")
        messagebox.showinfo(APP_NAME, str(out))

    def import_url_list(self):
        file = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")])
        if not file:
            return
        lines = Path(file).read_text(encoding="utf-8", errors="ignore").splitlines()
        urls = []
        for line in lines:
            line = line.strip().strip(";")
            if not line or line.startswith("#"):
                continue
            if ";" in line:
                line = line.split(";")[0].strip()
            urls.append(line)
        self.urls_text.delete("1.0", "end")
        self.urls_text.insert("1.0", "\n".join(urls))


    def retry_failed_downloads(self):
        urls = [
            url for url, info in self.results.items()
            if str(info.get("status", "")).lower() in ("fehler", "error")
        ]
        if not urls:
            messagebox.showinfo(APP_NAME, self.l("Keine Fehler-Treffer vorhanden.", "No failed results available."))
            return
        self.stop_requested = False
        threading.Thread(target=self.download_worker, args=(urls,), daemon=True).start()

    def download_new_only(self):
        urls = []
        for url, info in self.results.items():
            local = info.get("local_path")
            if local and Path(local).exists():
                continue
            status = str(info.get("status", "")).lower()
            if status in ("vorhanden", "existing", "gespeichert", "saved"):
                continue
            urls.append(url)

        if not urls:
            messagebox.showinfo(APP_NAME, self.l("Keine neuen Dateien zum Download gefunden.", "No new files found for download."))
            return

        self.stop_requested = False
        threading.Thread(target=self.download_worker, args=(urls,), daemon=True).start()

    def search_all_projects(self):
        query = self.search_text_var.get().strip().lower()
        if not query:
            messagebox.showinfo(APP_NAME, self.l("Bitte Suchtext eingeben.", "Please enter search text."))
            return

        results = {}
        base = self.base_dir()
        for db_file in base.glob("*/database.json"):
            try:
                data = json.loads(db_file.read_text(encoding="utf-8"))
                project = data.get("project", db_file.parent.name)
                for url, info in data.get("assets", {}).items():
                    haystack = " ".join([
                        url,
                        str(info.get("category", "")),
                        " ".join(info.get("tags", [])) if isinstance(info.get("tags", []), list) else str(info.get("tags", "")),
                        project
                    ]).lower()
                    if query in haystack:
                        new_info = dict(info)
                        new_info["category"] = f"{project} / {new_info.get('category', '')}"
                        results[url] = new_info
            except Exception as e:
                self.log(f"Cross-project search error: {db_file} -> {e}")

        self.results = results
        self.refresh_tree()
        self.update_top_stats()
        self.log(self.l(f"Projektübergreifende Suche: {len(results)} Treffer", f"Cross-project search: {len(results)} results"))

    def start_download(self):
        if not self.results:
            messagebox.showinfo(APP_NAME, self.t("no_results"))
            return

        urls = self.selected_urls() or list(self.results.keys())
        self.stop_requested = False
        self.ensure_project_folders(self.current_project.get())
        self.status_var.set(self.t("download_started"))
        threading.Thread(target=self.download_worker, args=(urls,), daemon=True).start()

    def target_path_for_url(self, url):
        parsed = urllib.parse.urlparse(url)
        folder = self.project_dir() / type_folder_for_ext(get_ext(url))
        if self.keep_structure_var.get():
            rel = (parsed.netloc + parsed.path).strip("/")
            if not rel or rel.endswith("/"):
                rel += "index.html"
            return folder / rel
        return folder / safe_filename(url)


    def download_url_to_file(self, url, target):
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Referer": url.rsplit("/", 1)[0] + "/"
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                http_status = getattr(resp, "status", 200)
                content_type = resp.headers.get("Content-Type", "")
                content_length = resp.headers.get("Content-Length", "")
                data = resp.read()

            if http_status != 200:
                return {"ok": False, "status_text": f"HTTP {http_status}", "http_status": http_status, "content_type": content_type, "content_length": content_length, "bytes": 0, "reason": f"HTTP {http_status}"}

            if len(data) == 0:
                if target.exists():
                    try:
                        target.unlink()
                    except Exception:
                        pass
                return {"ok": False, "status_text": "0 KB", "http_status": http_status, "content_type": content_type, "content_length": content_length, "bytes": 0, "reason": "0 KB"}

            target.write_bytes(data)
            ok, validation = self.validate_downloaded_file(target)
            if not ok:
                if validation == "0 KB" and target.exists():
                    try:
                        target.unlink()
                    except Exception:
                        pass
                return {"ok": False, "status_text": validation, "http_status": http_status, "content_type": content_type, "content_length": content_length, "bytes": len(data), "reason": validation}

            return {"ok": True, "status_text": "OK", "http_status": http_status, "content_type": content_type, "content_length": content_length, "bytes": len(data), "reason": "OK"}

        except urllib.error.HTTPError as e:
            status = getattr(e, "code", 0)
            if status == 404:
                text = "404 Not Found"
            elif status == 403:
                text = "403 Forbidden"
            else:
                text = f"HTTP {status}"

            if target.exists() and target.stat().st_size == 0:
                try:
                    target.unlink()
                except Exception:
                    pass

            return {"ok": False, "status_text": text, "http_status": status, "content_type": "", "content_length": "", "bytes": 0, "reason": text}

        except Exception as e:
            if target.exists() and target.stat().st_size == 0:
                try:
                    target.unlink()
                except Exception:
                    pass
            return {"ok": False, "status_text": "Fehler", "http_status": "", "content_type": "", "content_length": "", "bytes": 0, "reason": str(e)}

    def download_worker(self, urls):
        total = len(urls)
        delay = max(0.0, float(self.delay_var.get()))
        bytes_done = 0
        start_time = time.time()

        for i, url in enumerate(urls, start=1):
            if self.stop_requested:
                break
            try:
                target = self.target_path_for_url(url)
                target.parent.mkdir(parents=True, exist_ok=True)

                if target.exists() and self.skip_existing_var.get():
                    size = target.stat().st_size
                    bytes_done += size
                    self.results[url]["status"] = self.t("existing")
                    self.results[url]["size"] = format_bytes(size)
                    self.results[url]["local_path"] = str(target)
                else:
                    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = resp.read()
                    target.write_bytes(data)
                    size = len(data)
                    bytes_done += size
                    self.results[url]["status"] = self.t("saved")
                    self.results[url]["size"] = format_bytes(size)
                    self.results[url]["local_path"] = str(target)

                local_path = self.results[url].get("local_path")
                if local_path:
                    ok, reason = self.validate_downloaded_file(local_path)
                    self.results[url]["valid"] = ok
                    self.results[url]["validation"] = reason
                    if not ok:
                        self.results[url]["status"] = self.t("error")
                        self.log(f"Validation warning: {url} -> {reason}")

                self.database[url] = dict(self.results[url])
                self.root.after(0, self.refresh_tree)
            except Exception as e:
                if url in self.results:
                    self.results[url]["status"] = self.t("error")
                    self.database[url] = dict(self.results[url])
                self.log(f"Error: {url} -> {e}")

            self.ui_queue.put({"kind": "download_progress", "done": i, "total": total, "bytes_done": bytes_done, "elapsed": time.time() - start_time})
            time.sleep(delay)

        self.save_database()
        self.save_results_json()
        self.ui_queue.put({"kind": "status", "text": self.t("download_finished")})
        self.log(self.t("download_finished"))
        self.root.after(0, self.update_dashboard)
        self.root.after(0, self.refresh_explorer)

    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def copy_selected_link(self):
        url = self.selected_url()
        if url:
            self.root.clipboard_clear()
            self.root.clipboard_append(url)

    def open_selected_in_browser(self):
        url = self.selected_url()
        if url:
            os.startfile(url)

    def download_selected_only(self):
        urls = self.selected_urls()
        if urls:
            self.stop_requested = False
            threading.Thread(target=self.download_worker, args=(urls,), daemon=True).start()

    def mark_selected_favorite(self):
        urls = self.selected_urls()
        for url in urls:
            if url in self.results:
                self.results[url]["favorite"] = not self.results[url].get("favorite", False)
                self.database[url] = dict(self.results[url])
        self.save_database()
        self.refresh_tree()
        self.update_dashboard()

    def tag_selected(self):
        urls = self.selected_urls()
        if not urls:
            return
        tag = simpledialog.askstring(APP_NAME, "Tag / Kategorie:")
        if not tag:
            return
        for url in urls:
            if url in self.results:
                tags = self.results[url].setdefault("tags", [])
                if tag not in tags:
                    tags.append(tag)
                self.results[url]["category"] = tag
                self.database[url] = dict(self.results[url])
        self.save_database()
        self.refresh_tree()
        self.update_dashboard()

    def export_project_zip(self):
        if not self.current_project.get():
            return
        project = self.project_dir()
        out = project / "exports" / f"{clean_folder_name(self.current_project.get())}_export.zip"
        out.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for file in project.rglob("*"):
                if file.is_file() and file != out:
                    z.write(file, file.relative_to(project))
        messagebox.showinfo(APP_NAME, f"ZIP exported:\n{out}")

    def on_asset_select(self, event=None):
        url = self.selected_url()
        if not url or url not in self.results:
            return
        info = self.results[url]
        text = [
            f"URL: {url}",
            f"Type: {info.get('type', '')}",
            f"Size: {info.get('size', '')}",
            f"Status: {info.get('status', '')}",
            f"Category: {info.get('category', '')}",
            f"Favorite: {info.get('favorite', False)}",
            f"Tags: {', '.join(info.get('tags', []))}",
            f"Valid: {info.get('valid', '')}",
            f"Validation: {info.get('validation', '')}",
            f"Local path: {info.get('local_path', '')}",
            f"Source: {info.get('source_url', '')}",
        ]
        self.selected_info_var.set("\n".join(text))

        if hasattr(self, "preview_text"):
            self.preview_text.configure(state="normal")
            self.preview_text.delete("1.0", "end")
            self.preview_text.insert("1.0", "\n".join(text) + "\n\n")

            local = info.get("local_path")
            ext = info.get("ext", "")
            if local and Path(local).exists() and ext in TEXT_EXTS:
                try:
                    content = Path(local).read_text(encoding="utf-8", errors="ignore")
                    self.preview_text.insert("end", content[:20000])
                except Exception as e:
                    self.preview_text.insert("end", f"Preview error: {e}")
            elif local and Path(local).exists():
                self.preview_text.insert("end", "Binary/media file. Open it from the project folder.\nBinär-/Mediendatei. Über den Projektordner öffnen.")
            else:
                self.preview_text.insert("end", "Not downloaded yet.\nNoch nicht heruntergeladen.")
            self.preview_text.configure(state="disabled")

    def refresh_explorer(self):
        if not hasattr(self, "explorer_tree"):
            return
        for item in self.explorer_tree.get_children():
            self.explorer_tree.delete(item)
        counts = {}
        for info in self.database.values():
            key = info.get("type", "other")
            counts[key] = counts.get(key, 0) + 1
        for key in sorted(counts):
            self.explorer_tree.insert("", "end", text=key, values=(counts[key],))

    def on_explorer_select(self, event=None):
        sel = self.explorer_tree.selection()
        if not sel:
            return
        key = self.explorer_tree.item(sel[0], "text")
        self.results = {url: dict(info) for url, info in self.database.items() if info.get("type") == key}
        self.refresh_tree()

    def update_dashboard(self):
        if not hasattr(self, "dashboard_text"):
            return
        total_db = len(self.database)
        favs = sum(1 for i in self.database.values() if i.get("favorite"))
        counts = {}
        cats = {}
        saved = 0
        size = 0
        for info in self.database.values():
            counts[info.get("type", "other")] = counts.get(info.get("type", "other"), 0) + 1
            cats[info.get("category", "Other")] = cats.get(info.get("category", "Other"), 0) + 1
            if info.get("local_path") and Path(info.get("local_path")).exists():
                saved += 1
                try:
                    size += Path(info.get("local_path")).stat().st_size
                except Exception:
                    pass

        lines = [
            f"Project: {self.current_project.get()}",
            f"Database assets: {total_db}",
            f"Saved files: {saved}",
            f"Favorites: {favs}",
            f"Saved size: {format_bytes(size)}",
            "",
            "By file type:",
        ]
        for k in sorted(counts):
            lines.append(f"  {k:12} {counts[k]}")
        lines.append("")
        lines.append("By category:")
        for k in sorted(cats):
            lines.append(f"  {k:18} {cats[k]}")

        self.dashboard_text.configure(state="normal")
        self.dashboard_text.delete("1.0", "end")
        self.dashboard_text.insert("1.0", "\n".join(lines))
        self.dashboard_text.configure(state="disabled")

    def load_notes(self):
        if not hasattr(self, "notes_text"):
            return
        self.notes_text.configure(state="normal")
        self.notes_text.delete("1.0", "end")
        nf = self.notes_file()
        if nf.exists():
            self.notes_text.insert("1.0", nf.read_text(encoding="utf-8", errors="ignore"))
        else:
            self.notes_text.insert("1.0", f"{self.current_project.get()}\n\n")
        self.notes_text.configure(state="normal")

    def save_notes(self):
        if not hasattr(self, "notes_text"):
            return
        self.notes_file().write_text(self.notes_text.get("1.0", "end").rstrip(), encoding="utf-8")
        self.log("Notes saved.")


    def open_github_profile(self):
        try:
            os.startfile("https://github.com/PraesidentenGamer")
        except Exception as e:
            messagebox.showerror(APP_NAME, str(e))


def main():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    root = tk.Tk()
    AssetScraperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
