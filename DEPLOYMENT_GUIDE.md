# DataRescue Deployment & Distribution Guide

This document provides step-by-step instructions for deploying the DataRescue FastAPI backend to production (Railway.app), packaging standalone installers/executables for Windows and macOS, setting up codesigning and notarization, and executing marketing launches on Product Hunt and AppSumo.

---

## 1. Backend Deployment (Railway.app)

The DataRescue backend manages licenses, checks credit balances, processes Stripe purchase webhooks, and redeems AppSumo promotional codes.

### Prerequisites
- A [Railway.app](https://railway.app) account.
- The Railway CLI installed locally (optional, but recommended).
- A PostgreSQL database instance (Railway provides this as a service).
- A Stripe Developer Account.

### Step-by-Step Deployment
1. **Prepare the Repository**:
   Ensure the backend code contains the `backend/Procfile` and `backend/railway.toml`.
2. **Initialize Railway Project**:
   ```bash
   railway login
   railway init
   ```
3. **Provision PostgreSQL**:
   Add a PostgreSQL database service in your Railway project dashboard. Railway automatically provisions the database and sets the connection string environment variables.
4. **Configure Environment Variables**:
   In the Railway dashboard under your FastAPI service settings, add the following variables:
   - `DATABASE_URL`: `postgresql+asyncpg://...` (populated automatically by Railway's PostgreSQL binding).
   - `STRIPE_SECRET_KEY`: Your live or test secret key (`sk_live_...` or `sk_test_...`).
   - `STRIPE_WEBHOOK_SECRET`: The webhook signing secret from your Stripe dashboard (`whsec_...`).
   - `STRIPE_SUCCESS_URL`: Redirect URL on successful purchase (e.g., `https://datarescue.app/success?session_id={CHECKOUT_SESSION_ID}`).
   - `STRIPE_CANCEL_URL`: Redirect URL on cancellation (e.g., `https://datarescue.app/pricing`).
   - `PORT`: `8000`
5. **Deploy the Code**:
   Trigger deployment via the dashboard (connected to GitHub) or use:
   ```bash
   railway up
   ```
6. **Set up Stripe Webhooks**:
   - Go to Stripe Dashboard -> Developers -> Webhooks.
   - Add an endpoint pointing to `https://your-railway-app-url.up.railway.app/api/webhooks/stripe`.
   - Select the `checkout.session.completed` event.
   - Copy the Signing Secret and set it as `STRIPE_WEBHOOK_SECRET` in Railway.

---

## 2. Windows Standalone Executable Packaging

Windows Standalone executable packaging uses `PyInstaller` and the custom spec file.

### Prerequisites
- Windows 10 or 11 (x64).
- Python 3.11 installed.
- Install dependencies:
  ```cmd
  pip install -r requirements.txt
  ```

### Packaging Steps
1. **Ensure Binaries are Downloaded**:
   Execute the download script to retrieve PhotoRec and TestDisk executables and DLLs:
   ```cmd
   python download_binaries.py
   ```
2. **Generate Icon**:
   Run the icon generator script to build `assets/icon.ico`:
   ```cmd
   python generate_icons.py
   ```
3. **Run PyInstaller Build**:
   Build the single-file executable using the Windows spec configuration:
   ```cmd
   pyinstaller --clean --noconfirm build/datarescue_win.spec
   ```
4. **Locate Output**:
   The packaged executable `DataRescue.exe` will be located in the `dist/` folder.
5. **Sign Executable (Optional but Recommended)**:
   To avoid Windows SmartScreen warnings, sign the executable using a certificate:
   ```cmd
   signtool sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a dist/DataRescue.exe
   ```

---

## 3. macOS App Bundling, Signing & Notarization

On macOS, stand-alone apps must be signed and notarized to prevent Gatekeeper warnings.

### Prerequisites
- macOS machine running Ventura or newer.
- Xcode Command Line Tools installed.
- Apple Developer Account with a Developer ID Application Certificate.
- An App Store Connect API Key or App-Specific Password.

### Step-by-Step Bundling & Signing
1. **Download macOS Engine Binaries**:
   Ensure macOS PhotoRec/TestDisk binaries are in `binaries/mac/` (run `python download_binaries.py`).
2. **Generate macOS Icon**:
   Ensure `assets/icon.icns` exists (run `python generate_icons.py`).
3. **Build the App Bundle**:
   Run PyInstaller using the macOS spec configuration:
   ```bash
   pyinstaller --clean --noconfirm build/datarescue_mac.spec
   ```
   This produces `dist/DataRescue.app` (.app bundle).
4. **Codesign the App Bundle**:
   Sign the dynamic libraries, helper binaries, and the main app bundle using your Certificate and the `build/entitlements.plist`:
   ```bash
   # Sign the internal PhotoRec and TestDisk binaries first
   codesign --force --options runtime --entitlements build/entitlements.plist --sign "Developer ID Application: Your Name (TeamID)" dist/DataRescue.app/Contents/Resources/binaries/mac/photorec
   codesign --force --options runtime --entitlements build/entitlements.plist --sign "Developer ID Application: Your Name (TeamID)" dist/DataRescue.app/Contents/Resources/binaries/mac/testdisk
   
   # Sign all internal C extensions/so files
   find dist/DataRescue.app/Contents/MacOS -name "*.so" -exec codesign --force --options runtime --sign "Developer ID Application: Your Name (TeamID)" {} \;
   
   # Sign the app bundle itself
   codesign --force --options runtime --entitlements build/entitlements.plist --sign "Developer ID Application: Your Name (TeamID)" dist/DataRescue.app
   ```
5. **Notarize the App**:
   Zip the signed app bundle and submit it to Apple for notarization:
   ```bash
   ditto -c -k --keepParent dist/DataRescue.app dist/DataRescue.zip
   
   xcrun notarytool submit dist/DataRescue.zip --apple-id "your-apple-id@email.com" --password "your-app-specific-password" --team-id "YOUR_TEAM_ID" --wait
   ```
6. **Staple Notarization Ticket**:
   Once approved, staple the notarization ticket to the app bundle:
   ```bash
   xcrun stapler staple dist/DataRescue.app
   ```
7. **Verify Gatekeeper Status**:
   ```bash
   spctl --assess -vv dist/DataRescue.app
   ```

---

## 4. Marketing Launch & Checklists

### Product Hunt Launch Checklist
- [ ] **Launch Media**:
  - [ ] App Logo: High-res square image (GIF/PNG).
  - [ ] Promo Video: 1-minute video highlighting partition scanning and file recovery flow.
  - [ ] Screenshots: At least 3 high-res screenshots displaying dark/light GUI mode, sector grids, and preview grids.
- [ ] **Taglines & Copy**:
  - [ ] Product Name: DataRescue
  - [ ] Tagline: "Secure, local, credit-based file recovery wrapper for PhotoRec."
  - [ ] Description: Pitch focusing on privacy (runs completely local) and fair usage (only pay for what you recover).
- [ ] **Promo Deals**:
  - [ ] PH Launch Discount (e.g., 20% off all credit packs for launch week).
- [ ] **Launch Timing**:
  - [ ] Set launch schedule for 12:01 AM PST to maximize exposure time.

### AppSumo Launch Checklist
- [ ] **Product Setup**:
  - [ ] Define the Lifetime Deal (LTD) structure (e.g., $49 lifetime access with 500 recovery credits).
  - [ ] Create redemption portal linking AppSumo codes to backend (`/api/licence/appsumo`).
- [ ] **Copy & Guidelines**:
  - [ ] Write detailed redemption instructions.
  - [ ] Highlight that the recovery engine runs entirely offline for ultimate security.
- [ ] **Customer Support Plan**:
  - [ ] Set up support email ticket system.
  - [ ] Prepare FAQ docs resolving "How do I grant Full Disk Access on Mac?" and "How is my configuration secured?"
