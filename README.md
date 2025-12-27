## How to use ?

- Navigate to your ROM source directory

```bash
cd /path/to/your/rom/source
```

- Download the script using wget

```bash
wget https://raw.githubusercontent.com/theleafir1/build-script/main/bot.py
```

Or alternatively using curl:

```bash
curl -O https://raw.githubusercontent.com/theleafir1/build-script/main/bot.py
```

- Make it executable

```bash
chmod +x bot.py
```

- Edit the script and update the variables

```bash
nano bot.py
```

- Update the configuration variables (see Variables section below)

- Run the script

```bash
python3 bot.py -h
```

- Done

### Variables 

---------------

```python
# Your device codename :
DEVICE = ""

# Your build variant : [user/userdebug/eng] 
VARIANT = ""

# ROM type : Leave empty for standard ROMs (LineageOS, AOSP, etc.)
#            For AxionAOSP use: "axion-pico" / "axion-core" / "axion-vanilla"
ROM_TYPE = ""

# Your telegram group/channel chatid eg - "-xxxxxxxx"
CONFIG_CHATID = ""

# Your HTTP API bot token (get it from botfather) 
CONFIG_BOT_TOKEN = ""

# Turn off server after build (save resource) [False/True]
POWEROFF = False

# Pin success message in chat [True/False]
PIN_SUCCESS_MESSAGE = True
```

### Requirements

```bash
# Python packages (Debian/Ubuntu)
sudo apt install python3-requests python3-pil

# Python packages (Arch Linux)
sudo pacman -S python-requests python-pillow

# Optional: Install rclone for cloud uploads
sudo apt install rclone git

# Required only if UPLOAD_OTA_JSON = True
sudo apt install netcat-openbsd
```

### Credits

Initial reference and base taken from  
[Build-Script](https://github.com/hipexscape/Build-Script) by [hipexscape](https://github.com/hipexscape).
