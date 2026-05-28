import os
import customtkinter as ctk
from PIL import Image, ImageTk, ImageDraw
from gui.theme import *

class FileCard(ctk.CTkFrame):
    def __init__(self, master, file_data, select_callback, double_click_callback, **kwargs):
        super().__init__(
            master, 
            width=140, 
            height=160, 
            corner_radius=6, 
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD,
            cursor="hand2",
            **kwargs
        )
        self.file_data = file_data
        self.select_callback = select_callback
        self.double_click_callback = double_click_callback
        self.selected = file_data.get('selected', False)
        
        self.file_path = file_data.get('path', '')
        self.file_name = file_data.get('name', '')
        self.file_size = file_data.get('size', 0)
        self.file_ext = file_data.get('ext', '').lower()
        
        # Prevent auto-resizing of frame to fit widgets
        self.pack_propagate(False)
        self.grid_propagate(False)
        
        self.create_widgets()
        self.bind_events_recursively(self)
        self.update_selection_state()

    def get_color_for_extension(self):
        # Return (light_mode_color, dark_mode_color)
        ext = self.file_ext
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            return (PRIMARY, PRIMARY)  # Blue
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv']:
            return (SECONDARY, SECONDARY)  # Green
        elif ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']:
            return ("#EF4444", "#DC2626")  # Red
        elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
            return ("#8B5CF6", "#7C3AED")  # Purple
        else:
            return (TERTIARY, TERTIARY)  # Amber/Orange

    def generate_placeholder_image(self):
        # Create a clean PIL image for the thumbnail
        img = Image.new("RGBA", (120, 85), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        ext = self.file_ext
        colors = self.get_color_for_extension()
        accent_color = colors[1]  # Theme color based on file type
        
        # Draw central icon container
        # Coordinates: 120 width, 85 height
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff']:
            # Photo Icon placeholder (if loading fails)
            # Draw a photo frame card
            draw.rounded_rectangle([(30, 12), (90, 72)], radius=5, fill="#1E293B", outline=accent_color, width=2)
            # Draw mountain peaks inside
            draw.polygon([(40, 60), (55, 35), (70, 60)], fill="#475569")
            draw.polygon([(55, 60), (70, 45), (85, 60)], fill="#334155")
            # Draw sun
            draw.ellipse([(70, 25), (80, 35)], fill="#F59E0B")
            
        elif ext in ['.pdf', '.doc', '.docx', '.txt', '.xls', '.xlsx', '.ppt', '.pptx', '.csv']:
            # Document Icon (Page with folded corner)
            # Draw page outline
            page_pts = [(40, 12), (70, 12), (80, 22), (80, 72), (40, 72)]
            draw.polygon(page_pts, fill="#F8FAFC", outline="#CBD5E1", width=1)
            # Draw the fold triangle
            draw.polygon([(70, 12), (70, 22), (80, 22)], fill="#E2E8F0")
            
            # Draw text lines
            draw.line([(46, 32), (74, 32)], fill="#94A3B8", width=2)
            draw.line([(46, 42), (74, 42)], fill="#94A3B8", width=2)
            draw.line([(46, 52), (62, 52)], fill="#94A3B8", width=2)
            
            # Draw file type badge in accent color at the bottom
            badge_text = ext.replace('.', '').upper()[:4]
            draw.rectangle([(40, 58), (80, 72)], fill=accent_color)
            draw.text((60, 65), badge_text, fill="#FFFFFF", anchor="mm", font=None)
            
        elif ext in ['.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv']:
            # Video Icon (Media frame + Play button)
            draw.rounded_rectangle([(25, 15), (95, 70)], radius=6, fill="#0F172A", outline="#334155", width=2)
            # Draw play triangle in the center
            draw.polygon([(52, 32), (52, 52), (72, 42)], fill=accent_color)
            # Filmstrip border lines on left and right
            for y in range(20, 65, 10):
                draw.rectangle([(28, y), (32, y+5)], fill="#475569")
                draw.rectangle([(88, y), (92, y+5)], fill="#475569")
                
        elif ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']:
            # Audio Icon (Sound Waves)
            draw.rounded_rectangle([(35, 15), (85, 70)], radius=5, fill="#1E293B", outline=accent_color, width=2)
            # Soundwave bars
            draw.rectangle([(45, 37), (48, 47)], fill=accent_color)
            draw.rectangle([(51, 30), (54, 55)], fill=accent_color)
            draw.rectangle([(57, 25), (60, 60)], fill=accent_color)
            draw.rectangle([(63, 33), (66, 52)], fill=accent_color)
            draw.rectangle([(69, 40), (72, 45)], fill=accent_color)
            
        else:
            # Other/Archive Icon (Folder or generic binary gear)
            draw.rounded_rectangle([(30, 20), (90, 68)], radius=5, fill="#1E293B", outline=accent_color, width=2)
            for y in range(28, 62, 6):
                draw.line([(57, y), (63, y)], fill=accent_color, width=2)
            badge_text = ext.replace('.', '').upper()[:3] if ext else "BIN"
            draw.rounded_rectangle([(45, 45), (75, 60)], radius=3, fill=accent_color)
            draw.text((60, 52), badge_text, fill="#FFFFFF", anchor="mm", font=None)
            
        return ctk.CTkImage(light_image=img, dark_image=img, size=(120, 85))

    def get_thumbnail(self):
        if not self.file_path or not os.path.exists(self.file_path):
            return self.generate_placeholder_image()
            
        ext = self.file_ext
        if ext in ['.jpg', '.jpeg', '.png', '.bmp', '.gif']:
            try:
                # Load real image using PIL
                with Image.open(self.file_path) as pil_img:
                    # Create thumbnail preserving aspect ratio
                    pil_img.thumbnail((120, 85))
                    # Place on a transparent canvas of size 120x85 to center it
                    canvas = Image.new("RGBA", (120, 85), (0, 0, 0, 0))
                    x_offset = (120 - pil_img.width) // 2
                    y_offset = (85 - pil_img.height) // 2
                    canvas.paste(pil_img, (x_offset, y_offset))
                    return ctk.CTkImage(light_image=canvas, dark_image=canvas, size=(120, 85))
            except Exception:
                pass
                
        return self.generate_placeholder_image()

    def format_size(self, num_bytes):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if num_bytes < 1024.0:
                return f"{num_bytes:.1f} {unit}"
            num_bytes /= 1024.0
        return f"{num_bytes:.1f} TB"

    def create_widgets(self):
        # Thumbnail area
        self.thumb_label = ctk.CTkLabel(self, text="", image=self.get_thumbnail())
        self.thumb_label.pack(fill="x", padx=6, pady=(6, 2))
        
        # File details container
        self.text_container = ctk.CTkFrame(self, fg_color="transparent")
        self.text_container.pack(fill="both", expand=True, padx=8, pady=(0, 6))
        
        # File name (truncated)
        short_name = self.file_name
        if len(short_name) > 14:
            short_name = short_name[:11] + "..."
            
        self.name_lbl = ctk.CTkLabel(
            self.text_container, 
            text=short_name,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            anchor="w",
            text_color=TEXT_BRIGHT
        )
        self.name_lbl.pack(fill="x", anchor="w", pady=0)
        
        # File size
        size_str = self.format_size(self.file_size)
        self.size_lbl = ctk.CTkLabel(
            self.text_container,
            text=size_str,
            font=ctk.CTkFont(family=FONT_FAMILY, size=10),
            anchor="w",
            text_color=TEXT_MUTED
        )
        self.size_lbl.pack(fill="x", anchor="w", pady=0)
        
        # Selection checkbox (top-right overlay or bottom-right inside card)
        # We place it in the corner of text_container or pack it
        self.chk = ctk.CTkCheckBox(
            self, 
            text="", 
            width=16, 
            height=16,
            checkbox_width=16,
            checkbox_height=16,
            fg_color=PRIMARY,
            hover_color="#2563EB",
            corner_radius=4,
            command=self.on_checkbox_toggle
        )
        self.chk.place(x=114, y=10)
        
        if self.selected:
            self.chk.select()
        else:
            self.chk.deselect()

    def bind_events_recursively(self, widget):
        # Bind click events, ignoring the checkbox itself so it handles its own clicks
        if widget != self.chk:
            widget.bind("<Button-1>", self.on_click)
            widget.bind("<Double-Button-1>", self.on_double_click)
            
        for child in widget.winfo_children():
            self.bind_events_recursively(child)

    def on_click(self, event=None):
        self.selected = not self.selected
        self.update_selection_state()
        self.select_callback(self.file_data, self.selected)

    def on_checkbox_toggle(self):
        self.selected = self.chk.get()
        self.update_selection_state()
        self.select_callback(self.file_data, self.selected)

    def on_double_click(self, event=None):
        self.double_click_callback(self.file_data)

    def update_selection_state(self):
        if self.selected:
            self.configure(
                border_color=PRIMARY,
                border_width=2,
                fg_color=BG_CARD
            )
            self.chk.select()
        else:
            self.configure(
                border_color=BORDER_COLOR,
                border_width=1,
                fg_color=BG_CARD
            )
            self.chk.deselect()

class ThumbnailGrid(ctk.CTkScrollableFrame):
    def __init__(self, master, select_callback, double_click_callback, **kwargs):
        super().__init__(
            master,
            corner_radius=0,
            fg_color="transparent",
            **kwargs
        )
        self.select_callback = select_callback
        self.double_click_callback = double_click_callback
        self.cards = []
        self.files_list = []
        
        # Configure grid column weights to make them align nicely
        for col in range(4):
            self.grid_columnconfigure(col, weight=1, pad=10)

    def render_files(self, files_list):
        self.clear()
        self.files_list = files_list
        
        # Render cards in a 4-column grid layout
        for i, file_data in enumerate(files_list):
            row = i // 4
            col = i % 4
            
            card = FileCard(
                self, 
                file_data=file_data,
                select_callback=self.select_callback,
                double_click_callback=self.double_click_callback
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self.cards.append(card)

    def clear(self):
        for card in self.cards:
            try:
                card.destroy()
            except Exception:
                pass
        self.cards = []
        self.files_list = []
