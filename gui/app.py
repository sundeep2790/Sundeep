import os
import re
import sys
import threading
import customtkinter as ctk
import webbrowser
import logging
from config import load_config, save_config, set_email, set_credits, set_lifetime, get_credits
from api.client import DataRescueClient
from gui.components.step_indicator import StepIndicator
from gui.components.credit_modal import CreditModal
from gui.theme import *

logger = logging.getLogger("datarescue-gui")

class CTkApp(ctk.CTk):
    def __init__(self, is_online=False):
        super().__init__()
        
        # 1. Page Configuration
        self.title("DataRescue v1.0")
        self.geometry("960x640")
        self.minsize(800, 560)
        self.resizable(True, True)
        
        # Appearance setting
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        
        self.is_online = is_online
        
        # 2. Local State initialization
        self.config_data = load_config()
        email = self.config_data.get("email") or ""
        device_token = self.config_data.get("device_token")
        
        # Create API Client (fallback URL is local backend, else client handles mock)
        api_url = os.environ.get("DATARESCUE_API_URL", "http://localhost:8000")
        self.client = DataRescueClient(api_base_url=api_url, email=email, device_token=device_token)
        
        # If is_online is False or API unreachable, the client transitions to mock mode.
        if not self.is_online:
            self.client.is_mock_mode = True
            
        # IMP-003: Load balance immediately from local cache (no network block on startup)
        credits_balance = get_credits()
        is_lifetime = self.config_data.get("is_lifetime", False)
        
        # State dict matching design instructions
        self.app_state = {
            'drive': None,
            'dest_path': None,
            'file_tree': None,
            'selected_files': [],
            'credits': credits_balance,
            'email': email if email else None,
            'scan_thread': None,
            'client': self.client,
            'is_lifetime': is_lifetime
        }
        
        self.create_layout()
        self.init_screens()
        self.show_screen("drive")

    def create_layout(self):
        # Configure columns/rows for the window
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # Content area expands
        
        # Left Sidebar: 220px, dark navy
        self.sidebar = ctk.CTkFrame(
            self, 
            width=220, 
            corner_radius=0, 
            fg_color=BG_SIDEBAR
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Logo inside sidebar
        logo_lbl = ctk.CTkLabel(
            self.sidebar,
            text="DataRescue v1.0",
            font=ctk.CTkFont(family="Inter", size=20, weight="bold"),
            text_color="#FFFFFF"
        )
        logo_lbl.pack(pady=(25, 10), padx=20, anchor="w")
        
        # Email Input Section in sidebar
        email_lbl = ctk.CTkLabel(
            self.sidebar,
            text="Account Email:",
            font=ctk.CTkFont(family="Inter", size=11, weight="normal"),
            text_color="#94A3B8"
        )
        email_lbl.pack(padx=20, anchor="w", pady=(10, 2))
        
        self.email_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Enter email address",
            height=28,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            fg_color=BG_CARD,
            border_color=BORDER_COLOR,
            text_color=TEXT_BRIGHT
        )
        self.email_entry.pack(fill="x", padx=20, pady=(0, 10))
        if self.app_state['email']:
            self.email_entry.insert(0, self.app_state['email'])
        self.email_entry.bind("<FocusOut>", self.on_email_changed)
        self.email_entry.bind("<Return>", self.on_email_changed)
        
        # Stepper component
        self.step_indicator = StepIndicator(self.sidebar)
        self.step_indicator.pack(fill="x", padx=10, pady=15)
        
        # Divider line
        divider = ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER_COLOR)
        divider.pack(fill="x", padx=15, pady=5)
        
        # Credit Balance section
        self.credits_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.credits_frame.pack(fill="x", padx=20, pady=10)
        
        self.balance_lbl = ctk.CTkLabel(
            self.credits_frame,
            text="Credits: " + str(self.app_state['credits']),
            font=ctk.CTkFont(family="Inter", size=13, weight="bold"),
            text_color="#FFFFFF"
        )
        self.balance_lbl.pack(anchor="w")
        self.update_credits_ui()
        
        self.buy_btn = ctk.CTkButton(
            self.credits_frame,
            text="Buy / Redeem Credits",
            height=26,
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
            fg_color=PRIMARY,
            hover_color="#2563EB",
            corner_radius=6,
            command=self.open_buy_credits
        )
        self.buy_btn.pack(fill="x", pady=(8, 0))
        
        # Help link at the bottom
        self.help_lbl = ctk.CTkLabel(
            self.sidebar,
            text="Help & Documentation ↗",
            font=ctk.CTkFont(family=FONT_FAMILY, size=11, underline=True),
            text_color=TEXT_MUTED,
            cursor="hand2"
        )
        self.help_lbl.pack(side="bottom", pady=20, padx=20, anchor="w")
        self.help_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://github.com"))
        
        # Content Area: 740px right of sidebar
        self.content_area = ctk.CTkFrame(
            self, 
            corner_radius=0, 
            fg_color=BG_MAIN
        )
        self.content_area.grid(row=0, column=1, sticky="nsew")
        
        # Configure content area grids
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

    def init_screens(self):
        # We import screens inside to prevent circular import if screens import CTkApp
        from gui.screen_drive import ScreenDrive
        from gui.screen_scan import ScreenScan
        from gui.screen_results import ScreenResults
        from gui.screen_pay import ScreenPay
        
        self.screens = {
            "drive": ScreenDrive(self.content_area, self),
            "scan": ScreenScan(self.content_area, self),
            "results": ScreenResults(self.content_area, self),
            "pay": ScreenPay(self.content_area, self)
        }
        
        # Grid all screens on top of each other
        for name, screen in self.screens.items():
            screen.grid(row=0, column=0, sticky="nsew")

    def show_screen(self, name):
        if name not in self.screens:
            logger.error(f"Screen '{name}' not found!")
            return
            
        # Update sidebar step indicator based on screen name
        step_map = {
            "drive": 1,
            "scan": 2,
            "results": 3,
            "pay": 4
        }
        self.step_indicator.update_step(step_map[name])
        
        # Show screen
        screen = self.screens[name]
        screen.tkraise()
        
        # Call refresh method on screen if exists
        if hasattr(screen, "on_show"):
            screen.on_show()

    def on_email_changed(self, event=None):
        new_email = self.email_entry.get().strip()
        if not new_email:
            self.app_state['email'] = None
            set_email("")
            self.client.email = ""
            return

        # IMP-007: Basic email format validation before saving
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", new_email):
            logger.warning(f"Invalid email format entered: {new_email!r} — not saved.")
            return

        self.app_state['email'] = new_email
        set_email(new_email)
        self.client.email = new_email

        # Recheck balance for new email
        self.refresh_credits()

    def refresh_credits(self):
        try:
            balance = self.client.get_balance()
            is_lifetime = self.client.validate_licence().get("is_lifetime", False)
            
            self.app_state['credits'] = balance
            self.app_state['is_lifetime'] = is_lifetime
            
            set_credits(balance)
            set_lifetime(is_lifetime)
            
            self.update_credits_ui()
            
            # If current screen is results or pay, refresh their UI to reflect new credit balance
            for screen in self.screens.values():
                if hasattr(screen, "refresh_credits_display"):
                    screen.refresh_credits_display()
        except Exception as e:
            logger.warning(f"Could not refresh credits from API: {e}")

    def update_credits_ui(self):
        if self.app_state['is_lifetime']:
            self.balance_lbl.configure(text="Credits: Lifetime Pro 💎", text_color=SECONDARY)
        else:
            self.balance_lbl.configure(text="Credits: " + str(self.app_state['credits']), text_color=TEXT_BRIGHT)

    def open_buy_credits(self):
        # Open Credit modal dialog
        email = self.app_state['email'] or "user@example.com"
        modal = CreditModal(self, self.client, email, on_success_callback=self.on_credits_purchased)

    def on_credits_purchased(self, new_balance, is_lifetime):
        self.app_state['credits'] = new_balance
        self.app_state['is_lifetime'] = is_lifetime
        
        set_credits(new_balance)
        set_lifetime(is_lifetime)
        
        self.update_credits_ui()
        
        # Trigger updates on screens
        for screen in self.screens.values():
            if hasattr(screen, "refresh_credits_display"):
                screen.refresh_credits_display()

    def _background_sync_balance(self):
        """Fetch fresh balance from backend in a daemon thread — never blocks the UI."""
        def worker():
            try:
                balance = self.client.get_balance()
                is_lifetime = self.client.validate_licence().get("is_lifetime", False)
                set_credits(balance)
                set_lifetime(is_lifetime)
                self.after(0, lambda: self._apply_synced_balance(balance, is_lifetime))
            except Exception:
                pass  # Keep cached values — handled gracefully
        threading.Thread(target=worker, daemon=True).start()

    def _apply_synced_balance(self, balance, is_lifetime):
        self.app_state['credits'] = balance
        self.app_state['is_lifetime'] = is_lifetime
        self.update_credits_ui()
        for screen in self.screens.values():
            if hasattr(screen, "refresh_credits_display"):
                screen.refresh_credits_display()

    def run(self):
        # Kick off a background balance sync 200ms after launch (IMP-003)
        self.after(200, self._background_sync_balance)
        self.mainloop()
