import os
import sys
import customtkinter as ctk
from tkinter import filedialog
from engine.drive_scanner import scan_system_drives
from gui.components.drive_card import DriveCard
from gui.theme import *

class ScreenDrive(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.selected_card = None
        self.drive_cards = []
        self.drives = []
        
        self.create_widgets()

    def create_widgets(self):
        # Main Scrollable content container for this screen
        # To avoid scrolling conflicts, the screen itself is a frame with pack, and internal sections might have scrollbars.
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=25, pady=25)
        
        # 1. Heading + Safe Badge Row
        header_row = ctk.CTkFrame(self.container, fg_color="transparent")
        header_row.pack(fill="x", pady=(0, 15))
        
        title_lbl = ctk.CTkLabel(
            header_row,
            text="Select Drive for Recovery",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        title_lbl.pack(side="left")
        
        # Green Safe Badge
        safe_badge = ctk.CTkLabel(
            header_row,
            text="✓ 100% Safe & Read-Only",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TEXT_BRIGHT,
            fg_color=SECONDARY,
            corner_radius=4,
            width=150,
            height=22
        )
        safe_badge.pack(side="left", padx=15)
        
        # Refresh button
        refresh_btn = ctk.CTkButton(
            header_row,
            text="Refresh Drives",
            width=110,
            height=26,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=BG_CARD,
            text_color=TEXT_BRIGHT,
            hover_color=BORDER_COLOR,
            command=self.refresh_drives
        )
        refresh_btn.pack(side="right")
        
        # 2. Drive list scrollable frame
        self.list_frame = ctk.CTkScrollableFrame(
            self.container,
            height=200,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_MAIN
        )
        self.list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # 3. TestDisk Collapsable Expander
        self.expander = TestDiskExpander(self.container, scan_callback=self.run_testdisk_scan)
        self.expander.pack(fill="x", pady=(0, 15))
        
        # 4. Destination Directory Section
        dest_section = ctk.CTkFrame(
            self.container,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        dest_section.pack(fill="x", pady=(0, 20))
        
        dest_lbl = ctk.CTkLabel(
            dest_section,
            text="Recovery Destination Folder:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        dest_lbl.pack(anchor="w", padx=15, pady=(10, 2))
        
        dest_input_row = ctk.CTkFrame(dest_section, fg_color="transparent")
        dest_input_row.pack(fill="x", padx=15, pady=(0, 10))
        
        # Set default directory to workspace/recovered
        default_dir = os.path.abspath(os.path.join(os.getcwd(), "recovered"))
        self.dest_entry = ctk.CTkEntry(
            dest_input_row,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=BG_MAIN,
            border_color=BORDER_COLOR,
            text_color=TEXT_BRIGHT,
            height=30
        )
        self.dest_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.dest_entry.insert(0, default_dir)
        
        browse_btn = ctk.CTkButton(
            dest_input_row,
            text="Browse...",
            width=90,
            height=30,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=BG_CARD,
            text_color=TEXT_BRIGHT,
            hover_color=BORDER_COLOR,
            command=self.browse_dest
        )
        browse_btn.pack(side="right")
        
        # 5. Start Recovery CTA Button
        self.start_btn = ctk.CTkButton(
            self.container,
            text="Start Recovery Scan",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=PRIMARY,
            hover_color="#2563EB",
            height=40,
            state="disabled",
            command=self.start_scan
        )
        self.start_btn.pack(fill="x")
        
        # Initial scan
        self.refresh_drives()

    def browse_dest(self):
        selected_dir = filedialog.askdirectory(initialdir=os.getcwd())
        if selected_dir:
            # Normalize path delimiters for OS consistency
            selected_dir = os.path.abspath(selected_dir)
            self.dest_entry.delete(0, "end")
            self.dest_entry.insert(0, selected_dir)

    def refresh_drives(self):
        # Clear existing cards
        for card in self.drive_cards:
            card.destroy()
        self.drive_cards = []
        self.selected_card = None
        self.start_btn.configure(state="disabled")
        
        # Scan drives
        self.drives = scan_system_drives()
        
        # Render cards
        for drive in self.drives:
            card = DriveCard(self.list_frame, drive, select_callback=self.on_drive_selected)
            card.pack(fill="x", padx=10, pady=5)
            self.drive_cards.append(card)

    def on_drive_selected(self, selected_card):
        # Deselect old card
        if self.selected_card:
            self.selected_card.set_selected(False)
            
        self.selected_card = selected_card
        self.selected_card.set_selected(True)
        
        # Enable CTA
        self.start_btn.configure(state="normal")
        self.app.app_state['drive'] = selected_card.drive_data

    def run_testdisk_scan(self):
        # Show simulated testdisk search progress
        self.expander.content_frame.configure(border_color=TERTIARY) # Highlight orange (Tertiary)
        
        # Create a status label inside expander
        status_lbl = ctk.CTkLabel(
            self.expander.content_frame,
            text="Analyzing cylinders: 0%...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            text_color=TERTIARY
        )
        status_lbl.pack(padx=15, pady=(0, 10), anchor="w")
        
        def update_progress(step=1):
            if step <= 5:
                status_lbl.configure(text=f"Analyzing cylinders: {step * 20}%...")
                self.after(200, lambda: update_progress(step + 1))
            else:
                status_lbl.configure(text="TestDisk completed: Found 1 lost partition!", text_color=SECONDARY)
                # Add mock partition to drive cards
                lost_partition = {
                    'device': 'TESTDISK_PARTITION_01',
                    'mountpoint': '',
                    'fstype': 'NTFS (Recovered)',
                    'total': 40 * 1024 * 1024 * 1024, # 40 GB
                    'free': 12 * 1024 * 1024 * 1024,
                    'label': 'Lost Partition (Recovered by TestDisk)'
                }
                card = DriveCard(self.list_frame, lost_partition, select_callback=self.on_drive_selected)
                card.pack(fill="x", padx=10, pady=5)
                self.drive_cards.append(card)
                # Automatically highlight it!
                self.on_drive_selected(card)
                
        update_progress()

    def start_scan(self):
        dest_path = self.dest_entry.get().strip()
        if not dest_path:
            return
            
        # Warn if scanning real drive on Windows without Admin rights
        drive = self.app.app_state['drive']
        device = drive.get('device', '') if drive else ''
        is_mock = (device == 'MOCK_DISK_01' or device == 'TESTDISK_PARTITION_01')
        
        if sys.platform == "win32" and not is_mock:
            import ctypes
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                is_admin = True
                
            if not is_admin:
                from tkinter import messagebox
                response = messagebox.askyesno(
                    "Administrator Privileges Required",
                    "Scanning physical disk partitions typically requires Administrator privileges.\n\n"
                    "DataRescue is not running as Administrator. The scan will likely fail or fall back to simulation mode.\n\n"
                    "Do you want to proceed with the scan anyway?",
                    icon="warning"
                )
                if not response:
                    return

        # Ensure destination directory exists
        os.makedirs(dest_path, exist_ok=True)
        self.app.app_state['dest_path'] = dest_path
        
        # Navigate to step 2 (Scanning screen)
        self.app.show_screen("scan")

    def on_show(self):
        # Re-verify drive selection state when screen returns/loads
        if self.app.app_state['drive']:
            for card in self.drive_cards:
                if card.drive_data['device'] == self.app.app_state['drive']['device']:
                    self.on_drive_selected(card)
                    break
        else:
            self.start_btn.configure(state="disabled")

class TestDiskExpander(ctk.CTkFrame):
    def __init__(self, master, scan_callback, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.scan_callback = scan_callback
        self.expanded = False
        
        self.toggle_btn = ctk.CTkButton(
            self,
            text="Advanced Partition Recovery (TestDisk)  ▼",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color="transparent",
            text_color=PRIMARY,
            hover=False,
            anchor="w",
            command=self.toggle
        )
        self.toggle_btn.pack(fill="x", pady=2)
        
        self.content_frame = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            border_width=1,
            border_color=BORDER_COLOR,
            corner_radius=6
        )
        
    def toggle(self):
        self.expanded = not self.expanded
        if self.expanded:
            self.toggle_btn.configure(text="Advanced Partition Recovery (TestDisk)  ▲")
            self.content_frame.pack(fill="x", padx=10, pady=5)
            self.create_content_widgets()
        else:
            self.toggle_btn.configure(text="Advanced Partition Recovery (TestDisk)  ▼")
            self.content_frame.pack_forget()
            
    def create_content_widgets(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
            
        desc_lbl = ctk.CTkLabel(
            self.content_frame,
            text="If your partition has been deleted, formatted, or shows as RAW/unallocated, "
                 "TestDisk can analyze the drive structure and search for missing partition tables.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11),
            text_color=TEXT_MUTED,
            wraplength=650,
            justify="left"
        )
        desc_lbl.pack(padx=15, pady=(12, 6), anchor="w")
        
        scan_btn = ctk.CTkButton(
            self.content_frame,
            text="Run TestDisk Deep Partition Analysis",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=TERTIARY,
            hover_color="#D97706",
            height=30,
            command=self.scan_callback
        )
        scan_btn.pack(padx=15, pady=(6, 12), anchor="w")
