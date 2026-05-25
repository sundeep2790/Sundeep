import customtkinter as ctk
from gui.theme import *

class DriveCard(ctk.CTkFrame):
    def __init__(self, master, drive_data, select_callback, **kwargs):
        super().__init__(
            master, 
            corner_radius=8, 
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD,
            cursor="hand2",
            **kwargs
        )
        self.drive_data = drive_data
        self.select_callback = select_callback
        self.selected = False
        
        self.device = drive_data.get('device', '')
        self.mountpoint = drive_data.get('mountpoint', '')
        self.fstype = drive_data.get('fstype', 'RAW')
        self.total = drive_data.get('total', 0)
        self.free = drive_data.get('free', 0)
        self.label_text = drive_data.get('label', 'Unknown Disk')
        
        self.total_gb = self.total / (1024 ** 3) if self.total > 0 else 0
        self.free_gb = self.free / (1024 ** 3) if self.free > 0 else 0
        self.used_gb = max(0.0, self.total_gb - self.free_gb)
        
        self.create_widgets()
        self.bind_click_recursively(self, self.on_click)

    def create_widgets(self):
        # Top row: Label/Name of partition
        self.label_lbl = ctk.CTkLabel(
            self, 
            text=self.label_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        self.label_lbl.pack(anchor="w", padx=15, pady=(12, 2))
        
        # Middle row: System details
        details_text = f"Mount: {self.mountpoint}  |  FS: {self.fstype}  |  Device: {self.device}"
        if not self.mountpoint:
            details_text = f"FS: {self.fstype}  |  Device: {self.device}"
            
        self.details_lbl = ctk.CTkLabel(
            self,
            text=details_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED
        )
        self.details_lbl.pack(anchor="w", padx=15, pady=2)
        
        # Bottom row: Capacity indicators
        if self.total > 0:
            cap_text = f"{self.used_gb:.1f} GB used of {self.total_gb:.1f} GB ({self.free_gb:.1f} GB free)"
            self.cap_lbl = ctk.CTkLabel(
                self,
                text=cap_text,
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="normal"),
                text_color=TEXT_MUTED
            )
            self.cap_lbl.pack(anchor="w", padx=15, pady=(2, 6))
            
            self.progress = ctk.CTkProgressBar(
                self, 
                height=6,
                progress_color=PRIMARY,
                fg_color=BORDER_COLOR
            )
            self.progress.pack(fill="x", padx=15, pady=(0, 12))
            self.progress.set(self.used_gb / self.total_gb if self.total_gb > 0 else 0)
        else:
            # Partition with unknown size
            self.cap_lbl = ctk.CTkLabel(
                self,
                text="Size Unknown or Unallocated space",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="normal"),
                text_color=TERTIARY
            )
            self.cap_lbl.pack(anchor="w", padx=15, pady=(2, 12))

    def bind_click_recursively(self, widget, callback):
        widget.bind("<Button-1>", callback)
        for child in widget.winfo_children():
            self.bind_click_recursively(child, callback)

    def on_click(self, event=None):
        self.select_callback(self)

    def set_selected(self, selected: bool):
        self.selected = selected
        if selected:
            self.configure(
                border_color=PRIMARY,
                border_width=2,
                fg_color=BG_CARD
            )
        else:
            self.configure(
                border_color=BORDER_COLOR,
                border_width=1,
                fg_color=BG_CARD
            )
