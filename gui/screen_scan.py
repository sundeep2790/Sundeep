import queue
import customtkinter as ctk
import logging
from engine.runner import PhotoRecRunner
from gui.theme import *

logger = logging.getLogger("datarescue-gui")

class ScreenScan(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.runner = None
        self.progress_queue = None
        self.sector_blocks = []
        
        self.create_widgets()

    def create_widgets(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=25, pady=25)
        
        # 1. Title
        self.title_lbl = ctk.CTkLabel(
            self.container,
            text="Scanning Drive for Deleted Files...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        self.title_lbl.pack(anchor="w", pady=(0, 10))
        
        # 2. Progress Bar and Percentage Label
        progress_row = ctk.CTkFrame(self.container, fg_color="transparent")
        progress_row.pack(fill="x", pady=(0, 15))
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_row, 
            height=12,
            progress_color=PRIMARY,
            fg_color=BORDER_COLOR
        )
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=(0, 15))
        self.progress_bar.set(0.0)
        
        self.pct_lbl = ctk.CTkLabel(
            progress_row,
            text="0%",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_BRIGHT,
            width=50
        )
        self.pct_lbl.pack(side="right")
        
        # 3. Middle Area: Left (Stats + Sector Grid) | Right (Log Text Area)
        mid_row = ctk.CTkFrame(self.container, fg_color="transparent")
        mid_row.pack(fill="both", expand=True, pady=(0, 15))
        
        # Left container
        left_col = ctk.CTkFrame(mid_row, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # File Stats 2x2 Grid
        stats_frame = ctk.CTkFrame(
            left_col, 
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD,
            height=100
        )
        stats_frame.pack(fill="x", pady=(0, 10))
        
        # Define stats boxes
        self.photo_val = self.create_stat_box(stats_frame, "Photos", 0, 0)
        self.video_val = self.create_stat_box(stats_frame, "Videos", 0, 1)
        self.doc_val = self.create_stat_box(stats_frame, "Documents", 1, 0)
        self.other_val = self.create_stat_box(stats_frame, "Others", 1, 1)
        
        # Configure columns/rows for stats
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(1, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)
        stats_frame.grid_rowconfigure(1, weight=1)
        
        # Sector Grid Panel (20x5 blocks)
        grid_panel = ctk.CTkFrame(
            left_col,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        grid_panel.pack(fill="both", expand=True)
        
        grid_title = ctk.CTkLabel(
            grid_panel,
            text="Simulated Disk Sectors Map",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        grid_title.pack(anchor="w", padx=12, pady=(10, 5))
        
        # Container for the grid blocks
        blocks_container = ctk.CTkFrame(grid_panel, fg_color="transparent")
        blocks_container.pack(padx=10, pady=(0, 10), fill="both", expand=True)
        
        # Create 100 block labels inside a 20x5 structure
        self.sector_blocks = []
        for r in range(5):
            blocks_container.grid_rowconfigure(r, weight=1)
            for c in range(20):
                if r == 0:
                    blocks_container.grid_columnconfigure(c, weight=1)
                
                # Small square for block
                block = ctk.CTkLabel(
                    blocks_container, 
                    text="", 
                    width=10, 
                    height=10, 
                    fg_color=BORDER_COLOR,
                    corner_radius=2
                )
                block.grid(row=r, column=c, padx=2, pady=2, sticky="nsew")
                self.sector_blocks.append(block)
                
        # Right container (Log Console)
        right_col = ctk.CTkFrame(
            mid_row,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        right_col.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        log_title = ctk.CTkLabel(
            right_col,
            text="Console Scan Logs",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        log_title.pack(anchor="w", padx=15, pady=(10, 5))
        
        self.log_txt = ctk.CTkTextbox(
            right_col,
            font=ctk.CTkFont(family=FONT_TECH, size=11),
            fg_color="transparent",
            text_color=TEXT_BRIGHT,
            activate_scrollbars=True
        )
        self.log_txt.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.log_txt.configure(state="disabled")
        
        # 4. Bottom Control Row
        ctrl_row = ctk.CTkFrame(self.container, fg_color="transparent")
        ctrl_row.pack(fill="x")
        
        self.cancel_btn = ctk.CTkButton(
            ctrl_row,
            text="Cancel Scan",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color="#EF4444",
            hover_color="#DC2626",
            height=36,
            command=self.cancel_scan
        )
        self.cancel_btn.pack(side="left")
        
        self.next_btn = ctk.CTkButton(
            ctrl_row,
            text="Next: View Recovered Files",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=SECONDARY,
            hover_color="#0D9488",
            height=36,
            state="disabled",
            command=self.go_to_results
        )
        self.next_btn.pack(side="right")

    def create_stat_box(self, parent, label_text, row, col):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=row, column=col, padx=10, pady=5, sticky="nsew")
        
        title = ctk.CTkLabel(
            box,
            text=label_text,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED
        )
        title.pack(anchor="w")
        
        value = ctk.CTkLabel(
            box,
            text="0 files",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        value.pack(anchor="w")
        return value

    def append_log(self, message):
        self.log_txt.configure(state="normal")
        self.log_txt.insert("end", f"[{self.get_time_str()}] {message}\n")
        self.log_txt.see("end")
        self.log_txt.configure(state="disabled")

    def get_time_str(self):
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")

    def reset_ui(self):
        self.progress_bar.set(0.0)
        self.pct_lbl.configure(text="0%")
        self.photo_val.configure(text="0 files")
        self.video_val.configure(text="0 files")
        self.doc_val.configure(text="0 files")
        self.other_val.configure(text="0 files")
        
        # Clear log text
        self.log_txt.configure(state="normal")
        self.log_txt.delete("1.0", "end")
        self.log_txt.configure(state="disabled")
        
        # Reset sectors grid
        for block in self.sector_blocks:
            block.configure(fg_color=BORDER_COLOR)
            
        self.cancel_btn.configure(state="normal")
        self.next_btn.configure(state="disabled")

    def on_show(self):
        self.reset_ui()
        
        # Make sure drive is selected
        drive = self.app.app_state['drive']
        dest_path = self.app.app_state['dest_path']
        if not drive or not dest_path:
            self.append_log("Error: Drive or destination path was not selected properly.")
            self.cancel_btn.configure(state="normal")
            return
            
        # Start PhotoRec Background Thread
        self.progress_queue = queue.Queue()
        self.runner = PhotoRecRunner(drive, dest_path, self.progress_queue)
        self.app.app_state['scan_thread'] = self.runner
        self.runner.start()
        
        # Start queue processing
        self.after(50, self.poll_queue)

    def poll_queue(self):
        if not self.runner or not self.runner.is_alive():
            # If the thread stopped and we didn't receive final messages, handle it
            if self.progress_queue.empty():
                return
                
        # Drain queue
        try:
            while True:
                msg = self.progress_queue.get_nowait()
                msg_type = msg.get("type")
                
                if msg_type == "status":
                    self.append_log(msg.get("message"))
                    
                elif msg_type == "progress":
                    val = msg.get("value", 0.0)
                    self.progress_bar.set(val)
                    self.pct_lbl.configure(text=f"{int(val * 100)}%")
                    
                elif msg_type == "stats":
                    self.photo_val.configure(text=f"{msg.get('photos', 0)} files")
                    self.video_val.configure(text=f"{msg.get('videos', 0)} files")
                    self.doc_val.configure(text=f"{msg.get('docs', 0)} files")
                    self.other_val.configure(text=f"{msg.get('others', 0)} files")
                    
                elif msg_type == "sector":
                    idx = msg.get("index", 0)
                    state = msg.get("state", "pending")
                    if 0 <= idx < len(self.sector_blocks):
                        block = self.sector_blocks[idx]
                        if state == "done":
                            block.configure(fg_color=SECONDARY)  # Emerald Green
                        elif state == "scanning":
                            block.configure(fg_color=TERTIARY)   # Amber Gold
                        elif state == "bad":
                            block.configure(fg_color="#EF4444")  # Modern Red
                            
                elif msg_type == "complete":
                    self.app.app_state['file_tree'] = msg.get("recovered_files", [])
                    self.next_btn.configure(state="normal")
                    self.cancel_btn.configure(state="disabled")
                    self.append_log("Scan finished. Ready to browse results.")
                    
                elif msg_type == "error":
                    self.append_log(f"Error occurred: {msg.get('message')}")
                    self.cancel_btn.configure(state="normal")
                    
                self.progress_queue.task_done()
        except queue.Empty:
            pass
            
        # Re-schedule queue checking
        self.after(50, self.poll_queue)

    def cancel_scan(self):
        if self.runner:
            self.runner.cancel()
            self.append_log("Aborting recovery processes...")
            
        # Clear states
        self.app.app_state['scan_thread'] = None
        self.app.app_state['file_tree'] = None
        
        # Navigate back to drive selection
        self.app.show_screen("drive")

    def go_to_results(self):
        # Navigate to step 3 (results browsing)
        self.app.show_screen("results")
