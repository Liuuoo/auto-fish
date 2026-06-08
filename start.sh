#!/bin/bash
# ========================================
# Fishing Bot - One-Click Startup (macOS)
# ========================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}Fishing Bot - One-Click Startup (macOS)${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""

# ----------------------------------------
# Step 1: Close existing browser instances
# ----------------------------------------
echo -e "${YELLOW}[1/4] Closing existing browsers...${NC}"
killall "Google Chrome" 2>/dev/null && echo -e "${GRAY}  Chrome closed.${NC}" || echo -e "${GRAY}  Chrome not running.${NC}"
killall "Microsoft Edge" 2>/dev/null && echo -e "${GRAY}  Edge closed.${NC}" || echo -e "${GRAY}  Edge not running.${NC}"
sleep 2
echo -e "${GREEN}Done.${NC}"
echo ""

# ----------------------------------------
# Step 2: Find browser
# ----------------------------------------
echo -e "${YELLOW}[2/4] Finding browser...${NC}"

BROWSER_PATH=""
BROWSER_NAME=""

# Try Chrome first
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ -f "$CHROME_PATH" ]; then
    BROWSER_PATH="$CHROME_PATH"
    BROWSER_NAME="Google Chrome"
fi

# Try Edge if Chrome not found
if [ -z "$BROWSER_PATH" ]; then
    EDGE_PATH="/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    if [ -f "$EDGE_PATH" ]; then
        BROWSER_PATH="$EDGE_PATH"
        BROWSER_NAME="Microsoft Edge"
    fi
fi

# Try Chromium
if [ -z "$BROWSER_PATH" ]; then
    CHROMIUM_PATH="/Applications/Chromium.app/Contents/MacOS/Chromium"
    if [ -f "$CHROMIUM_PATH" ]; then
        BROWSER_PATH="$CHROMIUM_PATH"
        BROWSER_NAME="Chromium"
    fi
fi

if [ -z "$BROWSER_PATH" ]; then
    echo -e "${RED}ERROR: No supported browser found${NC}"
    echo -e "${RED}Please install Google Chrome or Microsoft Edge${NC}"
    read -p "Press Enter to exit"
    exit 1
fi

echo -e "${GREEN}Found: ${BROWSER_NAME}${NC}"
echo -e "${GRAY}Path: ${BROWSER_PATH}${NC}"
echo ""

# ----------------------------------------
# Step 3: Start browser with debugging port
# ----------------------------------------
echo -e "${YELLOW}[3/4] Starting browser with debugging port...${NC}"

PORT=9222
USER_DATA_DIR="$HOME/.chrome-fishing-9222"

# Ensure profile directory exists (persistent — keeps login session)
mkdir -p "$USER_DATA_DIR"

"$BROWSER_PATH" \
    --remote-debugging-port="$PORT" \
    --user-data-dir="$USER_DATA_DIR" \
    --remote-allow-origins=\* \
    --disable-features=RendererCodeIntegrity \
    --no-first-run \
    --no-default-browser-check \
    &

BROWSER_PID=$!
sleep 3

# Check if browser is still running
if ! kill -0 "$BROWSER_PID" 2>/dev/null; then
    echo -e "${RED}ERROR: Browser failed to start${NC}"
    echo -e "${RED}Please check the browser installation${NC}"
    read -p "Press Enter to exit"
    exit 1
fi

echo -e "${GREEN}Browser started on port ${PORT}${NC}"
echo ""

# ----------------------------------------
# Wait for user to login
# ----------------------------------------
echo -e "${YELLOW}Please complete the following steps:${NC}"
echo -e "${WHITE}  1. Visit the game website${NC}"
echo -e "${WHITE}  2. Login to your account${NC}"
echo -e "${WHITE}  3. Navigate to the fishing page${NC}"
echo ""

read -p "Press Enter when you're ready to start fishing..."

# ----------------------------------------
# Step 4: Start fishing script
# ----------------------------------------
echo ""
echo -e "${YELLOW}[4/4] Starting fishing script...${NC}"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/fishing_mac.py"

if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo -e "${RED}ERROR: fishing_mac.py not found at $PYTHON_SCRIPT${NC}"
    read -p "Press Enter to exit"
    exit 1
fi

# Open a new Terminal window running the fishing script
osascript -e "tell application \"Terminal\" to do script \"cd '$SCRIPT_DIR' && python3 '$PYTHON_SCRIPT'\""

sleep 2
echo -e "${GREEN}Fishing script started in a new Terminal window.${NC}"
echo ""

# ----------------------------------------
# Complete
# ----------------------------------------
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}Startup Complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo -e "${WHITE}  1. In the fishing script window:${NC}"
echo -e "${CYAN}     - Press F8 to bind the browser window${NC}"
echo -e "${WHITE}     - Drag to select the fishing area in the preview window${NC}"
echo -e "${CYAN}  2. Press F7 to start fishing${NC}"
echo -e "${CYAN}  3. Press F1 for equipment crafting${NC}"
echo -e "${WHITE}  4. Press ESC to stop${NC}"
echo ""
echo -e "${YELLOW}Hotkeys:${NC}"
echo -e "${CYAN}  F8  - Bind browser window${NC}"
echo -e "${CYAN}  F7  - Start/Pause fishing${NC}"
echo -e "${CYAN}  F1  - Equipment crafting${NC}"
echo -e "${CYAN}  ESC - Stop/Exit${NC}"
echo ""

read -p "Press Enter to exit this launcher"
