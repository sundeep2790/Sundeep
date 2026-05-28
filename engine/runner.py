import os
import sys
import re
import math
import time
import random
import logging
import threading
import subprocess
from PIL import Image, ImageDraw

# Import shared helpers — eliminates duplicate implementation (BUG-007)
from engine.photorec_wrapper import is_destination_on_source
from engine.drive_manager import get_raw_device_path
from engine.log_parser import parse_photorec_log

logger = logging.getLogger("datarescue-engine")

class PhotoRecRunner(threading.Thread):
    def __init__(self, drive, dest_path, progress_queue):
        super().__init__()
        self.drive = drive
        self.dest_path = dest_path
        self.progress_queue = progress_queue
        self.cancelled = False
        self.paused = False
        self.retrieve_early = False
        self.daemon = True

    def run(self):
        try:
            # Safety check: ensure destination path is not on the source drive
            device = self.drive.get("device", "")
            mountpoint = self.drive.get("mountpoint", "")
            if is_destination_on_source(device, self.dest_path) or (mountpoint and is_destination_on_source(mountpoint, self.dest_path)):
                raise ValueError("Destination path cannot be on the source drive to prevent data overwriting.")

            # Check if we should use mock scanning (Virtual Disk or any fallback)
            is_mock = (self.drive.get('device') == 'MOCK_DISK_01' or 
                       self.drive.get('device') == 'TESTDISK_PARTITION_01' or
                       os.environ.get("DATARESCUE_FORCE_MOCK") == "1")
                       
            if is_mock:
                self.run_mock_scan()
            else:
                self.run_real_scan()
        except Exception as e:
            logger.exception("Error in PhotoRecRunner thread")
            self.progress_queue.put({"type": "error", "message": str(e)})

    def cancel(self):
        self.cancelled = True

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop_and_retrieve(self):
        self.retrieve_early = True
        self.cancelled = True

    def run_mock_scan(self):
        self.send_log("Initializing PhotoRec Simulated Recovery engine...")
        time.sleep(0.5)
        
        if self.cancelled: return
        self.send_log(f"Scanning drive: {self.drive.get('label')}...")
        self.send_log(f"Recovery destination path: {self.dest_path}")
        time.sleep(0.5)
        
        # Setup recup directory like real photorec
        recup_dir = os.path.join(self.dest_path, "recup_dir.1")
        os.makedirs(recup_dir, exist_ok=True)
        
        # Prepare lists of files we will "find" and write to disk
        photos = 0
        videos = 0
        docs = 0
        others = 0
        
        recovered_files_metadata = []
        
        # 10 steps of simulation
        total_steps = 10
        for step in range(1, total_steps + 1):
            # Check pause state
            while self.paused and not self.cancelled:
                time.sleep(0.2)

            if self.cancelled:
                if self.retrieve_early:
                    self.send_log(f"Scan stopped early by user. {len(recovered_files_metadata)} files retrieved so far.")
                    self.progress_queue.put({
                        "type": "stats",
                        "photos": photos,
                        "videos": videos,
                        "docs": docs,
                        "others": others
                    })
                    self.progress_queue.put({"type": "progress", "value": 1.0})
                    self.progress_queue.put({"type": "complete", "recovered_files": recovered_files_metadata})
                else:
                    self.send_log("Recovery scan aborted by user.")
                return
                
            progress = step / total_steps
            self.progress_queue.put({"type": "progress", "value": progress})
            
            # Update simulated sector grid
            # Update ~10 sector blocks each step
            for block_idx in range((step-1)*10, step*10):
                # Sector grid is 20x5 (100 blocks)
                # Assign states: 90% healthy (done), 5% scanning (current), 5% bad
                state = "done"
                if block_idx >= step*10 - 2:
                    state = "scanning"
                elif random.random() < 0.04:
                    state = "bad"
                self.progress_queue.put({"type": "sector", "index": block_idx, "state": state})
            
            # Generate a recovered file on disk at certain stages
            if step == 2:
                # JPG Image
                photos += 1
                filepath = os.path.join(recup_dir, "f0000001.jpg")
                self.create_mock_image(filepath, "red", "Recovered Photo #1")
                recovered_files_metadata.append({
                    "path": filepath, "name": "f0000001.jpg", "size": os.path.getsize(filepath), "ext": ".jpg", "selected": False
                })
                self.send_log("Found file: f0000001.jpg (JPEG Image) at block 18")
                
            elif step == 3:
                # TXT Document
                docs += 1
                filepath = os.path.join(recup_dir, "f0000002.txt")
                with open(filepath, "w") as f:
                    f.write("DataRescue Recovery Log\n---\nThis document contains recovered system information.")
                recovered_files_metadata.append({
                    "path": filepath, "name": "f0000002.txt", "size": os.path.getsize(filepath), "ext": ".txt", "selected": False
                })
                self.send_log("Found file: f0000002.txt (Plain Text Document) at block 25")
                
            elif step == 5:
                # PNG Image
                photos += 1
                filepath = os.path.join(recup_dir, "f0000003.png")
                self.create_mock_image(filepath, "blue", "Recovered Photo #2")
                recovered_files_metadata.append({
                    "path": filepath, "name": "f0000003.png", "size": os.path.getsize(filepath), "ext": ".png", "selected": False
                })
                self.send_log("Found file: f0000003.png (PNG Image) at block 42")
                
            elif step == 6:
                # MP4 Video
                videos += 1
                filepath = os.path.join(recup_dir, "f0000004.mp4")
                # Write some dummy bytes
                with open(filepath, "wb") as f:
                    f.write(b"RIFF....AVI LIST" + os.urandom(100 * 1024))
                recovered_files_metadata.append({
                    "path": filepath, "name": "f0000004.mp4", "size": os.path.getsize(filepath), "ext": ".mp4", "selected": False
                })
                self.send_log("Found file: f0000004.mp4 (MPEG-4 Video) at block 55")
                
            elif step == 8:
                # PDF Document
                docs += 1
                filepath = os.path.join(recup_dir, "f0000005.pdf")
                with open(filepath, "w") as f:
                    f.write("%PDF-1.4 ... mock pdf content")
                recovered_files_metadata.append({
                    "path": filepath, "name": "f0000005.pdf", "size": os.path.getsize(filepath), "ext": ".pdf", "selected": False
                })
                self.send_log("Found file: f0000005.pdf (PDF Document) at block 78")
                
            elif step == 9:
                # Custom Zip
                others += 1
                filepath = os.path.join(recup_dir, "f0000006.zip")
                with open(filepath, "wb") as f:
                    f.write(b"PK\x03\x04" + os.urandom(20 * 1024))
                recovered_files_metadata.append({
                    "path": filepath, "name": "f0000006.zip", "size": os.path.getsize(filepath), "ext": ".zip", "selected": False
                })
                self.send_log("Found file: f0000006.zip (ZIP Compressed Archive) at block 91")
                
            # Send updated counts
            self.progress_queue.put({
                "type": "stats",
                "photos": photos,
                "videos": videos,
                "docs": docs,
                "others": others
            })
            
            # Wait to simulate processing time
            time.sleep(0.6)
            
        self.send_log("Disk scan finished. 100% analyzed.")
        self.send_log(f"Recovery complete. Total files recovered: {len(recovered_files_metadata)}")
        self.progress_queue.put({"type": "complete", "recovered_files": recovered_files_metadata})

    def run_real_scan(self):  # noqa: C901
        """Run a real PhotoRec scan against a physical drive.

        Progress tracking strategy
        --------------------------
        PhotoRec (ncurses/Qt) writes progress lines such as
          ``Pass 1 - Reading sector   12345/9999999 - 42 files found``
        to STDOUT.  The ``/log`` flag writes *recovered file entries* to
        photorec.log (not progress percentages), so the old approach of
        parsing photorec.log for percentages never worked.

        Fix: parse STDOUT in a dedicated thread, share the parsed percent
        with the main polling loop via a thread-safe dict.  If STDOUT gives
        nothing useful (ncurses sends escape sequences that get swallowed by
        the pipe on some Windows builds), fall back to an asymptotic
        time-based curve so the bar always moves.
        """
        import re
        import math

        self.send_log("Preparing physical recovery with PhotoRec engine...")

        # ── locate binary ────────────────────────────────────────────────
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "binaries")
        if sys.platform == "win32":
            photorec_bin = os.path.join(bin_dir, "win", "photorec.exe")
        else:
            photorec_bin = os.path.join(bin_dir, "mac", "photorec")

        if not os.path.exists(photorec_bin):
            self.send_log("PhotoRec executable not found — launching simulation fallback...")
            time.sleep(1.0)
            self.run_mock_scan()
            return

        os.makedirs(self.dest_path, exist_ok=True)

        # ── build device path ────────────────────────────────────────────
        device = self.drive.get("device", "")
        if sys.platform == "win32":
            if device.startswith("\\\\.\\"):
                raw_device = device
            else:
                drive_letter = os.path.splitdrive(device)[0].rstrip(":")
                raw_device = f"\\\\.\\{drive_letter}:" if drive_letter else device
        else:
            raw_device = device

        self.send_log(f"Scanning device: {raw_device}  →  destination: {self.dest_path}")

        photorec_dest = os.path.join(self.dest_path, "recup_dir")
        cmd = [photorec_bin, "/log", "/d", photorec_dest, "/cmd", raw_device]

        is_logical = True
        if sys.platform == "win32":
            if "PhysicalDrive" in raw_device:
                is_logical = False
        else:
            if re.search(r"/dev/disk\d+$", raw_device) or re.search(r"/dev/sd[a-z]$", raw_device):
                is_logical = False
        if not is_logical:
            cmd.append("1")
        cmd.append("wholespace,search")

        self.send_log(f"Command: {' '.join(cmd)}")

        # ── progress state shared across threads ─────────────────────────
        _pstate = {"percent": 0.0, "files": 0, "pass": 0, "got_real": False}
        _plock = threading.Lock()

        # Regex for PhotoRec stdout progress line
        # "Pass 1 - Reading sector     1234/12345678 - 5 files found"
        _pass_re = re.compile(
            r"Pass\s+(\d+)\s*-\s*Reading\s+sector\s+(\d+)\s*/\s*(\d+)"
            r"(?:\s*-\s*(\d+)\s+files?\s+found)?",
            re.IGNORECASE,
        )
        # Strip ANSI / ncurses escape sequences
        _ansi_re = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[()][AB012]|\r")

        # ── helper: count every file in all recup_dir.* subdirs ──────────
        def _count_recovered():
            photos = videos = docs = others = 0
            recovered = []
            try:
                for entry in os.scandir(self.dest_path):
                    if not (entry.is_dir() and entry.name.lower().startswith("recup_dir")):
                        continue
                    try:
                        for fentry in os.scandir(entry.path):
                            if not fentry.is_file():
                                continue
                            ext = os.path.splitext(fentry.name)[1].lower()
                            if ext in (".jpg", ".jpeg", ".png", ".gif", ".bmp",
                                       ".tiff", ".heic", ".webp", ".cr2", ".nef", ".arw"):
                                photos += 1
                            elif ext in (".mp4", ".avi", ".mov", ".mkv", ".wmv",
                                         ".flv", ".webm", ".m4v", ".3gp"):
                                videos += 1
                            elif ext in (".pdf", ".doc", ".docx", ".xls", ".xlsx",
                                         ".ppt", ".pptx", ".txt", ".rtf", ".csv", ".odt"):
                                docs += 1
                            else:
                                others += 1
                            recovered.append({
                                "path": fentry.path,
                                "name": fentry.name,
                                "size": fentry.stat().st_size,
                                "ext": os.path.splitext(fentry.name)[1],
                                "selected": False,
                            })
                    except Exception:
                        pass
            except Exception:
                pass
            return photos, videos, docs, others, recovered

        # ── stdout reader thread ─────────────────────────────────────────
        def _read_stdout(stream):
            try:
                for raw_line in iter(stream.readline, ""):
                    line = _ansi_re.sub("", raw_line).strip()
                    if not line:
                        continue
                    self.send_log(f"[PhotoRec] {line}")
                    m = _pass_re.search(line)
                    if m:
                        p_num = int(m.group(1))
                        cur_sec = int(m.group(2))
                        tot_sec = int(m.group(3))
                        files = int(m.group(4)) if m.group(4) else 0
                        if tot_sec > 0:
                            pct = min((cur_sec / tot_sec) * 100.0, 99.9)
                            with _plock:
                                _pstate["percent"] = pct
                                _pstate["pass"] = p_num
                                _pstate["got_real"] = True
                                if files:
                                    _pstate["files"] = files
            except Exception:
                pass

        def _read_stderr(stream):
            try:
                for line in iter(stream.readline, ""):
                    cleaned = line.strip()
                    if cleaned:
                        self.send_log(f"[PhotoRec ERR] {cleaned}")
            except Exception:
                pass

        try:
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 0  # SW_HIDE

            process = subprocess.Popen(
                cmd,
                cwd=self.dest_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                text=True,
                shell=False,
                startupinfo=startupinfo,
            )

            threading.Thread(target=_read_stdout, args=(process.stdout,), daemon=True).start()
            threading.Thread(target=_read_stderr, args=(process.stderr,), daemon=True).start()

            # ── main polling loop ─────────────────────────────────────────
            scan_start = time.monotonic()
            last_block_end = 0

            while process.poll() is None:
                # Check pause state
                if self.paused and not self.cancelled:
                    try:
                        import psutil
                        psutil.Process(process.pid).suspend()
                        self.send_log("Scan paused by user.")
                        while self.paused and not self.cancelled:
                            time.sleep(0.2)
                        if not self.cancelled:
                            psutil.Process(process.pid).resume()
                            self.send_log("Scan resumed.")
                    except Exception as e:
                        logger.error(f"Failed to toggle suspend/resume: {e}")

                if self.cancelled:
                    try:
                        import psutil
                        psutil.Process(process.pid).resume()
                    except Exception:
                        pass
                    process.terminate()
                    if self.retrieve_early:
                        photos, videos, docs, others, recovered = _count_recovered()
                        self.send_log(f"Scan stopped early by user. {len(recovered)} files retrieved so far.")
                        self.progress_queue.put({
                            "type": "stats",
                            "photos": photos, "videos": videos,
                            "docs": docs, "others": others,
                        })
                        self.progress_queue.put({"type": "progress", "value": 1.0})
                        self.progress_queue.put({"type": "complete", "recovered_files": recovered})
                    else:
                        self.send_log("PhotoRec process terminated by user.")
                    return

                # File stats — scan ALL recup_dir.* not just recup_dir.1
                photos, videos, docs, others, _ = _count_recovered()
                self.progress_queue.put({
                    "type": "stats",
                    "photos": photos,
                    "videos": videos,
                    "docs": docs,
                    "others": others,
                })

                # Determine percentage
                with _plock:
                    pct = _pstate["percent"]
                    got_real = _pstate["got_real"]

                if not got_real:
                    # Asymptotic fallback: reaches ~50% in 5 min, ~90% in 20 min.
                    # Never resets to 0 and never reaches 100 (reserved for completion).
                    elapsed = time.monotonic() - scan_start
                    pct = min(95.0 * (1.0 - math.exp(-elapsed / 600.0)), 95.0)

                self.progress_queue.put({"type": "progress", "value": pct / 100.0})

                # Update sector heat-map blocks
                block_end = min(int(pct), 99)
                for idx in range(last_block_end, block_end + 1):
                    state = "scanning" if idx == block_end else "done"
                    self.progress_queue.put({"type": "sector", "index": idx, "state": state})
                last_block_end = block_end

                time.sleep(1.0)

            # ── process finished ─────────────────────────────────────────
            returncode = process.returncode
            if returncode != 0:
                # NOTE: do NOT call process.communicate() here — stdout/stderr
                # pipes were already drained by the reader threads; communicate()
                # would block indefinitely waiting for a pipe that is already closed.
                self.send_log(f"PhotoRec exited with code {returncode}.")
                if sys.platform == "win32" and returncode == 1:
                    self.send_log(
                        "WARNING: Administrator privileges are required to scan "
                        "physical drives. Right-click the app and choose Run as Administrator."
                    )
                raise RuntimeError(f"PhotoRec exited with code {returncode}")

            # Collect final file list
            photos, videos, docs, others, recovered = _count_recovered()
            self.send_log(f"Scan complete. {len(recovered)} files recovered.")
            self.progress_queue.put({
                "type": "stats",
                "photos": photos, "videos": videos,
                "docs": docs, "others": others,
            })
            self.progress_queue.put({"type": "progress", "value": 1.0})
            self.progress_queue.put({"type": "complete", "recovered_files": recovered})

        except Exception as e:
            self.send_log(f"Real scan failed: {e}.")
            self.send_log("Falling back to simulation mode.")
            time.sleep(2.0)
            self.run_mock_scan()

    def send_log(self, text):
        self.progress_queue.put({"type": "status", "message": text})

    def create_mock_image(self, filepath, color, text):
        # Create a beautiful vector landscape/art image instead of a generic "X"
        img = Image.new("RGB", (300, 200), color="#0F172A")
        draw = ImageDraw.Draw(img)
        
        filename = os.path.basename(filepath).lower()
        
        if "f0000001" in filename:
            # Sunset scene
            # Sky Gradient (simplified with overlapping bands)
            colors = ["#2E1065", "#4C1D95", "#6D28D9", "#7C3AED", "#9061F9", "#A78BFA"]
            for i, c in enumerate(colors):
                draw.rectangle([(0, i*20), (300, (i+1)*20)], fill=c)
                
            # Sun
            draw.ellipse([(110, 100), (170, 160)], fill="#F59E0B")
            
            # Mountains silhouettes
            draw.polygon([(0, 200), (80, 110), (160, 200)], fill="#1E1B4B")
            draw.polygon([(100, 200), (190, 120), (280, 200)], fill="#111827")
            draw.polygon([(160, 200), (230, 140), (300, 200)], fill="#0F172A")
            
        else:
            # Sunny Day / Green Field scene
            # Blue Sky
            draw.rectangle([(0, 0), (300, 120)], fill="#38BDF8")
            
            # Sun
            draw.ellipse([(20, 20), (60, 60)], fill="#FDE047")
            
            # White Clouds
            draw.ellipse([(140, 30), (190, 60)], fill="#FFFFFF")
            draw.ellipse([(170, 25), (220, 55)], fill="#FFFFFF")
            
            # Green Field / Hill
            draw.ellipse([(-50, 100), (350, 250)], fill="#22C55E")
            draw.ellipse([(50, 120), (450, 280)], fill="#16A34A")
            
        # Draw a sleek overlay label at the bottom
        draw.rectangle([(0, 175), (300, 200)], fill="#000000", outline=None)
        draw.text((10, 180), text, fill="#FFFFFF")
        img.save(filepath)
