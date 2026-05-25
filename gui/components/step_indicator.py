import customtkinter as ctk
from gui.theme import *

class StepIndicator(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.steps = [
            "Select Drive",
            "Scan Disk",
            "Browse Files",
            "Save & Restore"
        ]
        self.current_step = 1  # 1-based index
        self.step_labels = []
        self.step_dots = []
        self.create_widgets()
        
    def create_widgets(self):
        for i, step_name in enumerate(self.steps, 1):
            step_frame = ctk.CTkFrame(self, fg_color="transparent")
            step_frame.pack(anchor="w", pady=12, fill="x")
            
            # Indicator dot/number
            dot = ctk.CTkLabel(
                step_frame,
                text=str(i),
                width=26,
                height=26,
                fg_color=BORDER_COLOR,  # initial pending color (Neutral T30)
                text_color=TEXT_BRIGHT,
                font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold")
            )
            # Custom rounded corner simulation in CustomTkinter CTkLabel requires setting corner_radius
            dot.configure(corner_radius=13)
            dot.pack(side="left", padx=(10, 15))
            
            # Text label
            lbl = ctk.CTkLabel(
                step_frame,
                text=step_name,
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="normal"),
                text_color=TEXT_MUTED  # initial pending text color
            )
            lbl.pack(side="left")
            
            self.step_dots.append(dot)
            self.step_labels.append(lbl)
            
        self.update_step(1)
        
    def update_step(self, step_num: int):
        self.current_step = step_num
        for i in range(1, 5):
            dot = self.step_dots[i-1]
            lbl = self.step_labels[i-1]
            
            if i < step_num:
                # Complete: Success Green (Secondary)
                dot.configure(fg_color=SECONDARY)
                lbl.configure(text_color=SECONDARY)
            elif i == step_num:
                # Active: Primary Action Blue (Primary)
                dot.configure(fg_color=PRIMARY)
                lbl.configure(text_color=TEXT_BRIGHT)
            else:
                # Pending: Grey (Neutral T30 / Muted)
                dot.configure(fg_color=BORDER_COLOR)
                lbl.configure(text_color=TEXT_MUTED)
