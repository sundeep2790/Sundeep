import customtkinter as ctk
import webbrowser
import logging
import re
from PIL import Image
from gui.theme import *

logger = logging.getLogger("datarescue-gui")

class CreditModal(ctk.CTkToplevel):
    def __init__(self, master, client, email, on_success_callback=None, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Buy Credits & Redeem Licence")
        self.geometry("680x560")
        self.resizable(False, False)
        
        self.client = client
        self.email = email or "user@example.com"
        self.on_success_callback = on_success_callback
        
        # Bring to front and grab focus
        self.lift()
        self.grab_set()
        self.focus_force()
        
        # Design system colors
        self.configure(fg_color=BG_MAIN)
        
        self.create_widgets()

    def create_widgets(self):
        # 1. Title / Header
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        title_lbl = ctk.CTkLabel(
            header_frame,
            text="Upgrade & Purchase Credits",
            font=ctk.CTkFont(family=FONT_FAMILY, size=20, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        title_lbl.pack(anchor="w")
        
        sub_lbl = ctk.CTkLabel(
            header_frame,
            text=f"Selected email: {self.email} (Credits will link to this account)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            text_color=TEXT_MUTED
        )
        sub_lbl.pack(anchor="w", pady=(2, 0))
        
        # 2. Credits Grid (4 Packs)
        packs_frame = ctk.CTkFrame(self, fg_color="transparent")
        packs_frame.pack(fill="x", padx=20, pady=10)
        
        packs = [
            {"id": "starter", "name": "Starter", "desc": "5 Credits", "price": "$4.99", "badge": "Great for single files"},
            {"id": "standard", "name": "Standard", "desc": "10 Credits", "price": "$9.99", "badge": "Popular"},
            {"id": "plus", "name": "Plus", "desc": "25 Credits", "price": "$19.99", "badge": "Best value"},
            {"id": "unlimited", "name": "Unlimited", "desc": "Lifetime Access", "price": "$34.99", "badge": "Unlimited recoveries"}
        ]
        
        for i, pack in enumerate(packs):
            pack_card = ctk.CTkFrame(
                packs_frame, 
                corner_radius=8, 
                border_width=1,
                border_color=BORDER_COLOR,
                fg_color=BG_CARD,
                width=140,
                height=180
            )
            pack_card.grid(row=0, column=i, padx=8, pady=5, sticky="nsew")
            pack_card.grid_propagate(False)
            
            # Badge or spacer
            badge_lbl = ctk.CTkLabel(
                pack_card,
                text=pack["badge"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=9, weight="normal"),
                text_color=PRIMARY,
                fg_color=BG_MAIN,
                corner_radius=4,
                height=16
            )
            badge_lbl.pack(pady=(10, 5), padx=5)
            
            name_lbl = ctk.CTkLabel(
                pack_card,
                text=pack["name"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=14, weight="bold"),
                text_color=TEXT_BRIGHT
            )
            name_lbl.pack(pady=2)
            
            desc_lbl = ctk.CTkLabel(
                pack_card,
                text=pack["desc"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=12),
                text_color=TEXT_MUTED
            )
            desc_lbl.pack(pady=1)
            
            price_lbl = ctk.CTkLabel(
                pack_card,
                text=pack["price"],
                font=ctk.CTkFont(family=FONT_FAMILY, size=18, weight="bold"),
                text_color=TEXT_BRIGHT
            )
            price_lbl.pack(pady=6)
            
            buy_btn = ctk.CTkButton(
                pack_card,
                text="Buy Pack",
                font=ctk.CTkFont(family=FONT_FAMILY, size=11, weight="bold"),
                fg_color=PRIMARY,
                hover_color="#2563EB",
                height=26,
                corner_radius=6,
                command=lambda p=pack["id"]: self.on_buy_pack(p)
            )
            buy_btn.pack(side="bottom", pady=10)
            
        # Configure columns equally
        for col in range(4):
            packs_frame.grid_columnconfigure(col, weight=1)

        # 3. Verification & Coupon entry
        action_frame = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=1,
            border_color=BORDER_COLOR,
            fg_color=BG_CARD
        )
        action_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        # Left Side: Confirm Payment Session ID
        verify_section = ctk.CTkFrame(action_frame, fg_color="transparent")
        verify_section.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        verify_title = ctk.CTkLabel(
            verify_section,
            text="Verify Stripe Purchase",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        verify_title.pack(anchor="w", pady=(0, 5))
        
        self.session_entry = ctk.CTkEntry(
            verify_section,
            placeholder_text="Enter Stripe Session ID (e.g. cs_test_...)",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            height=30
        )
        self.session_entry.pack(fill="x", pady=5)
        
        # Inform user about test mode session IDs
        mock_tip_lbl = ctk.CTkLabel(
            verify_section,
            text="Mock: mock_starter, mock_standard, mock_plus, mock_unlimited",
            font=ctk.CTkFont(family=FONT_FAMILY, size=9),
            text_color=TEXT_MUTED,
            anchor="w"
        )
        mock_tip_lbl.pack(fill="x", pady=(0, 5))
        
        verify_btn = ctk.CTkButton(
            verify_section,
            text="Verify & Activate",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=SECONDARY,
            hover_color="#0D9488",
            height=30,
            command=self.on_verify_session
        )
        verify_btn.pack(fill="x", pady=5)
        
        # Vertical divider line
        divider = ctk.CTkFrame(action_frame, width=1, fg_color=BORDER_COLOR)
        divider.pack(side="left", fill="y", padx=10, pady=15)
        
        # Right Side: Redeem AppSumo Code
        sumo_section = ctk.CTkFrame(action_frame, fg_color="transparent")
        sumo_section.pack(side="left", fill="both", expand=True, padx=15, pady=15)
        
        sumo_title = ctk.CTkLabel(
            sumo_section,
            text="Redeem AppSumo Code",
            font=ctk.CTkFont(family=FONT_FAMILY, size=13, weight="bold"),
            text_color=TEXT_BRIGHT
        )
        sumo_title.pack(anchor="w", pady=(0, 5))
        
        self.code_entry = ctk.CTkEntry(
            sumo_section,
            placeholder_text="DRESC-XXXXXX",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12),
            height=30
        )
        self.code_entry.pack(fill="x", pady=5)
        
        # Link for AppSumo
        sumo_link_lbl = ctk.CTkLabel(
            sumo_section,
            text="Get AppSumo lifetime code here ↗",
            font=ctk.CTkFont(family=FONT_FAMILY, size=10, underline=True),
            text_color=PRIMARY,
            cursor="hand2"
        )
        sumo_link_lbl.pack(anchor="w", pady=(0, 5))
        sumo_link_lbl.bind("<Button-1>", lambda e: webbrowser.open("https://appsumo.com"))
        
        redeem_btn = ctk.CTkButton(
            sumo_section,
            text="Redeem Code",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="bold"),
            fg_color=TERTIARY,
            hover_color="#D97706",
            height=30,
            command=self.on_redeem_code
        )
        redeem_btn.pack(fill="x", pady=5)
        
        # 4. Status Message Label at bottom
        self.status_lbl = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight="normal"),
            text_color="#DC2626"
        )
        self.status_lbl.pack(pady=(0, 10))

    def on_buy_pack(self, pack_id):
        checkout_url = self.client.build_checkout_url(pack_id, self.email)
        logger.info(f"Opening checkout url for pack '{pack_id}': {checkout_url}")
        webbrowser.open(checkout_url)
        self.show_status(f"Checkout page opened in browser. Verify Stripe Session ID below.", color="#2563EB")

    def on_verify_session(self):
        session_id = self.session_entry.get().strip()
        if not session_id:
            self.show_status("Please enter a Stripe Session ID.", color="#DC2626")
            return
            
        try:
            res = self.client.confirm_payment(session_id)
            balance = res.get("balance", 0)
            is_lifetime = res.get("is_lifetime", False)
            msg = f"Success! New balance: {balance} credits."
            if is_lifetime:
                msg = "Success! Lifetime license activated."
            self.show_status(msg, color=SECONDARY)
            
            if self.on_success_callback:
                self.on_success_callback(balance, is_lifetime)
                
            # Close dialog after 1.5s success view
            self.after(1500, self.destroy)
        except Exception as e:
            self.show_status(f"Verification failed: {e}", color="#DC2626")

    def on_redeem_code(self):
        code = self.code_entry.get().strip()
        if not code:
            self.show_status("Please enter an AppSumo code.", color="#DC2626")
            return
            
        if not re.match(r"^DRESC-[A-Z0-9]{6}$", code.upper()):
            self.show_status("Format must match DRESC-XXXXXX (e.g. DRESC-A1B2C3).", color="#DC2626")
            return
            
        try:
            res = self.client.redeem_appsumo(code)
            balance = res.get("balance", 0)
            is_lifetime = res.get("is_lifetime", False)
            self.show_status("AppSumo Code Redeemed! Lifetime access granted.", color=SECONDARY)
            
            if self.on_success_callback:
                self.on_success_callback(balance, is_lifetime)
                
            # Close dialog after 1.5s success view
            self.after(1500, self.destroy)
        except Exception as e:
            self.show_status(f"Redemption failed: {e}", color="#DC2626")

    def show_status(self, text, color="#DC2626"):
        self.status_lbl.configure(text=text, text_color=color)
