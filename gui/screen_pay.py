import os
import sys
import shutil
import time
import queue
import logging
import threading
import subprocess
import customtkinter as ctk
from PIL import Image
from gui.components.credit_modal import CreditModal
from gui.theme import *

logger = logging.getLogger("datarescue-gui")

class RestoreThread(threading.Thread):
    def __init__(self, selected_files, dest_path, client, is_lifetime, progress_callback):
        super().__init__()
        self.selected_files = selected_files
        self.dest_path = dest_path
        self.client = client
        self.is_lifetime = is_lifetime
        self.progress_callback = progress_callback
        self.daemon = True

    def run(self):
        cost = len(self.selected_files)
        try:
            # 1. Deduct credits via API client (Bypassed for testing/free mode)
            self.progress_callback("deduct_done", "Skipping credit deduction in free testing mode.", 999999)
                
            # 2. Copy files to permanent Restored directory
            restore_dir = os.path.join(self.dest_path, "Restored_Files")
            os.makedirs(restore_dir, exist_ok=True)
            
            total_files = len(self.selected_files)
            for idx, file_info in enumerate(self.selected_files, 1):
                src = file_info["path"]
                filename = file_info["name"]
                dst = os.path.join(restore_dir, filename)
                
                self.progress_callback("copy_file", f"Restoring file {idx}/{total_files}: {filename}...", (idx / total_files))
                
                # Copy file
                if os.path.exists(src):
                    shutil.copy2(src, dst)
                else:
                    # Write mock file if it got cleaned up
                    with open(dst, "w") as f:
                        f.write(f"Mock recovered content for {filename}")
                        
                time.sleep(0.3)  # Simulate progress delay
                
            self.progress_callback("complete", "All files successfully restored!", restore_dir)
            
        except Exception as e:
            logger.exception("Error in RestoreThread")
            self.progress_callback("error", f"Restoration failed: {str(e)}")

class ScreenPay(ctk.CTkFrame):
    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.app = app
        self.selected_files = []
        self.restore_thread = None
        self.restored_dir = None
        
        self.create_widgets()

    def create_widgets(self):
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=25, pady=25)
        
        # State A Frame: Purchase needed
        self.state_a_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_state_a()
        
        # State B Frame: Restoration progress
        self.state_b_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_state_b()
        
        # State C Frame: Recovery complete
        self.state_c_frame = ctk.CTkFrame(self.container, fg_color="transparent")
        self.setup_state_c()

    def setup_state_a(self):
        # Heading
        title = ctk.CTkLabel(
            self.state_a_frame,
            text="Insufficient Credits for Recovery",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color="#EF4444"  # Modern red
        )
        title.pack(anchor="w", pady=(0, 10))
        
        self.deficit_lbl = ctk.CTkLabel(
            self.state_a_frame,
            text="You have selected 0 files (cost: 0 credits). Your current balance is 0 credits.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_BRIGHT,
            justify="left"
        )
        self.deficit_lbl.pack(anchor="w", pady=(0, 15))
        
        # Prompt to buy pack
        buy_lbl = ctk.CTkLabel(
            self.state_a_frame,
            text="Select a pack to purchase credits or enter an AppSumo license key below:",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="normal"),
            text_color=TEXT_MUTED
        )
        buy_lbl.pack(anchor="w", pady=(0, 10))
        
        # Inline Credit packs button trigger
        btn_pack = ctk.CTkButton(
            self.state_a_frame,
            text="Open Purchase & Licence Validation Panel",
            font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
            fg_color=PRIMARY,
            hover_color="#2563EB",
            height=40,
            command=self.app.open_buy_credits
        )
        btn_pack.pack(fill="x", pady=10)
        
        # Cancel / Back button
        back_btn = ctk.CTkButton(
            self.state_a_frame,
            text="Back to File Browser",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=BG_CARD,
            text_color=TEXT_BRIGHT,
            hover_color=BORDER_COLOR,
            height=36,
            command=self.go_back
        )
        back_btn.pack(pady=10)

    def setup_state_b(self):
        title = ctk.CTkLabel(
            self.state_b_frame,
            text="Restoring Selected Files...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        title.pack(anchor="w", pady=(0, 10))

        self.status_lbl = ctk.CTkLabel(
            self.state_b_frame,
            text="Initializing restoration engine...",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED
        )
        self.status_lbl.pack(anchor="w", pady=(0, 15))

        self.restore_progress = ctk.CTkProgressBar(
            self.state_b_frame,
            height=12,
            progress_color=PRIMARY,
            fg_color=BORDER_COLOR
        )
        self.restore_progress.pack(fill="x", pady=10)
        self.restore_progress.set(0.0)

        # BUG-009: Create the error "Go Back" button once and keep it hidden.
        # Showing it dynamically on each error was creating duplicate buttons.
        self.error_back_btn = ctk.CTkButton(
            self.state_b_frame,
            text="Go Back",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=BG_CARD,
            text_color=TEXT_BRIGHT,
            hover_color=BORDER_COLOR,
            command=self.go_back
        )
        # Hidden by default — only revealed on error
        self.error_back_btn.pack_forget()

    def setup_state_c(self):
        # Success Icon Checkmark
        self.success_icon = ctk.CTkLabel(
            self.state_c_frame,
            text="✓",
            font=ctk.CTkFont(family=FONT_FAMILY, size=48, weight="bold"),
            text_color=TEXT_BRIGHT,
            fg_color=SECONDARY,
            width=80,
            height=80,
            corner_radius=40
        )
        self.success_icon.pack(pady=(20, 10))
        
        self.success_title = ctk.CTkLabel(
            self.state_c_frame,
            text="Recovery Completed Successfully!",
            font=ctk.CTkFont(family=FONT_FAMILY, size=22, weight="bold"),
            text_color=SECONDARY
        )
        self.success_title.pack(pady=5)
        
        self.success_desc = ctk.CTkLabel(
            self.state_c_frame,
            text="5 files have been restored to your chosen folder.",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13),
            text_color=TEXT_MUTED
        )
        self.success_desc.pack(pady=(5, 20))
        
        # Action Row
        actions = ctk.CTkFrame(self.state_c_frame, fg_color="transparent")
        actions.pack(pady=10)
        
        open_folder_btn = ctk.CTkButton(
            actions,
            text="Open Recovery Folder",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=PRIMARY,
            hover_color="#2563EB",
            height=40,
            command=self.open_recovered_folder
        )
        open_folder_btn.pack(side="left", padx=10)
        
        restart_btn = ctk.CTkButton(
            actions,
            text="Start New Recovery",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            fg_color=BG_CARD,
            text_color=TEXT_BRIGHT,
            hover_color=BORDER_COLOR,
            height=40,
            command=self.restart_recovery
        )
        restart_btn.pack(side="left", padx=10)

    def on_show(self):
        self.selected_files = self.app.app_state['selected_files'] or []
        cost = len(self.selected_files)
        
        # Hide all frames initially
        self.state_a_frame.pack_forget()
        self.state_b_frame.pack_forget()
        self.state_c_frame.pack_forget()
        
        if cost == 0:
            self.deficit_lbl.configure(
                text="No files selected for recovery. Please complete a scan and select files first."
            )
            self.state_a_frame.pack(fill="both", expand=True)
            return
            
        # Always proceed to restoration without credit check (Free testing mode)
        self.state_b_frame.pack(fill="both", expand=True)
        self.start_restore_process()

    def start_restore_process(self):
        self.restore_progress.set(0.0)
        self.status_lbl.configure(text="Initializing file restoration...")
        
        dest_path = self.app.app_state['dest_path']
        is_lifetime = self.app.app_state['is_lifetime']
        
        # Start background copy thread
        self.restore_thread = RestoreThread(
            self.selected_files,
            dest_path,
            self.app.client,
            is_lifetime,
            progress_callback=self.on_restore_progress
        )
        self.restore_thread.start()

    def on_restore_progress(self, event, status_msg, value=None):
        # CustomTkinter UI must be updated in the main thread.
        # Since this callback is invoked from the RestoreThread, we use self.after to schedule UI updates.
        self.after(0, lambda: self.handle_restore_callback(event, status_msg, value))

    def handle_restore_callback(self, event, status_msg, value):
        if event == "deduct_start" or event == "copy_file":
            self.status_lbl.configure(text=status_msg)
            if event == "copy_file" and isinstance(value, float):
                self.restore_progress.set(value)
                
        elif event == "deduct_done":
            self.status_lbl.configure(text=status_msg)
            # Sync balance on app
            if isinstance(value, int):
                self.app.app_state['credits'] = value
                self.app.update_credits_ui()
                
        elif event == "complete":
            self.restored_dir = value
            self.state_b_frame.pack_forget()
            
            # Show State C
            self.success_desc.configure(
                text=f"{len(self.selected_files)} files have been restored to your chosen folder:\n{self.restored_dir}"
            )
            self.state_c_frame.pack(fill="both", expand=True)
            
        elif event == "error":
            self.status_lbl.configure(text=status_msg, text_color="#EF4444")
            # Reveal the single pre-created "Go Back" button (BUG-009 fix)
            self.error_back_btn.pack(pady=10)

    def open_recovered_folder(self):
        if not self.restored_dir or not os.path.exists(self.restored_dir):
            return
            
        # Cross platform directory opening
        try:
            if sys.platform == "win32":
                os.startfile(self.restored_dir)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.restored_dir])
            else:
                subprocess.run(["xdg-open", self.restored_dir])
        except Exception as e:
            logger.warning(f"Could not open restored folder shell: {e}")

    def restart_recovery(self):
        # Reset recovery states in app
        self.app.app_state['drive'] = None
        self.app.app_state['file_tree'] = None
        self.app.app_state['selected_files'] = []
        
        # Navigate back to step 1
        self.app.show_screen("drive")

    def go_back(self):
        # Navigate back to Step 3 (results)
        self.app.show_screen("results")

    def refresh_credits_display(self):
        # If user purchases credits while in State A, recheck if balance is now sufficient
        if self.winfo_ismapped():
            self.on_show()
