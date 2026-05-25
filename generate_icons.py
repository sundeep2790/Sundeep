import os
from PIL import Image, ImageDraw

def create_icon():
    assets_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    
    # Create a 256x256 image with a blue background and a white cross/rescue symbol
    img = Image.new("RGBA", (256, 256), color=(41, 128, 185, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw simple rescue ring or cross symbol
    # Rescue ring
    draw.ellipse([20, 20, 236, 236], outline=(255, 255, 255, 255), width=24)
    # Cross in the middle
    draw.rectangle([112, 60, 144, 196], fill=(255, 255, 255, 255))
    draw.rectangle([60, 112, 196, 144], fill=(255, 255, 255, 255))
    
    ico_path = os.path.join(assets_dir, "icon.ico")
    icns_path = os.path.join(assets_dir, "icon.icns")
    
    # Save as ICO (with multiple sizes)
    img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print(f"Generated ICO icon: {ico_path}")
    
    # Save as ICNS
    # Pillow supports saving to ICNS format
    try:
        img.save(icns_path, format="ICNS")
        print(f"Generated ICNS icon: {icns_path}")
    except Exception as e:
        print(f"Failed to save ICNS directly: {e}. Writing a placeholder.")
        # Fallback to writing a small file or copying
        with open(icns_path, "wb") as f:
            f.write(b"")

if __name__ == "__main__":
    create_icon()
