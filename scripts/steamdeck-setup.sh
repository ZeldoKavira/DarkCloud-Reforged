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

# ── Helpers ──────────────────────────────────────────────────────────────────
info()  { echo -e "\e[1;34m[INFO]\e[0m $*"; }
warn()  { echo -e "\e[1;33m[WARN]\e[0m $*"; }
error() { echo -e "\e[1;31m[ERROR]\e[0m $*"; }

mkdir -p "$BASE_DIR"

# ── 0. Self-install & self-update ────────────────────────────────────────────
CURRENT_SCRIPT="${BASH_SOURCE[0]:-}"
if [[ -z "$CURRENT_SCRIPT" ]] || [[ "$(realpath "$CURRENT_SCRIPT" 2>/dev/null)" != "$(realpath "$LOCAL_SCRIPT" 2>/dev/null)" ]]; then
    info "Installing script to $LOCAL_SCRIPT..."
    curl -fsSL -o "$LOCAL_SCRIPT" "$SCRIPT_URL"
    chmod +x "$LOCAL_SCRIPT"
    exec "$LOCAL_SCRIPT" "$@"
fi

info "Checking for script updates..."
if curl -fsSL -o "$LOCAL_SCRIPT.tmp" "$SCRIPT_URL"; then
    if ! cmp -s "$LOCAL_SCRIPT.tmp" "$LOCAL_SCRIPT" 2>/dev/null; then
        mv "$LOCAL_SCRIPT.tmp" "$LOCAL_SCRIPT"
        chmod +x "$LOCAL_SCRIPT"
        info "Script updated, restarting..."
        exec "$LOCAL_SCRIPT" "$@"
    else
        rm -f "$LOCAL_SCRIPT.tmp"
        info "Script is up to date."
    fi
else
    rm -f "$LOCAL_SCRIPT.tmp"
    warn "Could not check for script updates."
fi

# ── 1. Download PCSX2 AppImage ───────────────────────────────────────────────
PCSX2_BIN="$BASE_DIR/pcsx2.AppImage"
if [[ ! -f "$PCSX2_BIN" ]]; then
    info "Downloading PCSX2 v2.6.3..."
    curl -L -o "$PCSX2_BIN" "$PCSX2_URL"
    chmod +x "$PCSX2_BIN"
else
    info "PCSX2 already downloaded."
fi

# ── 2. Download latest Linux mod release ─────────────────────────────────────
MOD_BIN="$BASE_DIR/DarkCloud-Reforged"
info "Fetching latest mod release..."
DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$MOD_REPO/releases/latest" \
    | grep -o '"browser_download_url": *"[^"]*Linux[^"]*\.zip"' \
    | head -1 \
    | cut -d'"' -f4 || true)

if [[ -z "$DOWNLOAD_URL" ]]; then
    DOWNLOAD_URL=$(curl -s "https://api.github.com/repos/$MOD_REPO/releases" \
        | grep -o '"browser_download_url": *"[^"]*Linux[^"]*\.zip"' \
        | head -1 \
        | cut -d'"' -f4 || true)
fi

if [[ -n "$DOWNLOAD_URL" ]]; then
    info "Downloading $DOWNLOAD_URL"
    if curl -fL -o "$BASE_DIR/mod.zip" "$DOWNLOAD_URL"; then
        unzip -o "$BASE_DIR/mod.zip" -d "$BASE_DIR"
        rm "$BASE_DIR/mod.zip"
        chmod +x "$MOD_BIN"
        info "Mod updated."
    elif [[ -f "$MOD_BIN" ]]; then
        warn "Download failed, using existing version."
    else
        error "Download failed and no existing version found."
        exit 1
    fi
elif [[ -f "$MOD_BIN" ]]; then
    warn "Could not find a release, using existing version."
else
    error "Could not find a Linux release. Check https://github.com/$MOD_REPO/releases"
    exit 1
fi

# ── 3. Check for ISO ────────────────────────────────────────────────────────
while [[ ! -f "$BASE_DIR/$ISO_NAME" ]]; do
    warn "\"$ISO_NAME\" not found in $BASE_DIR"
    echo "Please copy your ISO to:"
    echo "  $BASE_DIR/$ISO_NAME"
    echo ""
    read -rp "Press Enter once you've placed the file..."
done
info "ISO found."

# ── 4. Install game settings INI ────────────────────────────────────────────
GS_DIR="$PCSX2_CONFIG/gamesettings"
mkdir -p "$GS_DIR"
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

# ── 5. Check BIOS ───────────────────────────────────────────────────────────
BIOS_DIR="$PCSX2_CONFIG/bios"
mkdir -p "$BIOS_DIR"
while ! ls "$BIOS_DIR"/*.bin &>/dev/null; do
    warn "No BIOS .bin files found in $BIOS_DIR"
    echo "Please copy your PS2 BIOS .bin file(s) to:"
    echo "  $BIOS_DIR/"
    echo ""
    read -rp "Press Enter once you've placed the file..."
done
info "BIOS found."

# ── 6. Install PNACH (cheats) ───────────────────────────────────────────────
CHEATS_DIR="$PCSX2_CONFIG/cheats"
mkdir -p "$CHEATS_DIR"
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
    info "Created Steam shortcut. In Desktop Mode: Steam → Add a Game → Add a Non-Steam Game → check 'Dark Cloud Reforged'."
else
    info "Steam shortcut already exists."
fi

# ── 8. Launch ────────────────────────────────────────────────────────────────
info "Starting DarkCloud-Reforged mod..."
"$MOD_BIN" &

info "Starting PCSX2..."
"$PCSX2_BIN" -fullscreen -- "$BASE_DIR/$ISO_NAME"
