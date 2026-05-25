import os
import customtkinter as ctk
from PIL import Image
from gui.components.thumbnail_grid import ThumbnailGrid
from gui.components.credit_modal import CreditModal
from gui.theme import *

class ScreenResults(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.active_tab = "All"
        self.active_size_filter = "All Sizes"
        self.selected_files = []
        self.all_files = []
        self.active_preview_file = None
        
        self.create_widgets()

    def create_widgets(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. Header & Filters Row
        filter_row = ctk.CTkFrame(self.container, fg_color="transparent")
        filter_row.pack(fill="x", pady=(0, 10))
        
        # Tabs
        self.tabs_frame = ctk.CTkFrame(filter_row, fg_color="transparent")
        self.tabs_frame.pack(side="left")
        
        self.tab_buttons = {}
        tabs = ["All", "Photos", "Videos", "Documents", "Other"]
        for tab in tabs:
            btn = ctk.CTkButton(
                self.tabs_frame,
                text=tab,
                width=80,
                height=30,
                corner_radius=15,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                fg_color=BG_CARD,
                text_color=TEXT_BRIGHT,
                hover_color=BORDER_COLOR,
                command=lambda t=tab: self.select_tab(t)
            )
            btn.pack(side="left", padx=4)
            self.tab_buttons[tab] = btn
            
        # Select "All" tab by default
        self.highlight_tab("All")
        
        # Size Dropdown Filter
        self.size_menu = ctk.CTkOptionMenu(
            filter_row,
            values=["All Sizes", "< 100 KB", "100 KB - 1 MB", "1 MB - 10 MB", "> 10 MB"],
            width=140,
            height=30,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="normal"),
            fg_color=BG_CARD,
            button_color=BORDER_COLOR,
            button_hover_color=PRIMARY,
            command=self.select_size_filter
        )
        self.size_menu.pack(side="right", padx=5)
        
        size_lbl = ctk.CTkLabel(
            filter_row,
            text="Filter Size:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="normal"),
            text_color=TEXT_MUTED
        )
        size_lbl.pack(side="right", padx=5)

        # 2. Main Middle Area: Left (Scrollable ThumbnailGrid) | Right (Preview Metadata Card)
        mid_row = ctk.CTkFrame(self.container, fg_color="transparent")
        mid_row.pack(fill="both", expand=True, pady=(0, 15))
        
        # Left Panel (Grid)
        grid_container = ctk.CTkFrame(
            mid_row,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        grid_container.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.thumb_grid = ThumbnailGrid(
            grid_container, 
            select_callback=self.on_file_selected_toggle,
            double_click_callback=self.on_file_double_clicked
        )
        self.thumb_grid.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Right Panel (Preview Card)
        self.preview_panel = ctk.CTkFrame(
            mid_row,
            width=240,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        self.preview_panel.pack(side="right", fill="both", expand=False, padx=(10, 0))
        self.preview_panel.pack_propagate(False)
        
        # Preview contents setup
        self.setup_preview_panel()

        # 3. Bottom CTA and Credit status Row
        bottom_row = ctk.CTkFrame(
            self.container,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        bottom_row.pack(fill="x")
        
        # Left bottom: stats
        self.stats_lbl = ctk.CTkLabel(
            bottom_row,
            text="Selected: 0 files (0 KB)  |  Cost: 0 Credits  |  Balance: 0 Credits",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        self.stats_lbl.pack(side="left", padx=15, pady=15)
        
        # Right bottom: Actions
        self.cta_btn = ctk.CTkButton(
            bottom_row,
            text="Recover Selected Files",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=SECONDARY,
            hover_color="#0D9488",
            height=36,
            command=self.on_cta_clicked
        )
        self.cta_btn.pack(side="right", padx=15, pady=10)
        
        self.back_btn = ctk.CTkButton(
            bottom_row,
            text="Back",
            width=80,
            height=36,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=BG_CARD,
            text_color=TEXT_BRIGHT,
            hover_color=BORDER_COLOR,
            command=self.go_back
        )
        self.back_btn.pack(side="right", padx=(0, 10), pady=10)

    def setup_preview_panel(self):
        # Header title
        title = ctk.CTkLabel(
            self.preview_panel,
            text="Preview & Metadata",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        title.pack(anchor="w", padx=15, pady=(12, 5))
        
        # Separator
        sep = ctk.CTkFrame(self.preview_panel, height=1, fg_color=BORDER_COLOR)
        sep.pack(fill="x", padx=15, pady=2)
        
        # Container for changing content
        self.preview_content = ctk.CTkFrame(self.preview_panel, fg_color="transparent")
        self.preview_content.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Default placeholder when nothing is active
        self.show_default_preview()

    def show_default_preview(self):
        for w in self.preview_content.winfo_children():
            w.destroy()
            
        lbl = ctk.CTkLabel(
            self.preview_content,
            text="Double-click a file card\nto preview its contents\nand view metadata.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
            justify="center"
        )
        lbl.pack(fill="both", expand=True)

    def show_file_preview(self, file_data):
        for w in self.preview_content.winfo_children():
            w.destroy()
            
        self.active_preview_file = file_data
        
        # 1. Preview box (Image or placeholder text/code box)
        preview_box = ctk.CTkFrame(
            self.preview_content,
            height=130,
            corner_radius=4,
            fg_color=BG_MAIN,
            border_width=1,
            border_color=BORDER_COLOR
        )
        preview_box.pack(fill="x", pady=(0, 10))
        preview_box.pack_propagate(False)
        
        file_path = file_data.get('path', '')
        ext = file_data.get('ext', '').lower()
        
        # Render preview inside box
        rendered = False
        if file_path and os.path.exists(file_path):
            if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
                try:
                    # Load and scale for preview
                    with Image.open(file_path) as pil_img:
                        pil_img.thumbnail((200, 120))
                        # Center in canvas
                        canvas = Image.new("RGBA", (200, 120), (0, 0, 0, 0))
                        x = (200 - pil_img.width) // 2
                        y = (120 - pil_img.height) // 2
                        canvas.paste(pil_img, (x, y))
                        
                        img_widget = ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(200, 120))
                        lbl = ctk.CTkLabel(preview_box, text="", image=img_widget)
                        lbl.pack(fill="both", expand=True)
                        rendered = True
                except Exception:
                    pass
            elif ext in ['.txt', '.log']:
                try:
                    # Read first few lines of text
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = [f.readline() for _ in range(7)]
                    txt_content = "".join(lines)[:250]
                    
                    tb = ctk.CTkTextbox(
                        preview_box,
                        font=ctk.CTkFont(family=FONT_TECH, size=9),
                        fg_color="transparent",
                        text_color=TEXT_BRIGHT,
                        activate_scrollbars=False
                    )
                    tb.pack(fill="both", expand=True, padx=4, pady=4)
                    tb.insert("1.0", txt_content)
                    tb.configure(state="disabled")
                    rendered = True
                except Exception:
                    pass
                    
        if not rendered:
            # Fallback graphical indicator based on type
            ext_label = ext.replace('.', '').upper() if ext else "FILE"
            lbl = ctk.CTkLabel(
                preview_box,
                text=f"[{ext_label}]\nNo Preview Available",
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
                text_color=TEXT_MUTED,
                justify="center"
            )
            lbl.pack(fill="both", expand=True)
            
        # 2. Metadata details
        lbl_style = ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold")
        val_style = ctk.CTkFont(family=FONT_FAMILY, size=11)
        
        meta_container = ctk.CTkFrame(self.preview_content, fg_color="transparent")
        meta_container.pack(fill="both", expand=True)
        
        metadata = [
            ("File Name:", file_data.get('name', 'Unknown')),
            ("Extension:", ext),
            ("Size:", self.format_size(file_data.get('size', 0))),
            ("Folder:", "recup_dir.1"),
            ("Status:", "Recoverable ✓")
        ]
        
        for label, val in metadata:
            row = ctk.CTkFrame(meta_container, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            lbl_w = ctk.CTkLabel(row, text=label, font=lbl_style, text_color=TEXT_MUTED, width=80, anchor="w")
            lbl_w.pack(side="left")
            
            # Truncate value if too long
            short_val = str(val)
            if len(short_val) > 20:
                short_val = short_val[:17] + "..."
                
            val_w = ctk.CTkLabel(row, text=short_val, font=val_style, text_color=TEXT_BRIGHT, anchor="w")
            val_w.pack(side="left", fill="x", expand=True)

    def select_tab(self, tab):
        self.active_tab = tab
        self.highlight_tab(tab)
        self.apply_filters()

    def highlight_tab(self, active_tab):
        for tab, btn in self.tab_buttons.items():
            if tab == active_tab:
                btn.configure(fg_color=PRIMARY, text_color=TEXT_BRIGHT)
            else:
                btn.configure(fg_color=BG_CARD, text_color=TEXT_BRIGHT)

    def select_size_filter(self, size_filter):
        self.active_size_filter = size_filter
        self.apply_filters()

    def apply_filters(self):
        # Filter files by Tab extension & Size
        filtered = []
        for f in self.all_files:
            ext = f.get('ext', '').lower()
            size = f.get('size', 0)
            
            # 1. Filter by extension tab
            match_tab = False
            if self.active_tab == "All":
                match_tab = True
            elif self.active_tab == "Photos" and ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
                match_tab = True
            elif self.active_tab == "Videos" and ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv']:
                match_tab = True
            elif self.active_tab == "Documents" and ext in ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv']:
                match_tab = True
            elif self.active_tab == "Other" and ext not in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv']:
                match_tab = True
                
            if not match_tab:
                continue
                
            # 2. Filter by size dropdown
            match_size = False
            if self.active_size_filter == "All Sizes":
                match_size = True
            elif self.active_size_filter == "< 100 KB" and size < 100 * 1024:
                match_size = True
            elif self.active_size_filter == "100 KB - 1 MB" and 100 * 1024 <= size <= 1 * 1024 * 1024:
                match_size = True
            elif self.active_size_filter == "1 MB - 10 MB" and 1 * 1024 * 1024 <= size <= 10 * 1024 * 1024:
                match_size = True
            elif self.active_size_filter == "> 10 MB" and size > 10 * 1024 * 1024:
                match_size = True
                
            if match_size:
                filtered.append(f)
                
        # Render filtered list
        self.thumb_grid.render_files(filtered)

    def on_file_selected_toggle(self, file_data, selected):
        # Update inside all_files structure
        for f in self.all_files:
            if f['path'] == file_data['path']:
                f['selected'] = selected
                break
        self.recalculate_cost()

    def on_file_double_clicked(self, file_data):
        self.show_file_preview(file_data)

    def recalculate_cost(self):
        self.selected_files = [f for f in self.all_files if f.get('selected', False)]
        count = len(self.selected_files)
        total_size = sum(f.get('size', 0) for f in self.selected_files)
        
        # 1 credit cost per file
        cost = count
        
        balance = self.app.app_state['credits']
        is_lifetime = self.app.app_state['is_lifetime']
        
        # Format sizes
        size_str = self.format_size(total_size)
        
        # Display stats
        if is_lifetime:
            self.stats_lbl.configure(
                text=f"Selected: {count} files ({size_str})  |  Cost: 0 Credits (Lifetime Pro 💎)  |  Balance: Unlimited",
                text_color=SECONDARY
            )
            self.cta_btn.configure(text="Recover Selected Files", fg_color=SECONDARY, hover_color="#0D9488", state="normal" if count > 0 else "disabled")
        else:
            self.stats_lbl.configure(
                text=f"Selected: {count} files ({size_str})  |  Cost: {cost} Credits  |  Balance: {balance} Credits",
                text_color=TEXT_BRIGHT
            )
            
            # Check balance sufficiency
            if count == 0:
                self.cta_btn.configure(text="Recover Selected Files", fg_color=SECONDARY, hover_color="#0D9488", state="disabled")
            elif balance >= cost:
                self.cta_btn.configure(text="Recover Selected Files", fg_color=SECONDARY, hover_color="#0D9488", state="normal")
            else:
                # Insufficient balance
                deficit = cost - balance
                self.stats_lbl.configure(text_color="#EF4444")  # Alert color
                self.cta_btn.configure(text=f"Buy Credits (Need {deficit} more)", fg_color=PRIMARY, hover_color="#2563EB", state="normal")

    def on_cta_clicked(self):
        count = len(self.selected_files)
        if count == 0:
            return
            
        balance = self.app.app_state['credits']
        is_lifetime = self.app.app_state['is_lifetime']
        cost = count
        
        if not is_lifetime and balance < cost:
            # Need to buy credits
            self.app.open_buy_credits()
        else:
            # Enough credits or lifetime - proceed to pay & restore step!
            self.app.app_state['selected_files'] = self.selected_files
            self.app.show_screen("pay")

    def refresh_credits_display(self):
        self.recalculate_cost()

    def format_size(self, num_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if num_bytes < 1024.0:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} TB"

    def go_back(self):
        # Navigate back to scan page
        self.app.show_screen("scan")

    def on_show(self):
        # Reset selections and reload files
        self.all_files = self.app.app_state['file_tree'] or []
        
        # Sort files by name
        self.all_files.sort(key=lambda x: x.get('name', ''))
        
        self.active_tab = "All"
        self.active_size_filter = "All Sizes"
        self.size_menu.set("All Sizes")
        self.highlight_tab("All")
        
        self.apply_filters()
        self.show_default_preview()
        self.recalculate_cost()
