#!/usr/bin/env python3
"""
CI Bot - Automated Android ROM Build Script with Telegram Notifications
Clean version with banner generation
"""

import os
import sys
import subprocess
import time
import re
import requests
import signal
import hashlib
from pathlib import Path
from threading import Thread
from io import BytesIO
from html import escape as html_escape

# Try to import PIL for banner generation
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Warning: Pillow not installed. Banner generation disabled.", file=sys.stderr)
    print("   Install with: sudo apt install python3-pil", file=sys.stderr)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Telegram Configuration
CONFIG_CHATID = "-1003684590213"
CONFIG_BOT_TOKEN = "8245386388:AAEMYSiG0fcTwXWSOgysg2dAgIk3uBueD4I"

# Build Configuration
DEVICE = "lunaa"
VARIANT = "userdebug"
ROM_TYPE = "axion-pico"  # For Axion: "axion-pico", "axion-core", "axion-vanilla"

# ROM Display Name (for banner)
ROM_DISPLAY_NAME = "AxionOS 2.3"  # Leave empty to auto-detect

# Banner Configuration
BANNER_COLOR_SCHEME = "axion"  # "axion", "crdroid", "lineage", "arrow", "aosp"

# ============================================================================
# GLOBALS
# ============================================================================

ROOT_DIR = os.getcwd()
ROM_NAME = os.path.basename(ROOT_DIR)
BUILD_LOG = os.path.join(ROOT_DIR, "build.log")
OUT_DIR = os.path.join(ROOT_DIR, f"out/target/product/{DEVICE}")
ANDROID_VERSION = ""
GITHUB_ORG_AVATAR = ""
BUILD_MESSAGE_ID = None
USE_BANNER = False
BUILD_PROCESS = None
LAST_PROGRESS = ""

TELEGRAM_URL = f"https://api.telegram.org/bot{CONFIG_BOT_TOKEN}"

# ============================================================================
# BANNER GENERATOR - TAMINARU FONT ONLY
# ============================================================================

class BannerGenerator:
    """Banner generator using ONLY Taminaru_Regular.otf"""

    def __init__(self, width=1200, height=630):
        self.width = width
        self.height = height

    def fetch_avatar(self, avatar_url):
        """Fetch avatar from GitHub"""
        try:
            response = requests.get(avatar_url, timeout=10)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))
        except:
            pass
        return None

    def create_circular_avatar(self, avatar, size=200):
        """Create circular avatar - OLD VERSION (NOT CROPPED)"""
        # Convert to RGBA
        if avatar.mode != 'RGBA':
            avatar = avatar.convert('RGBA')

        # Remove white backgrounds
        data = list(avatar.getdata())
        new_data = []
        for item in data:
            r, g, b = item[0], item[1], item[2]
            if r > 240 and g > 240 and b > 240:
                new_data.append((r, g, b, 0))
            else:
                new_data.append(item)
        avatar.putdata(new_data)

        # Simple 15% padding for all logos
        padding = int(size * 0.15)
        inner_size = size - (padding * 2)

        # Resize maintaining aspect ratio
        avatar.thumbnail((inner_size, inner_size), Image.Resampling.LANCZOS)

        # White circular background
        background = Image.new('RGBA', (size, size), (255, 255, 255, 255))

        # Center logo
        x_offset = (size - avatar.width) // 2
        y_offset = (size - avatar.height) // 2
        background.paste(avatar, (x_offset, y_offset), avatar)

        # Circular mask
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size, size), fill=255)

        # Apply mask
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(background, (0, 0))
        output.putalpha(mask)

        # Create glow effect
        glow_size = size + 40
        glow = Image.new('RGBA', (glow_size, glow_size), (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow)

        # Draw multiple circles for glow
        for i in range(20, 0, -2):
            alpha = int(255 * (i / 20) * 0.3)
            glow_draw.ellipse(
                (20-i, 20-i, glow_size-20+i, glow_size-20+i),
                fill=(255, 255, 255, alpha)
            )

        # Paste circular avatar on glow
        glow.paste(output, (20, 20), output)
        return glow

    def get_taminaru_font(self, size, bold=False):
        """Get ONLY Taminaru_Regular.otf font"""
        TAMINARU_FONT = "/home/some8b/.local/share/fonts/t/Taminaru_Regular.otf"

        if os.path.exists(TAMINARU_FONT):
            try:
                return ImageFont.truetype(TAMINARU_FONT, size)
            except Exception as e:
                print(f"❌ Error loading Taminaru font: {e}")
                print(f"   File exists: {os.path.exists(TAMINARU_FONT)}")
                print(f"   File size: {os.path.getsize(TAMINARU_FONT)} bytes")
                raise

        print(f"❌ Taminaru font not found: {TAMINARU_FONT}")
        raise FileNotFoundError(f"Taminaru font not found: {TAMINARU_FONT}")

    def generate(self, title, avatar_url, device='', version=''):
        """Generate banner with Taminaru font only"""
        text_primary = (255, 255, 255, 255)
        text_secondary = (200, 210, 230, 255)

        # Colors
        color_scheme = BANNER_COLOR_SCHEME.lower() if BANNER_COLOR_SCHEME else "default"

        if color_scheme == "axion":
            colors = [(60, 60, 60), (100, 180, 255), (180, 180, 180)]
        elif color_scheme == "crdroid":
            colors = [(26, 35, 126), (74, 20, 140), (103, 58, 183)]
        else:
            colors = [(100, 200, 255), (150, 100, 255), (200, 150, 100)]

        accent = colors[0]

        raw_avatar = self.fetch_avatar(avatar_url)

        darkened = [tuple(max(0, int(c * 0.15)) for c in color) for color in colors]
        lightened = [tuple(min(255, int(c * 0.45)) for c in color) for color in colors]

        image = Image.new('RGB', (self.width, self.height))
        for y in range(self.height):
            progress = y / self.height
            if progress < 0.5:
                local_blend = progress * 2
                color = tuple(int(darkened[0][i] * (1 - local_blend) + lightened[0 if len(darkened) == 1 else 1][i] * local_blend) for i in range(3))
            else:
                local_blend = (progress - 0.5) * 2
                start_color = lightened[0 if len(lightened) == 1 else 1]
                end_color = lightened[1 if len(lightened) < 3 else 2]
                color = tuple(int(start_color[i] * (1 - local_blend) + end_color[i] * local_blend) for i in range(3))
            for x in range(self.width):
                image.putpixel((x, y), color)

        image = image.convert('RGBA')

        card_margin = 60
        card_layer = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        card_draw = ImageDraw.Draw(card_layer)
        card_draw.rounded_rectangle(
            (card_margin, card_margin, self.width - card_margin, self.height - card_margin),
            radius=30, fill=(255, 255, 255, 25), outline=(255, 255, 255, 60), width=2
        )
        image = Image.alpha_composite(image, card_layer.filter(ImageFilter.GaussianBlur(1)))

        logo_size = 200
        if raw_avatar:
            circular = self.create_circular_avatar(raw_avatar, logo_size)
            logo_x, logo_y = 120, (self.height - circular.height) // 2

            glow_layer = Image.new('RGBA', image.size, (0, 0, 0, 0))
            glow_center = (logo_x + circular.width // 2, logo_y + circular.height // 2)
            ImageDraw.Draw(glow_layer).ellipse(
                (glow_center[0] - logo_size, glow_center[1] - logo_size,
                 glow_center[0] + logo_size, glow_center[1] + logo_size),
                fill=(accent[0], accent[1], accent[2], 80)
            )
            image = Image.alpha_composite(image, glow_layer.filter(ImageFilter.GaussianBlur(40)))
            image.paste(circular, (logo_x, logo_y), circular)

        draw = ImageDraw.Draw(image)
        text_start_x, title_y = 400, self.height // 2 - 60

        # TAMINARU FONT ONLY
        title_font = self.get_taminaru_font(23)  # Large for title
        info_font = self.get_taminaru_font(20)   # Smaller for info

        title_text = title.title()
        max_width = self.width - text_start_x - 50
        while True:
            bbox = draw.textbbox((0, 0), title_text, font=title_font)
            if bbox[2] - bbox[0] <= max_width or len(title_text) <= 4:
                break
            title_text = title_text[:-4] + "..."

        draw.text((text_start_x, title_y), title_text, fill=text_primary, font=title_font)

        info_parts = []
        if device:
            info_parts.append(f"Device: {device}")
        if version:
            info_parts.append(f"Android {version}")
        info_text = " | ".join(info_parts)

        if info_text:
            draw.text((text_start_x, title_y + 105), info_text, fill=text_secondary, font=info_font)

        return image

    def save(self, image, output_path):
        """Save banner"""
        image.save(output_path, 'PNG', quality=95, optimize=True)
        return output_path

def generate_build_banner():
    """Generate build banner with Taminaru font"""
    output_file = os.path.join(ROOT_DIR, "build_banner.png")

    if not PIL_AVAILABLE:
        print("❌ Pillow not installed. Banner disabled.")
        return None

    try:
        print("📸 Generating banner...")
        generator = BannerGenerator()

        display_name = ROM_DISPLAY_NAME if ROM_DISPLAY_NAME else ROM_NAME

        image = generator.generate(
            title=display_name,
            avatar_url=GITHUB_ORG_AVATAR if GITHUB_ORG_AVATAR else 'https://avatars.githubusercontent.com/u/0?v=4',
            device=DEVICE,
            version=ANDROID_VERSION
        )

        generator.save(image, output_file)
        print("✅ Banner generated!")
        return output_file
    except Exception as e:
        print(f"❌ Error generating banner: {e}")
        return None

# ============================================================================
# TELEGRAM FUNCTIONS
# ============================================================================

def telegram_request(endpoint, data=None, files=None, timeout=30):
    """Send request to Telegram"""
    url = f"{TELEGRAM_URL}/{endpoint}"
    try:
        if files:
            response = requests.post(url, data=data, files=files, timeout=timeout)
        else:
            response = requests.post(url, json=data, timeout=timeout)
        result = response.json()
        return result if result.get('ok') else None
    except:
        return None

def send_message(text):
    """Send text message"""
    data = {
        'chat_id': CONFIG_CHATID,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    result = telegram_request('sendMessage', data=data)
    return result['result']['message_id'] if result else None

def send_photo(photo_path, caption):
    """Send photo with caption"""
    with open(photo_path, 'rb') as photo:
        files = {'photo': photo}
        data = {
            'chat_id': CONFIG_CHATID,
            'caption': caption,
            'parse_mode': 'HTML'
        }
        result = telegram_request('sendPhoto', data=data, files=files)
        return result['result']['message_id'] if result else None

def send_file(file_path):
    """Send file"""
    if not os.path.exists(file_path):
        return None
    with open(file_path, 'rb') as file:
        files = {'document': file}
        data = {'chat_id': CONFIG_CHATID}
        result = telegram_request('sendDocument', data=data, files=files, timeout=120)
        return result['result']['message_id'] if result else None

def edit_message(message_id, text):
    """Edit text message"""
    data = {
        'chat_id': CONFIG_CHATID,
        'message_id': message_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    return telegram_request('editMessageText', data=data)

def edit_photo_caption(message_id, caption):
    """Edit photo caption"""
    data = {
        'chat_id': CONFIG_CHATID,
        'message_id': message_id,
        'caption': caption,
        'parse_mode': 'HTML'
    }
    return telegram_request('editMessageCaption', data=data)

# ============================================================================
# BUILD FUNCTIONS
# ============================================================================

def get_build_progress():
    """Extract progress from build.log"""
    if not os.path.exists(BUILD_LOG):
        return "Initializing..."

    try:
        with open(BUILD_LOG, 'r') as f:
            lines = f.readlines()[-200:]

        # Check for packaging stage
        for line in reversed(lines[:100]):
            if any(x in line for x in ['Package Complete:', 'Writing full OTA', 'Generating OTA']):
                return "📦 Packing final ROM..."
            if 'add_img_to_target_files.py' in line and 'done' in line:
                return "📦 Packing final ROM..."
            if 'Compressing' in line and '.new.dat' in line:
                return "📦 Packing final ROM..."

        # Find progress percentage
        for line in reversed(lines):
            match = re.search(r'\[\s*(\d+)%\s+(\d+)/(\d+)\]', line) or \
                    re.search(r'(\d+)%\s+(\d+)/(\d+)', line)
            if match:
                return f"{match.group(1)}% ({match.group(2)}/{match.group(3)})"

        # Check if build is active
        if any(x in ''.join(lines[-10:]).lower() for x in ['ninja', 'soong', 'build']):
            return "Building..."

        return "Initializing the build system..."
    except:
        return "Initializing..."

def tail_build_log():
    """Print build log to console"""
    last_pos = 0
    while BUILD_PROCESS and BUILD_PROCESS.poll() is None:
        if os.path.exists(BUILD_LOG):
            try:
                with open(BUILD_LOG, 'r') as f:
                    f.seek(last_pos)
                    for line in f:
                        print(line.rstrip())
                    last_pos = f.tell()
            except:
                pass
        time.sleep(0.5)

def monitor_progress():
    """Update Telegram with progress"""
    global LAST_PROGRESS

    while BUILD_PROCESS and BUILD_PROCESS.poll() is None:
        current_progress = get_build_progress()

        if current_progress != LAST_PROGRESS:
            print(f"\n🔨 Progress: {current_progress}\n", file=sys.stderr)

            # Prepare caption based on banner usage
            if USE_BANNER:
                caption = f"""<b>🔨 Building {ROM_NAME}</b>

<b>Device:</b> {DEVICE} | <b>Android:</b> {ANDROID_VERSION}
<b>Type:</b> {'Official' if 'OFFICIAL' in os.environ else 'Unofficial'}

<b>⏳ Progress:</b> {current_progress}"""

                edit_photo_caption(BUILD_MESSAGE_ID, caption)
            else:
                text = f"""🟡 | <i>Compiling ROM...</i>

<b>• ROM:</b> <code>{ROM_NAME}</code>
<b>• DEVICE:</b> <code>{DEVICE}</code>
<b>• ANDROID VERSION:</b> <code>{ANDROID_VERSION}</code>
<b>• TYPE:</b> <code>{'Official' if 'OFFICIAL' in os.environ else 'Unofficial'}</code>
<b>• PROGRESS:</b> <code>{current_progress}</code>"""

                edit_message(BUILD_MESSAGE_ID, text)

            LAST_PROGRESS = current_progress

        time.sleep(3)

def find_rom_zip():
    """Find main ROM zip file"""
    patterns = ['axion-*.zip', 'lineage-*.zip', 'crdroid-*.zip',
                'voltage-*.zip', 'arrow-*.zip', 'evolution-*.zip', '*.zip']

    for pattern in patterns:
        files = [f for f in Path(OUT_DIR).glob(pattern)
                if 'ota' not in f.name.lower() and 'img' not in f.name.lower()
                and f.stat().st_size > 500 * 1024 * 1024]
        if files:
            return str(max(files, key=lambda f: f.stat().st_mtime))
    return None

def get_rom_info():
    """Get ROM name and avatar from GitHub"""
    global ROM_NAME, GITHUB_ORG_AVATAR

    # Use custom display name if set
    if ROM_DISPLAY_NAME:
        ROM_NAME = ROM_DISPLAY_NAME

    manifest_repo = os.path.join(ROOT_DIR, '.repo/manifests')
    if not os.path.exists(manifest_repo):
        return

    try:
        result = subprocess.run(
            ['git', '-C', manifest_repo, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True, timeout=5
        )

        if result.returncode == 0:
            remote_url = result.stdout.strip()
            match = re.search(r'github\.com[:/]([^/]+)', remote_url)
            if match:
                github_org = match.group(1)
                # Only override ROM_NAME if not set by user
                if not ROM_DISPLAY_NAME:
                    ROM_NAME = github_org.split('-')[0].title()
                GITHUB_ORG_AVATAR = f"https://github.com/{github_org}.png?size=200"
    except:
        pass

def detect_android_version():
    """Detect Android version from manifest"""
    default_manifest = os.path.join(ROOT_DIR, '.repo/manifests/default.xml')
    if os.path.exists(default_manifest):
        try:
            with open(default_manifest, 'r') as f:
                content = f.read()
                match = re.search(r'revision="refs/tags/android-(\d+)\.', content)
                if match:
                    return match.group(1)
                match = re.search(r'android-(\d+)\.\d+\.\d+', content)
                if match:
                    return match.group(1)
        except:
            pass
    return "Unknown"

def handle_interrupt(signum, frame):
    """Handle Ctrl+C"""
    print("\n⚠️  Build interrupted by user!")

    global BUILD_PROCESS
    if BUILD_PROCESS:
        BUILD_PROCESS.terminate()

    if BUILD_MESSAGE_ID:
        msg = f"""⚠️ | <i>Build interrupted by user</i>

<b>• ROM:</b> <code>{ROM_NAME}</code>
<b>• DEVICE:</b> <code>{DEVICE}</code>

<i>Build was cancelled</i>"""

        (edit_photo_caption if USE_BANNER else edit_message)(BUILD_MESSAGE_ID, msg)

    # Cleanup banner
    banner_path = Path(os.path.join(ROOT_DIR, 'build_banner.png'))
    if banner_path.exists():
        banner_path.unlink()

    sys.exit(130)

# ============================================================================
# MAIN
# ============================================================================

def main():
    global BUILD_MESSAGE_ID, USE_BANNER, BUILD_PROCESS, LAST_PROGRESS, ANDROID_VERSION

    signal.signal(signal.SIGINT, handle_interrupt)

    print("🚀 CI Bot - Starting build...")

    # Get ROM info
    get_rom_info()
    ANDROID_VERSION = detect_android_version()

    print(f"📄 ROM: {ROM_NAME}")
    print(f"📱 Device: {DEVICE}")
    print(f"🤖 Android: {ANDROID_VERSION}")

    # Clean old logs
    for log_file in ['out/error.log', 'out/.lock', BUILD_LOG]:
        Path(log_file).unlink(missing_ok=True)

    # Generate and send banner
    banner_file = generate_build_banner()

    if banner_file and PIL_AVAILABLE:
        print("📤 Sending banner to Telegram...")
        caption = f"""<b>🔨 Building {ROM_NAME}</b>

<b>Device:</b> {DEVICE} | <b>Android:</b> {ANDROID_VERSION}
<b>Type:</b> {'Official' if 'OFFICIAL' in os.environ else 'Unofficial'}

<b>⏳ Status:</b> Initializing build..."""

        BUILD_MESSAGE_ID = send_photo(banner_file, caption)
        USE_BANNER = bool(BUILD_MESSAGE_ID)

    if not USE_BANNER:
        print("📤 Sending text message...")
        text = f"""🟡 | <i>Compiling ROM...</i>

<b>• ROM:</b> <code>{ROM_NAME}</code>
<b>• DEVICE:</b> <code>{DEVICE}</code>
<b>• ANDROID VERSION:</b> <code>{ANDROID_VERSION}</code>
<b>• TYPE:</b> <code>{'Official' if 'OFFICIAL' in os.environ else 'Unofficial'}</code>
<b>• PROGRESS:</b> <code>Initializing...</code>"""
        BUILD_MESSAGE_ID = send_message(text)

    if not BUILD_MESSAGE_ID:
        print("❌ Failed to send Telegram message!")
        return

    build_start_time = time.time()

    # Build command
    if ROM_TYPE.startswith('axion-'):
        gms_type = ROM_TYPE.split('-')[1]
        gms_variant = 'vanilla' if gms_type == 'vanilla' else f'gms {gms_type}'
        build_cmd = f'. build/envsetup.sh && axion {DEVICE} {VARIANT} {gms_variant} && ax -b -j12 {VARIANT}'
        print(f"Build command: axion {DEVICE} {VARIANT} {gms_variant}")
    else:
        build_cmd = f'. build/envsetup.sh && brunch {DEVICE}'
        print(f"Build command: brunch {DEVICE}")

    print(f"Log file: {BUILD_LOG}\n")

    # Start build
    with open(BUILD_LOG, 'w') as log_file:
        BUILD_PROCESS = subprocess.Popen(
            build_cmd, shell=True, executable='/bin/bash',
            stdout=log_file, stderr=subprocess.STDOUT
        )

    # Monitor build
    Thread(target=tail_build_log, daemon=True).start()
    Thread(target=monitor_progress, daemon=True).start()

    # Wait for completion
    BUILD_PROCESS.wait()
    build_duration = int(time.time() - build_start_time)

    # Check for errors
    error_log = 'out/error.log'
    build_failed = False

    if BUILD_PROCESS.returncode != 0:
        build_failed = True
        print(f"❌ Build failed")
    elif os.path.exists(error_log) and os.path.getsize(error_log) > 0:
        build_failed = True
        print("❌ Build failed!")
    elif os.path.exists(BUILD_LOG):
        try:
            with open(BUILD_LOG, 'r') as f:
                log_content = f.read()
                if any(pattern in log_content for pattern in
                       ['error:', 'FAILED:', 'Cannot locate', 'fatal:', 'panic:']):
                    build_failed = True
                    print("❌ Build failed!")
        except:
            pass

    if build_failed:
        # Get last progress for error message
        last_progress = get_build_progress()

        hours, rem = divmod(build_duration, 3600)
        minutes, seconds = divmod(rem, 60)
        time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        # Clean error message without exit code or error details
        fail_msg = f"""<b>❌ {ROM_NAME} Build Failed</b>

<b>Device:</b> {DEVICE} | <b>Android:</b> {ANDROID_VERSION}
<b>Last Progress:</b> {last_progress}
<b>Duration:</b> {time_str}

<i>Check logs below for details</i>"""

        (edit_photo_caption if USE_BANNER else edit_message)(BUILD_MESSAGE_ID, fail_msg)

        # Send error logs
        for log_file in [error_log, BUILD_LOG]:
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                send_file(log_file)
    else:
        print("✅ Build succeeded!")

        # Find ROM file
        rom_zip = find_rom_zip()
        if not rom_zip:
            print("❌ Could not find ROM zip!")
            return

        print(f"📦 Found ROM: {os.path.basename(rom_zip)}")

        # Calculate MD5
        print("🔍 Calculating MD5...")
        md5_hash = hashlib.md5()
        with open(rom_zip, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                md5_hash.update(chunk)

        rom_filename = os.path.basename(rom_zip)
        rom_size = os.path.getsize(rom_zip) / (1024**3)
        hours, rem = divmod(build_duration, 3600)
        minutes, seconds = divmod(rem, 60)

        # Success message
        time_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        success_msg = f"""<b>✅ {ROM_NAME} Build Complete!</b>

<b>Device:</b> {DEVICE} | <b>Android:</b> {ANDROID_VERSION}
<b>Type:</b> {'Official' if 'OFFICIAL' in os.environ else 'Unofficial'}

<b>📊 Stats:</b>
<b>• Duration:</b> {time_str}

<b>🔧 File:</b>
<b>• Name:</b> <code>{html_escape(rom_filename)}</code>
<b>• Size:</b> {rom_size:.2f} GiB
<b>• MD5:</b> <code>{md5_hash.hexdigest()}</code>

<b>📁 Status:</b> Files saved locally"""

        (edit_photo_caption if USE_BANNER else edit_message)(BUILD_MESSAGE_ID, success_msg)

        # Send build log
        if os.path.exists(BUILD_LOG):
            send_file(BUILD_LOG)

    # Cleanup
    banner_path = Path(os.path.join(ROOT_DIR, 'build_banner.png'))
    if banner_path.exists():
        banner_path.unlink()

    print(f"\n{'❌' if build_failed else '✅'} Build {'failed' if build_failed else 'completed'} in {build_duration//60}m {build_duration%60}s")
    print("=" * 60)

if __name__ == "__main__":
    main()
