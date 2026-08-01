import customtkinter as ctk
from PIL import Image
import os
import sys
import requests
import json
import io
import threading
from tkinter import filedialog, messagebox

# Get icon.ico path
if getattr(sys, 'frozen', False):
    icon_path = os.path.join(sys._MEIPASS, "images", "icon.ico")
else:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "images", "icon.ico")

ctk.set_appearance_mode("dark")

class PyModFetch(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PyModFetch")
        self.geometry("960x540")
        self.iconbitmap(icon_path)
        self.configure(fg_color=("#f3f3f3", "#1a1a1a"))

        # Grid config
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=0)
        self.grid_rowconfigure(2, weight=1)

        self.grid_columnconfigure(0, weight=0, minsize=150)
        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(2, weight=0) 

        # Store category info
        self.current_category = "Mods"      # Currently selected category
        self.category_buttons = []          # list

        # Search values n stuff
        self.current_page = 1
        self.limit = 10
        self.sort_by = "relevance"
        self.total_results = 0
        self.offset = 0

        # Filter vars
        self.game_version_var = ctk.StringVar(value="All")
        self.loader_var = ctk.StringVar(value="All")

        # Actually build the thang
        self.create_header()
        self.create_sidebar()
        self.create_controls()
        self.create_results_area()
        self.select_category("Mods")        # Initial search w/"Mods"

    # Header (very top part)
    def create_header(self):
        header_frame = ctk.CTkFrame(
            self,
            height=100,
            corner_radius=0,
            fg_color="transparent"
        )
        header_frame.grid(row=0, columnspan=3, sticky="ew", padx=0, pady=0)
        header_frame.grid_propagate(False)
        
        header_frame.grid_rowconfigure(0, weight=1)
        header_frame.grid_rowconfigure(1, weight=1)
        header_frame.grid_columnconfigure(0, weight=0, minsize=150)
        header_frame.grid_columnconfigure(1, weight=1)

        # Logo img + powered by text (top left inside header)
        left_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_frame.grid(row=0, column=0, rowspan=2, sticky="w", padx=(15, 0))

        script_dir = os.path.dirname(os.path.abspath(__file__))
        image_path = os.path.join(script_dir, "images", "icon.ico")

        logo_img = ctk.CTkImage(
            light_image=Image.open(image_path),
            dark_image=Image.open(image_path),
            size=(60, 60)
        )
        logo_label = ctk.CTkLabel(left_frame, image=logo_img, text="")
        logo_label.pack(side="left", padx=(0, 1), pady=15)

        text_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        text_frame.pack(side="left")

        pwrdby_label = ctk.CTkLabel(
            text_frame,
            text="Powered by\n  modrinth API",
            font=("Segoe UI Semibold", 13),
            text_color="#f0f0f0",
            justify="center"
        )
        pwrdby_label.pack(anchor="w", pady=0)

        # Category btns + search bar (inside the header)
        right_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_frame.grid(row=0, column=1, rowspan=2, sticky="ew", padx=(55, 15))

        # Category btns
        btn_frame = ctk.CTkFrame(right_frame, fg_color="#303030")
        btn_frame.pack(anchor="w", fill="x", pady=(10, 5))

        categories = ["Mods", "Resource Packs", "Data Packs", "Shaders", "Modpacks", "Plugins", "Servers"]
        for i in range(len(categories)):
            btn_frame.grid_columnconfigure(i, weight=1)

        self.category_buttons = []

        for i, cat in enumerate(categories):
            btn = ctk.CTkButton(
                btn_frame,
                text=cat,
                font=("Segoe UI Semibold", 12),
                fg_color="transparent",
                text_color="#f0f0f0",
                hover_color="#2a2a2a",
                corner_radius=6,
                height=30,
                command=lambda c=cat: self.select_category(c)
            )
            btn.grid(row=0, column=i, padx=2, sticky="ew")
            self.category_buttons.append((cat, btn))

        # Search bar
        search_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        search_frame.pack(anchor="w", fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Search...",
            font=("Segoe UI", 14),
            height=30
        )
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        search_btn = ctk.CTkButton(
            search_frame,
            text="Search",
            font=("Segoe UI Semibold", 14),
            text_color="#1bd96a",
            fg_color="#24553d",
            hover_color="#317454",
            width=80,
            height=30,
            command=lambda: self.perform_search(reset_page=True)
        )
        search_btn.pack(side="left")

        # Bind "enter" to "search"
        self.search_entry.bind("<Return>", lambda event: self.perform_search(reset_page=True))

    # Actual search func logic
    def perform_search(self, reset_page=False):
        if reset_page:
            self.current_page = 1

        query = self.search_entry.get().strip()
        type_map = {
            "Mods": "mod",
            "Resource Packs": "resourcepack",
            "Data Packs": "datapack",
            "Shaders": "shader",
            "Modpacks": "modpack",
            "Plugins": "plugin",
            "Servers": "server"
        }
        project_type = type_map.get(self.current_category, "mod")
        sort = self.sort_var.get()
        limit = int(self.limit_var.get())
        offset = (self.current_page - 1) * limit

        url = "https://api.modrinth.com/v2/search"

        # Build facets dynamically
        facets = [
            [f"project_type:{project_type}"]
        ]
        version = self.game_version_var.get()
        if version != "All":
            facets.append([f"versions:{version}"])
        loader = self.loader_var.get()
        if loader != "All":
            facets.append([f"categories:{loader}"])

        facets_json = json.dumps(facets)

        params = {
            "query": query,
            "facets": facets_json,
            "limit": limit,
            "offset": offset
        }
        if sort != "relevance":
            params["sort"] = sort

        # Show loading text UI and clear
        self.loading_label.pack(pady=50)
        self.clear_results()

        # Run API call in a thread!!
        def fetch():
            try:
                response = requests.get(url, params=params)
                data = response.json()
                hits = data.get("hits", [])
                total = data.get("total_hits", 0)
                self.after(0, lambda: self.on_search_complete(hits, total))
            except Exception as e:
                self.after(0, lambda: self.display_error(str(e)))

        threading.Thread(target=fetch, daemon=True).start()

    # Called when the API response arrives / hides + displays results
    def on_search_complete(self, hits, total):
        self.loading_label.pack_forget() # Hide loading UI
        self.total_results = total
        self.update_page_label()
        self.display_results(hits)

    # Show error msg in the result area...
    def display_error(self, msg):
        self.loading_label.pack_forget()
        self.clear_results()
        label = ctk.CTkLabel(self.results_frame, text=f"Error: {msg}", text_color="red")
        label.pack(pady=50)

    # Remove everything except loading label
    def clear_results(self):
            for widget in self.results_frame.winfo_children():
                if widget != self.loading_label:
                    widget.destroy()

    # Sidebar filters and whatnot
    def create_sidebar(self):
        self.sidebar_frame = ctk.CTkFrame(
            self,
            width=185,
            corner_radius=0,
            fg_color="transparent"
        )
        self.sidebar_frame.grid(row=1, column=0, rowspan=2, sticky="nsw", padx=0, pady=0)
        self.sidebar_frame.grid_propagate(False)

        # Scrollable frame creation
        self.sidebar_content = ctk.CTkScrollableFrame(
            self.sidebar_frame,
            fg_color="#1a1a1a",
            corner_radius=0
        )
        self.sidebar_content.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkFrame(self.sidebar_content, height=2, fg_color="#303030").pack(fill="x", padx=12, pady=(0, 8))

        # Filter header txt
        header_label = ctk.CTkLabel(
            self.sidebar_content,
            text="Filters",
            font=("Segoe UI semibold", 14),
            text_color="#f0f0f0"
        )
        header_label.pack(anchor="w", padx=12, pady=(8, 0))

        # Game Version
        version_label = ctk.CTkLabel(
            self.sidebar_content,
            text="Game Version",
            font=("Segoe UI", 12),
            text_color="#a0a0a0"
        )
        version_label.pack(anchor="w", padx=12, pady=(0, 2))

        # MC versions
        version_values = [
            "All",
            "1.21.1",
            "1.21",
            "1.20.6",
            "1.20.4",
            "1.20.2",
            "1.20.1",
            "1.19.4",
            "1.19.2",
            "1.18.2",
            "1.17.1",
            "1.16.5",
            "1.15.2",
            "1.14.4",
            "1.13.2",
            "1.12.2"
        ]

        version_menu = ctk.CTkOptionMenu(
            self.sidebar_content,
            values=version_values,
            variable=self.game_version_var,
            width=150,
            fg_color="#2a2a2a",
            button_color="#2a2a2a",
            button_hover_color="#3a3a3a",
            text_color="#f0f0f0",
            dropdown_fg_color="#2a2a2a",
            dropdown_text_color="#f0f0f0",
            command=lambda _: self.perform_search(reset_page=True)
        )
        version_menu.pack(anchor="w", padx=12, pady=(0, 14))

        # Loader
        loader_label = ctk.CTkLabel(
            self.sidebar_content,
            text="Loader",
            font=("Segoe UI", 12),
            text_color="#a0a0a0"
        )
        loader_label.pack(anchor="w", padx=12, pady=(0, 4))

        loader_menu = ctk.CTkOptionMenu(
            self.sidebar_content,
            values=["All", "fabric", "forge", "quilt", "neoforge"],
            variable=self.loader_var,
            width=150,
            fg_color="#2a2a2a",
            button_color="#2a2a2a",
            button_hover_color="#3a3a3a",
            text_color="#f0f0f0",
            dropdown_fg_color="#2a2a2a",
            dropdown_text_color="#f0f0f0",
            command=lambda _: self.perform_search(reset_page=True)
        )
        loader_menu.pack(anchor="w", padx=12, pady=(0, 12))

    # Category selection
    def select_category(self, category):
        # Update highlited category + btns
        self.current_category = category

        # Reset all buttons to inactive
        for cat, btn in self.category_buttons:
            if cat == category:
                btn.configure(fg_color="#24553d", text_color="#1bd96a", hover_color="#317454")
            else:
                btn.configure(fg_color="transparent", text_color="#f0f0f0", hover_color="#2a2a2a")

        # Update sidebar
        self.perform_search(reset_page=True)

    # Options to change content and page selection!
    def create_controls(self):
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=1, column=1, sticky="ew", padx=10, pady=0, ipady=0)
        controls_frame.grid_columnconfigure(0, weight=1)

        # Sort by dropdown
        sort_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        sort_frame.grid(row=0, column=0, sticky="w")

        sort_label = ctk.CTkLabel(
            sort_frame,
            text="Sort by:",
            font=("Segoe UI", 12),
            text_color="#a0a0a0"
        )
        sort_label.pack(side="left", padx=(0, 5))

        self.sort_var = ctk.StringVar(value="relevance")
        sort_menu = ctk.CTkOptionMenu(
            sort_frame,
            values=["relevance", "downloads"],
            variable=self.sort_var,
            width=100,
            fg_color="#2a2a2a",
            button_color="#2a2a2a",
            button_hover_color="#3a3a3a",
            text_color="#f0f0f0",
            dropdown_fg_color="#2a2a2a",
            dropdown_text_color="#f0f0f0",
            command=lambda _: self.perform_search(reset_page=True)
        )
        sort_menu.pack(side="left")

        # Per page dropdown
        limit_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        limit_frame.grid(row=0, column=1, padx=20)

        limit_label = ctk.CTkLabel(
            limit_frame,
            text="Per page:",
            font=("Segoe UI", 12),
            text_color="#a0a0a0"
        )
        limit_label.pack(side="left", padx=(0, 5))

        self.limit_var = ctk.StringVar(value="10")
        limit_menu = ctk.CTkOptionMenu(
            limit_frame,
            values=["5", "10", "15", "20", "50", "100"],
            variable=self.limit_var,
            width=70,
            fg_color="#2a2a2a",
            button_color="#2a2a2a",
            button_hover_color="#3a3a3a",
            text_color="#f0f0f0",
            dropdown_fg_color="#2a2a2a",
            dropdown_text_color="#f0f0f0",
            command=lambda _: self.perform_search(reset_page=True)
        )
        limit_menu.pack(side="left")

        # Page selection
        page_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        page_frame.grid(row=0, column=2, sticky="e")

        self.page_label = ctk.CTkLabel(
            page_frame,
            text="Page 1",
            font=("Segoe UI", 12),
            text_color="#f0f0f0"
        )
        self.page_label.pack(side="left", padx=(0, 10))

        prev_btn = ctk.CTkButton(
            page_frame,
            text="◀",
            font=("Segoe UI", 14),
            width=30,
            height=30,
            fg_color="#303030",
            hover_color="#404040",
            text_color="#f0f0f0",
            command=self.prev_page
        )
        prev_btn.pack(side="left", padx=2)

        next_btn = ctk.CTkButton(
            page_frame,
            text="▶",
            font=("Segoe UI", 14),
            width=30,
            height=30,
            fg_color="#303030",
            hover_color="#404040",
            text_color="#f0f0f0",
            command=self.next_page
            )
        next_btn.pack(side="left", padx=2)

    # Go to next page
    def next_page(self):
        limit = int(self.limit_var.get())
        if self.current_page * limit < self.total_results:
            self.current_page += 1
            self.perform_search()

    # Go to prev page
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.perform_search()

    # Update page num
    def update_page_label(self):
        self.page_label.configure(text=f"Page {self.current_page}")

    # Results area, the actual downloadable content
    def create_results_area(self):
        # Scrollable frame creation
        self.results_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent"
        )
        self.results_frame.grid(row=2, column=1, sticky="nsew", padx=(0, 10), pady=10)

        # Loading text
        self.loading_label = ctk.CTkLabel(
            self.results_frame,
            text="Loading...",
            font=("Segoe UI", 16),
            text_color="#a0a0a0"
        )
        self.loading_label.pack(pady=50)
        self.loading_label.pack_forget()

    # Show results/mods/things
    def display_results(self, hits):
        # Clear old results (keep loading label)
        for widget in self.results_frame.winfo_children():
            if widget != self.loading_label:
                widget.destroy()

        if not hits:
            label = ctk.CTkLabel(self.results_frame, text="No results found")
            label.pack(pady=50)
            return

        # Loader color map (colored text, dark background)
        loader_colors = {
            "fabric": "#d6b4a8",
            "forge": "#e1694a",
            "quilt": "#d5c7a9",
            "neoforge": "#8a2be2"
        }

        for item in hits:
            card = ctk.CTkFrame(self.results_frame, fg_color="#2a2a2a", corner_radius=8)
            card.pack(fill="x", pady=5, padx=5)
            card.pack_propagate(False)
            card.configure(height=80)

            # Icon
            icon_url = item.get("icon_url")
            icon_label = ctk.CTkLabel(card, text="📦")
            icon_label.pack(side="left", padx=10, pady=10)

            def load_icon(url, label):
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        img_data = response.content
                        img = Image.open(io.BytesIO(img_data))
                        img = img.resize((50, 50), Image.Resampling.LANCZOS)
                        icon_img = ctk.CTkImage(light_image=img, dark_image=img, size=(50, 50))
                        self.after(0, lambda: label.configure(image=icon_img, text=""))
                except Exception as e:
                    print(f"Failed to load icon: {e}")

            if icon_url:
                threading.Thread(target=load_icon, args=(icon_url, icon_label), daemon=True).start()

            text_frame = ctk.CTkFrame(card, fg_color="transparent")
            text_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

            # Title and author row
            top_row = ctk.CTkFrame(text_frame, fg_color="transparent")
            top_row.pack(anchor="w", fill="x")

            title = ctk.CTkLabel(
                top_row,
                text=item.get("title", "Unknown"),
                font=("Segoe UI", 14, "bold"),
                text_color="#f0f0f0"
            )
            title.pack(side="left")

            author = item.get("author", "Unknown")
            author_label = ctk.CTkLabel(
                top_row,
                text=f" by {author}",
                font=("Segoe UI", 12),
                text_color="#6f6e73"
            )
            author_label.pack(side="left", padx=(4, 0))

            # Downloads + Loader badge
            info_row = ctk.CTkFrame(text_frame, fg_color="transparent")
            info_row.pack(anchor="w", fill="x", pady=(2, 0))

            # Download count
            downloads = item.get("downloads", 0)
            dl_label = ctk.CTkLabel(
                info_row,
                text=f"⬇ {downloads:,}",
                font=("Segoe UI", 12),
                text_color="#a0a0a0"
            )
            dl_label.pack(side="left", padx=(0, 10))

            # Loader badges
            categories = item.get("categories", [])
            loaders = [l for l in loader_colors.keys() if l in categories]
            if loaders:
                badge_container = ctk.CTkFrame(info_row, fg_color="transparent")
                badge_container.pack(side="left", fill="x", expand=True)

                for loader in loaders:
                    color = loader_colors.get(loader, "#ffffff")
                    badge = ctk.CTkButton(
                        badge_container,
                        text=loader.capitalize(),
                        font=("Segoe UI Semibold", 11),
                        text_color=color,
                        fg_color="#222222",
                        hover_color="#222222",
                        border_width=1,
                        border_color=color,
                        corner_radius=12,
                        width=55,
                        height=24,
                        command=lambda: None
                    )
                    badge.pack(side="left", padx=(0, 4))

            # Download btn
            download_btn = ctk.CTkButton(
                card,
                text="Download",
                font=("Segoe UI", 12, "bold"),
                fg_color="#24553d",
                hover_color="#317454",
                text_color="#1bd96a",
                width=80,
                height=30,
                command=lambda s=item.get("slug"): self.download_file(s)
            )
            download_btn.pack(side="right", padx=(0, 15))

    # Download logic + prog UI
    def download_file(self, slug):
        folder = filedialog.askdirectory()
        if not folder:
            return

        # Create prog window
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("Downloading...")
        progress_window.geometry("350x130")
        progress_window.resizable(False, False)
        progress_window.configure(fg_color="#1a1a1a")
        progress_window.grab_set()

        # txt
        label = ctk.CTkLabel(
            progress_window,
            text="Preparing download...",
            font=("Segoe UI", 13),
            text_color="#f0f0f0"
        )
        label.pack(pady=(15, 5))

        # Prog bar
        progress_bar = ctk.CTkProgressBar(
            progress_window,
            width=280,
            height=12,
            progress_color="#1bd96a",
            fg_color="#2a2a2a",
            corner_radius=8
        )
        progress_bar.pack(pady=10)
        progress_bar.set(0)

        # Run download in a thread
        def download_thread():
            try:
                response = requests.get(f"https://api.modrinth.com/v2/project/{slug}/version")
                versions = response.json()
                if not versions:
                    raise Exception("No versions found.")
                url = versions[0]["files"][0]["url"]
                filename = versions[0]["files"][0]["filename"]

                filepath = os.path.join(folder, filename)
                file_response = requests.get(url, stream=True)
                total_size = int(file_response.headers.get('content-length', 0))
                downloaded = 0

                with open(filepath, "wb") as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size:
                            progress = downloaded / total_size
                            progress_window.after(0, lambda p=progress: progress_bar.set(p))
                            progress_window.after(0, lambda p=progress: label.configure(
                                text=f"Downloading: {int(p*100)}%"
                            ))

                progress_window.after(0, progress_window.destroy)
                self.after(0, lambda: messagebox.showinfo(
                    "Download Complete",
                    f"Saved to:\n{filepath}"
                ))

            except Exception as e:
                progress_window.after(0, progress_window.destroy)
                self.after(0, lambda: messagebox.showerror(
                    "Error",
                    str(e)
                ))

        threading.Thread(target=download_thread, daemon=True).start()


# Create and run
if __name__ == "__main__":
    app = PyModFetch()
    app.mainloop()
