#!/usr/bin/env bash
set -euo pipefail

# ── Config ───────────────────────────────────────────────────────────────────
BASE_DIR="$HOME/.dark-cloud-reforged"
PCSX2_CONFIG="$HOME/.config/PCSX2"
PCSX2_URL="https://github.com/PCSX2/pcsx2/releases/download/v2.6.3/pcsx2-v2.6.3-linux-appimage-x64-Qt.AppImage"
MOD_REPO="ZeldoKavira/DarkCloud-Reforged"
PNACH_NAME="A5C05C78.pnach"
ISO_NAME="Dark Cloud (USA).iso"
INI_NAME="SCUS-97111_A5C05C78.ini"
SCRIPT_URL="https://raw.githubusercontent.com/$MOD_REPO/main/scripts/steamdeck-setup.sh"
LOCAL_SCRIPT="$BASE_DIR/steamdeck-setup.sh"
VERSION_FILE="$BASE_DIR/.mod-version"
UPDATE_CONFIG="$BASE_DIR/update-config.cfg"

# ── Helpers ──────────────────────────────────────────────────────────────────
info()  { echo -e "\e[1;34m[INFO]\e[0m $*"; }
warn()  { echo -e "\e[1;33m[WARN]\e[0m $*"; }
error() { echo -e "\e[1;31m[ERROR]\e[0m $*"; }

mkdir -p "$BASE_DIR"

# ── Update config ────────────────────────────────────────────────────────────
# Create default config if it doesn't exist
if [[ ! -f "$UPDATE_CONFIG" ]]; then
    cat > "$UPDATE_CONFIG" <<'CFGEOF'
# Dark Cloud Reforged - Update Configuration
# Set to "false" to disable auto-updates for that component.

# Auto-update the PCSX2 game settings INI
auto_update_gamesettings=true

# Auto-update the mod binary and PNACH cheats file
auto_update_mod=true

# Auto-update this launcher script
auto_update_script=true
CFGEOF
    info "Created update config at $UPDATE_CONFIG"
fi

# Read config values (default to true if missing)
auto_update_gamesettings=true
auto_update_mod=true
auto_update_script=true
source "$UPDATE_CONFIG"

# ── 0. Self-install & self-update ────────────────────────────────────────────
if [[ "$auto_update_script" == "true" ]]; then
    if curl -fsSL -o "$LOCAL_SCRIPT.tmp" "$SCRIPT_URL" 2>/dev/null; then
        if ! cmp -s "$LOCAL_SCRIPT.tmp" "$LOCAL_SCRIPT" 2>/dev/null; then
            mv "$LOCAL_SCRIPT.tmp" "$LOCAL_SCRIPT"
            chmod +x "$LOCAL_SCRIPT"
            info "Script updated."
        else
            rm -f "$LOCAL_SCRIPT.tmp"
        fi
    else
        rm -f "$LOCAL_SCRIPT.tmp"
        warn "Could not check for script updates."
    fi
else
    info "Script auto-update disabled."
fi

# If we're not running from the installed location, hand off to it
CURRENT_SCRIPT="${BASH_SOURCE[0]:-}"
if [[ -z "$CURRENT_SCRIPT" ]] || [[ "$(realpath "$CURRENT_SCRIPT" 2>/dev/null)" != "$(realpath "$LOCAL_SCRIPT" 2>/dev/null)" ]]; then
    if [[ -f "$LOCAL_SCRIPT" ]]; then
        exec bash "$LOCAL_SCRIPT" "$@" </dev/tty
    fi
fi

# ── 1. Download PCSX2 AppImage ───────────────────────────────────────────────
PCSX2_BIN="$BASE_DIR/pcsx2.AppImage"
PCSX2_VERSION_FILE="$BASE_DIR/.pcsx2-version"
INSTALLED_PCSX2=""
[[ -f "$PCSX2_VERSION_FILE" ]] && INSTALLED_PCSX2=$(cat "$PCSX2_VERSION_FILE")

if [[ "$PCSX2_URL" != "$INSTALLED_PCSX2" ]]; then
    info "Downloading PCSX2..."
    curl -L -o "$PCSX2_BIN" "$PCSX2_URL"
    chmod +x "$PCSX2_BIN"
    echo "$PCSX2_URL" > "$PCSX2_VERSION_FILE"
    info "PCSX2 updated."
else
    info "PCSX2 is up to date."
fi

# ── 2. Download latest Linux mod release ─────────────────────────────────────
MOD_BIN="$BASE_DIR/DarkCloud-Reforged"
if [[ "$auto_update_mod" == "true" ]]; then
    info "Fetching latest mod release..."

LATEST_URL=$(curl -s "https://api.github.com/repos/$MOD_REPO/releases/latest" \
    | grep -o '"browser_download_url": *"[^"]*Linux[^"]*\.zip"' \
    | head -1 \
    | cut -d'"' -f4 || true)

if [[ -z "$LATEST_URL" ]]; then
    LATEST_URL=$(curl -s "https://api.github.com/repos/$MOD_REPO/releases" \
        | grep -o '"browser_download_url": *"[^"]*Linux[^"]*\.zip"' \
        | head -1 \
        | cut -d'"' -f4 || true)
fi

if [[ -n "$LATEST_URL" ]]; then
    INSTALLED_URL=""
    [[ -f "$VERSION_FILE" ]] && INSTALLED_URL=$(cat "$VERSION_FILE")

    if [[ "$LATEST_URL" != "$INSTALLED_URL" ]]; then
        info "Downloading $LATEST_URL"
        if curl -fL -o "$BASE_DIR/mod.zip" "$LATEST_URL"; then
            unzip -o "$BASE_DIR/mod.zip" -d "$BASE_DIR"
            rm "$BASE_DIR/mod.zip"
            chmod +x "$MOD_BIN"
            echo "$LATEST_URL" > "$VERSION_FILE"
            info "Mod updated."
        elif [[ -f "$MOD_BIN" ]]; then
            warn "Download failed, using existing version."
        else
            error "Download failed and no existing version found."
            exit 1
        fi
    else
        info "Mod is up to date."
    fi
elif [[ -f "$MOD_BIN" ]]; then
    warn "Could not find a release, using existing version."
else
    error "Could not find a Linux release. Check https://github.com/$MOD_REPO/releases"
    exit 1
fi
else
    info "Mod auto-update disabled."
    if [[ ! -f "$MOD_BIN" ]]; then
        error "No mod binary found and auto-update is disabled."
        exit 1
    fi
fi

# ── 3. Check for ISO ────────────────────────────────────────────────────────
while [[ ! -f "$BASE_DIR/$ISO_NAME" ]]; do
    warn "\"$ISO_NAME\" not found in $BASE_DIR"
    echo "Please copy your ISO to:"
    echo "  $BASE_DIR/$ISO_NAME"
    echo ""
    xdg-open "$BASE_DIR" 2>/dev/null &
    read -rp "Press Enter once you've placed the file..." </dev/tty
done
info "ISO found."

# ── 4. Install game settings INI ────────────────────────────────────────────
GS_DIR="$PCSX2_CONFIG/gamesettings"
mkdir -p "$GS_DIR"
if [[ "$auto_update_gamesettings" == "true" ]]; then
    info "Downloading game settings INI..."
    if curl -fsSL -o "$GS_DIR/$INI_NAME.tmp" \
        "https://raw.githubusercontent.com/$MOD_REPO/main/pcsx2-files/$INI_NAME"; then
        mv "$GS_DIR/$INI_NAME.tmp" "$GS_DIR/$INI_NAME"
        info "Game settings INI updated."
    elif [[ -f "$GS_DIR/$INI_NAME" ]]; then
        rm -f "$GS_DIR/$INI_NAME.tmp"
        warn "Download failed, using existing INI."
    else
        error "Could not download INI and no existing version found."
        exit 1
    fi
else
    info "Game settings INI auto-update disabled."
    if [[ ! -f "$GS_DIR/$INI_NAME" ]]; then
        error "No game settings INI found and auto-update is disabled."
        exit 1
    fi
fi

# ── 5. Check BIOS ───────────────────────────────────────────────────────────
BIOS_DIR="$PCSX2_CONFIG/bios"
mkdir -p "$BIOS_DIR"
while ! ls "$BIOS_DIR"/*.bin &>/dev/null; do
    warn "No BIOS .bin files found in $BIOS_DIR"
    echo "Please copy your PS2 BIOS .bin file(s) to:"
    echo "  $BIOS_DIR/"
    echo ""
    xdg-open "$BIOS_DIR" 2>/dev/null &
    read -rp "Press Enter once you've placed the file..." </dev/tty
done
info "BIOS found."

# ── 6. Install PNACH (cheats) ───────────────────────────────────────────────
CHEATS_DIR="$PCSX2_CONFIG/cheats"
mkdir -p "$CHEATS_DIR"
if [[ "$auto_update_mod" == "true" ]]; then
    info "Downloading PNACH from repo..."
    if curl -fsSL -o "$CHEATS_DIR/$PNACH_NAME.tmp" \
        "https://raw.githubusercontent.com/$MOD_REPO/main/pcsx2-files/$PNACH_NAME"; then
        mv "$CHEATS_DIR/$PNACH_NAME.tmp" "$CHEATS_DIR/$PNACH_NAME"
        info "PNACH updated."
    elif [[ -f "$CHEATS_DIR/$PNACH_NAME" ]]; then
        rm -f "$CHEATS_DIR/$PNACH_NAME.tmp"
        warn "Download failed, using existing PNACH."
    else
        error "Could not download PNACH and no existing version found."
        exit 1
    fi
else
    info "PNACH auto-update disabled."
    if [[ ! -f "$CHEATS_DIR/$PNACH_NAME" ]]; then
        error "No PNACH found and auto-update is disabled."
        exit 1
    fi
fi

# ── 7. Add to Steam ─────────────────────────────────────────────────────────
DESKTOP_FILE="$HOME/.local/share/applications/DarkCloudReforged.desktop"
if [[ ! -f "$DESKTOP_FILE" ]]; then
    info "Adding Dark Cloud Reforged to Steam..."
    mkdir -p "$HOME/.local/share/applications"
    cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Dark Cloud Reforged
Exec=$LOCAL_SCRIPT
Terminal=true
Type=Application
Categories=Game;
Comment=Dark Cloud Reforged Mod via PCSX2
EOF
    chmod +x "$DESKTOP_FILE"
    echo ""
    info "Setup complete! To add Dark Cloud Reforged to your Steam library:"
    echo "  1. Open Steam in Desktop Mode"
    echo "  2. Click 'Add a Game' (bottom-left) → 'Add a Non-Steam Game'"
    echo "  3. Check 'Dark Cloud Reforged' from the list"
    echo "  4. Click 'Add Selected Programs'"
    echo ""
    echo "It will then appear in your library and work in Gaming Mode."
    echo ""
    read -rp "Would you like to launch the game now? [y/N] " LAUNCH </dev/tty
    if [[ ! "$LAUNCH" =~ ^[Yy]$ ]]; then
        info "Done! Launch Dark Cloud Reforged from Steam whenever you're ready."
        exit 0
    fi
else
    info "Steam shortcut already exists."
fi

# ── 8. Launch ────────────────────────────────────────────────────────────────
DEV_SRC="$BASE_DIR/dev/src/main.py"
if [[ -f "$DEV_SRC" ]]; then
    info "Dev source detected, running from src/..."
    python3 "$DEV_SRC" &
else
    info "Starting DarkCloud-Reforged mod..."
    "$MOD_BIN" &
fi

info "Starting PCSX2..."
"$PCSX2_BIN" -fullscreen -- "$BASE_DIR/$ISO_NAME"
