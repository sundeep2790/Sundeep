import sys
import psutil
import logging

logger = logging.getLogger("datarescue-engine")

def scan_system_drives():
    drives = []
    
    # 1. Add Virtual Mock Disk for easy testing
    drives.append({
        'device': 'MOCK_DISK_01',
        'mountpoint': 'Virtual:\\',
        'fstype': 'NTFS (Mock)',
        'total': 16 * 1024 * 1024 * 1024,  # 16 GB
        'free': 5.4 * 1024 * 1024 * 1024,  # 5.4 GB
        'label': 'Virtual Recovery Disk (Simulated)'
    })
    
    # 2. Add physical/logical partitions using psutil
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            # Skip CD-ROMs/DVDs or invalid devices
            if 'cdrom' in part.opts or not part.device:
                continue
            
            # Format friendly labels
            label = f"Local Disk ({part.device})"
            if sys.platform == "win32":
                label = f"Local Disk ({part.mountpoint.rstrip(chr(92))})" # rstrip backslash
            
            # Retrieve usage info safely
            total_bytes = 0
            free_bytes = 0
            try:
                usage = psutil.disk_usage(part.mountpoint)
                total_bytes = usage.total
                free_bytes = usage.free
            except Exception as e:
                # Permission errors or unmounted drives
                logger.debug(f"Could not read disk usage for {part.mountpoint}: {e}")
                
            # If filesystem is empty, guess RAW or generic
            fstype = part.fstype if part.fstype else "RAW"
            
            drives.append({
                'device': part.device,
                'mountpoint': part.mountpoint,
                'fstype': fstype,
                'total': total_bytes,
                'free': free_bytes,
                'label': label
            })
    except Exception as e:
        logger.warning(f"Error scanning system partitions: {e}")
        
    return drives
