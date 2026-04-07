#!/bin/bash

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                                                                              ║
# ║     N O V A    O S                                                           ║
# ║     Sovereign Infrastructure Engine                                          ║
# ║                                                                              ║
# ║     The Architect's Operating System                                         ║
# ║     Version 3.0.0                                                            ║
# ║                                                                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# ═══════════════════════════════════════════════════════════════════════════════
# PALETTE — Pure Monochrome. Space. Silence. Power.
# ═══════════════════════════════════════════════════════════════════════════════

W='\033[1;97m'           # Pure white bold
w='\033[0;97m'           # Pure white
S='\033[0;37m'           # Silver
G='\033[0;90m'           # Dark grey
D='\033[2;37m'           # Dim
B='\033[1m'              # Bold
I='\033[3m'              # Italic
U='\033[4m'              # Underline
R='\033[0m'              # Reset
H='\033[0;90m'           # Subtle
ACCENT='\033[38;5;255m'  # Star white

# Unicode
SB="✦"    # Star bright
SD="·"    # Star dim
SM="⋆"    # Star medium
DF="●"    # Dot full
DE="○"    # Dot empty
DR="◎"    # Dot ring
DH="◉"    # Dot heavy
DM="◆"    # Diamond
CK="✓"    # Check
CX="✕"    # Cross
AR="▸"    # Arrow
AL="→"    # Arrow long
LH="─"    # Line horizontal
LV="│"    # Line vertical
CTL="╭"   # Corner top left
CTR="╮"   # Corner top right
CBL="╰"   # Corner bottom left
CBR="╯"   # Corner bottom right
DTL="╔"   # Double top left
DTR="╗"   # Double top right
DBL="╚"   # Double bottom left
DBR="╝"   # Double bottom right
DH2="═"   # Double horizontal
DV="║"    # Double vertical
BF="█"    # Block full
BL="░"    # Block light

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBALS
# ═══════════════════════════════════════════════════════════════════════════════

NOVA_VERSION="3.0.0"
NOVA_DIR="$HOME/nova-os"
MIGRATION_FILE=""
SOURCE_DIR="$HOME"
TW=$(tput cols 2>/dev/null || echo 80)

# Component status
HAS_N8N=false
HAS_CADDY=false
HAS_COMPOSE=false
HAS_WHATSAPP=false
HAS_BROWSERLESS=false
HAS_LGTV=false
HAS_TV_BRIDGE=false
HAS_BACKUP_SQL=false
HAS_DOT_N8N=false
HAS_ENV=false
HAS_DOCKER=false

# ═══════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

center() {
    local text="$1"
    local clean=$(echo -e "$text" | sed 's/\x1b\[[0-9;]*m//g')
    local len=${#clean}
    local pad=$(( (TW - len) / 2 ))
    [ $pad -lt 0 ] && pad=0
    printf "%${pad}s" ""
    echo -e "$text"
}

hr() {
    local char="${1:-$LH}"
    local width="${2:-54}"
    local line=""
    for i in $(seq 1 $width); do line+="$char"; done
    echo -e "    ${G}${line}${R}"
}

void() { for i in $(seq 1 ${1:-1}); do echo ""; done; }

starfield() {
    local lines=${1:-2}
    local density=${2:-30}
    for i in $(seq 1 $lines); do
        local line=""
        for j in $(seq 1 $TW); do
            local r=$((RANDOM % density))
            case $r in
                0) line+="${G}${SD}${R}" ;;
                1) line+="${D}${SM}${R}" ;;
                2) line+="${S}${SB}${R}" ;;
                *) line+=" " ;;
            esac
        done
        echo -e "$line"
        sleep 0.015
    done
}

pulse() {
    local msg="$1"
    local frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    for i in $(seq 1 ${2:-15}); do
        for f in "${frames[@]}"; do
            printf "\r    ${G}${f}${R} ${D}${msg}${R}  "
            sleep 0.06
        done
    done
    printf "\r    ${w}${CK}${R}  ${S}${msg}${R}                              \n"
}

progress() {
    local current=$1 total=$2 width=44
    local filled=$((current * width / total))
    local empty=$((width - filled))
    local pct=$((current * 100 / total))
    printf "\r    ${G}${LV}${R}"
    [ $filled -gt 0 ] && printf "${w}%*s${R}" $filled | tr ' ' "${BF}"
    [ $empty -gt 0 ] && printf "${G}%*s${R}" $empty | tr ' ' "${BL}"
    printf "${G}${LV}${R} ${W}%3d%%${R}" $pct
}

ok()   { echo -e "    ${w}${CK}${R}  ${S}$1${R}"; }
fail() { echo -e "    ${G}${CX}${R}  ${D}$1${R}"; }
info() { echo -e "    ${w}${DM}${R}  ${S}$1${R}"; }
dim()  { echo -e "    ${D}$1${R}"; }
heading() {
    echo ""
    echo -e "    ${W}${DH} $1${R}"
    hr
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# BOOT SEQUENCE — THE FIRST LIGHT
# ═══════════════════════════════════════════════════════════════════════════════

boot() {
    clear
    printf '\033[3J'
    
    # Phase 1: Darkness with emerging stars
    void 1
    starfield 3 60
    sleep 0.3
    
    # Phase 2: The supernova appears — dim first
    void 1
    
    local logo_dim=(
        "                                                                     "
        "    ██████╗   ██╗   ██████╗   ██╗    ██╗   █████╗                    "
        "    ██╔══██╗  ██║   ██╔══██╗  ██║    ██║  ██╔══██╗                   "
        "    ██║  ██║  ██║   ██║  ██║  ██║    ██║  ███████║                   "
        "    ██║  ██║  ██║   ██║  ██║  ╚██╗  ██╔╝  ██╔══██║                   "
        "    ██║  ██║  ██║   ╚█████╔╝   ╚████╔╝   ██║  ██║                   "
        "    ╚═╝  ╚═╝  ╚═╝    ╚════╝     ╚═══╝    ╚═╝  ╚═╝                   "
        "                                                                     "
    )
    
    # First pass: ghost
    for line in "${logo_dim[@]}"; do
        echo -e "${G}${line}${R}"
        sleep 0.04
    done
    
    sleep 0.4
    
    # Second pass: ignite
    tput cuu ${#logo_dim[@]}
    
    for line in "${logo_dim[@]}"; do
        echo -e "${W}${line}${R}"
        sleep 0.03
    done
    
    sleep 0.2
    
    # The identity line
    local tag="S O V E R E I G N   I N F R A S T R U C T U R E   E N G I N E"
    center "${G}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${R}"
    void 1
    center "${S}${tag}${R}"
    void 1
    center "${G}v${NOVA_VERSION}  ${LH}${LH}  the architect${R}"
    void 1
    center "${G}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${R}"
    
    starfield 1 60
    void 1
    
    sleep 0.5
}

# ═══════════════════════════════════════════════════════════════════════════════
# DEEP SCAN — KNOW THY TERRITORY
# ═══════════════════════════════════════════════════════════════════════════════

deep_scan() {
    heading "SYSTEM ANALYSIS"
    
    # OS
    sleep 0.1
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        local os=$(cat /etc/os-release 2>/dev/null | grep "PRETTY_NAME" | cut -d'"' -f2)
        ok "os                    ${W}${os}${R}"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        ok "os                    ${W}macOS $(sw_vers -productVersion 2>/dev/null)${R}"
    fi
    sleep 0.1
    
    # Architecture
    local arch=$(uname -m 2>/dev/null)
    ok "arch                  ${W}${arch}${R}"
    sleep 0.1
    
    # Docker
    if command -v docker &> /dev/null; then
        local dv=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
        ok "docker                ${W}v${dv}${R}"
        HAS_DOCKER=true
    else
        fail "docker                ${D}not installed${R}"
        HAS_DOCKER=false
    fi
    sleep 0.1
    
    # Docker Compose
    if docker compose version &> /dev/null 2>&1; then
        local dcv=$(docker compose version 2>/dev/null | grep -oP '\d+\.\d+\.\d+' | head -1)
        ok "compose               ${W}v${dcv}${R}"
    fi
    sleep 0.1
    
    # Memory
    if command -v free &> /dev/null; then
        local mt=$(free -h 2>/dev/null | awk '/^Mem:/ {print $2}')
        local ma=$(free -h 2>/dev/null | awk '/^Mem:/ {print $7}')
        ok "memory                ${W}${ma:-?}${R} ${G}/ ${mt:-?}${R}"
    fi
    sleep 0.1
    
    # Disk
    local da=$(df -h / 2>/dev/null | awk 'NR==2 {print $4}')
    local dt=$(df -h / 2>/dev/null | awk 'NR==2 {print $2}')
    ok "disk                  ${W}${da:-?}${R} ${G}free of ${dt:-?}${R}"
    sleep 0.1
    
    # User
    ok "user                  ${W}$(whoami)${R}"
    ok "home                  ${W}${HOME}${R}"
    
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# COMPONENT DETECTION — WHAT DO WE HAVE
# ═══════════════════════════════════════════════════════════════════════════════

detect_components() {
    heading "COMPONENT DETECTION"
    
    dim "scanning filesystem for existing infrastructure..."
    echo ""
    sleep 0.3
    
    # Check for migration archive
    local archives=$(find "$HOME" -maxdepth 2 -name "*.tar.gz" -newer /tmp 2>/dev/null | head -5)
    if [ -n "$archives" ]; then
        dim "migration archives found:"
        echo "$archives" | while read f; do
            local sz=$(du -sh "$f" 2>/dev/null | cut -f1)
            echo -e "    ${w}${DM}${R}  ${S}$(basename $f)${R} ${G}(${sz})${R}"
        done
        echo ""
    fi
    
    # ── XUS-HTTPS / Main infrastructure ──────────────────────────────────
    
    echo -e "    ${W}${CTL}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${CTR}${R}"
    echo -e "    ${W}${LV}${R}                                                          ${W}${LV}${R}"
    echo -e "    ${W}${LV}${R}  ${W}INFRASTRUCTURE CORE${R}                                     ${W}${LV}${R}"
    echo -e "    ${W}${LV}${R}                                                          ${W}${LV}${R}"
    
    # docker-compose.yml
    if [ -f "$HOME/xus-https/docker-compose.yml" ]; then
        echo -e "    ${W}${LV}${R}  ${w}${CK}${R}  ${S}docker-compose.yml${R}                               ${W}${LV}${R}"
        HAS_COMPOSE=true
    elif [ -f "$NOVA_DIR/docker-compose.yml" ]; then
        echo -e "    ${W}${LV}${R}  ${w}${CK}${R}  ${S}docker-compose.yml${R}  ${G}(nova-os)${R}                ${W}${LV}${R}"
        HAS_COMPOSE=true
    else
        echo -e "    ${W}${LV}${R}  ${G}${CX}${R}  ${D}docker-compose.yml${R}  ${D}will generate${R}            ${W}${LV}${R}"
    fi
    sleep 0.1
    
    # Caddyfile
    if [ -f "$HOME/xus-https/Caddyfile" ]; then
        echo -e "    ${W}${LV}${R}  ${w}${CK}${R}  ${S}Caddyfile${R}                                        ${W}${LV}${R}"
        HAS_CADDY=true
    else
        echo -e "    ${W}${LV}${R}  ${G}${CX}${R}  ${D}Caddyfile${R}  ${D}will generate${R}                     ${W}${LV}${R}"
    fi
    sleep 0.1
    
    # .env
    if [ -f "$HOME/xus-https/.env" ]; then
        echo -e "    ${W}${LV}${R}  ${w}${CK}${R}  ${S}.env${R}                                             ${W}${LV}${R}"
        HAS_ENV=true
    fi
    sleep 0.1
    
    # backup_total.sql
    if [ -f "$HOME/xus-https/backup_total.sql" ]; then
        local sql_size=$(du -sh "$HOME/xus-https/backup_total.sql" 2>/dev/null | cut -f1)
        echo -e "    ${W}${LV}${R}  ${w}${CK}${R}  ${S}backup_total.sql${R}  ${G}(${sql_size})${R}                     ${W}${LV}${R}"
        HAS_BACKUP_SQL=true
    fi
    sleep 0.1
    
    # .n8n directory
    if [ -d "$HOME/.n8n" ]; then
        local n8n_size=$(du -sh "$HOME/.n8n" 2>/dev/null | cut -f1)
        echo -e "    ${W}${LV}${R}  ${w}${CK}${R}  ${S}.n8n/${R}  ${G}(${n8n_size})${R}                                  ${W}${LV}${R}"
        HAS_DOT_N8N=true
    fi
    sleep 0.1
    
    echo -e "    ${W}${LV}${R}                                                          ${W}${LV}${R}"
    echo -e "    ${W}${CBL}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${CBR}${R}"
    echo ""
    
    # ── BRIDGES & CONNECTIONS ────────────────────────────────────────────
    
    echo -e "    ${S}${CTL}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${CTR}${R}"
    echo -e "    ${S}${LV}${R}                                                          ${S}${LV}${R}"
    echo -e "    ${S}${LV}${R}  ${W}BRIDGES & CONNECTIONS${R}                                   ${S}${LV}${R}"
    echo -e "    ${S}${LV}${R}                                                          ${S}${LV}${R}"
    
    # WhatsApp Bridge
    if [ -d "$HOME/whatsapp-bridge" ]; then
        echo -e "    ${S}${LV}${R}  ${w}${CK}${R}  ${S}whatsapp-bridge/${R}                                 ${S}${LV}${R}"
        HAS_WHATSAPP=true
    else
        echo -e "    ${S}${LV}${R}  ${G}${CX}${R}  ${D}whatsapp-bridge/${R}  ${D}will install${R}               ${S}${LV}${R}"
    fi
    sleep 0.1
    
    # TV Bridge
    if [ -d "$HOME/tv-bridge" ]; then
        echo -e "    ${S}${LV}${R}  ${w}${CK}${R}  ${S}tv-bridge/${R}                                      ${S}${LV}${R}"
        HAS_TV_BRIDGE=true
    fi
    sleep 0.1
    
    # LGTV2
    if [ -d "$HOME/.lgtv2" ]; then
        echo -e "    ${S}${LV}${R}  ${w}${CK}${R}  ${S}.lgtv2/${R}                                         ${S}${LV}${R}"
        HAS_LGTV=true
    fi
    sleep 0.1
    
    # Browserless
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "browser"; then
        echo -e "    ${S}${LV}${R}  ${w}${CK}${R}  ${S}browserless${R}  ${G}(running)${R}                      ${S}${LV}${R}"
        HAS_BROWSERLESS=true
    else
        echo -e "    ${S}${LV}${R}  ${G}${CX}${R}  ${D}browserless${R}  ${D}will install${R}                   ${S}${LV}${R}"
    fi
    sleep 0.1
    
    echo -e "    ${S}${LV}${R}                                                          ${S}${LV}${R}"
    echo -e "    ${S}${CBL}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${CBR}${R}"
    echo ""
    
    # ── RUNNING CONTAINERS ───────────────────────────────────────────────
    
    if [ "$HAS_DOCKER" = true ]; then
        local running=$(docker ps --format "{{.Names}}" 2>/dev/null | wc -l)
        if [ "$running" -gt 0 ]; then
            echo -e "    ${G}${CTL}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${CTR}${R}"
            echo -e "    ${G}${LV}${R}                                                          ${G}${LV}${R}"
            echo -e "    ${G}${LV}${R}  ${D}ACTIVE CONTAINERS  (${running})${R}                              ${G}${LV}${R}"
            echo -e "    ${G}${LV}${R}                                                          ${G}${LV}${R}"
            
            docker ps --format "{{.Names}}|{{.Status}}" 2>/dev/null | while IFS='|' read name status; do
                local short_status=$(echo "$status" | cut -d' ' -f1-2)
                printf "    ${G}${LV}${R}  ${w}${DF}${R}  %-20s ${G}%s${R}" "$name" "$short_status"
                # Pad to box width
                local clean_line="  ●  ${name}                    ${short_status}"
                local pad=$((54 - ${#clean_line}))
                [ $pad -gt 0 ] && printf "%${pad}s" ""
                echo -e "  ${G}${LV}${R}"
            done
            
            echo -e "    ${G}${LV}${R}                                                          ${G}${LV}${R}"
            echo -e "    ${G}${CBL}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${CBR}${R}"
            echo ""
        fi
    fi
    
    # Summary count
    local found=0
    [ "$HAS_COMPOSE" = true ] && found=$((found + 1))
    [ "$HAS_CADDY" = true ] && found=$((found + 1))
    [ "$HAS_DOT_N8N" = true ] && found=$((found + 1))
    [ "$HAS_BACKUP_SQL" = true ] && found=$((found + 1))
    [ "$HAS_WHATSAPP" = true ] && found=$((found + 1))
    [ "$HAS_TV_BRIDGE" = true ] && found=$((found + 1))
    [ "$HAS_LGTV" = true ] && found=$((found + 1))
    [ "$HAS_BROWSERLESS" = true ] && found=$((found + 1))
    [ "$HAS_ENV" = true ] && found=$((found + 1))
    
    echo -e "    ${W}${found}${R} ${S}components detected${R}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# MIGRATION EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

extract_migration() {
    heading "MIGRATION SOURCE"
    
    # Find tar.gz files
    local archives=()
    while IFS= read -r f; do
        [ -f "$f" ] && archives+=("$f")
    done < <(find "$HOME" -maxdepth 2 -name "*.tar.gz" -type f 2>/dev/null | sort -t/ -k3)
    
    if [ ${#archives[@]} -gt 0 ]; then
        dim "migration archives available:"
        echo ""
        
        local idx=1
        for f in "${archives[@]}"; do
            local sz=$(du -sh "$f" 2>/dev/null | cut -f1)
            local fname=$(basename "$f")
            echo -e "    ${W}${idx}${R}  ${S}${fname}${R} ${G}(${sz})${R}"
            idx=$((idx + 1))
        done
        
        echo ""
        echo -e "    ${W}0${R}  ${D}skip — don't extract any archive${R}"
        echo ""
        
        read -p "$(echo -e "    ${W}${AR}${R} ${S}select archive to extract${R} ${G}[0]${R} ")" choice
        choice=${choice:-0}
        
        if [ "$choice" -gt 0 ] 2>/dev/null && [ "$choice" -le ${#archives[@]} ]; then
            MIGRATION_FILE="${archives[$((choice - 1))]}"
            echo ""
            dim "extracting $(basename $MIGRATION_FILE)..."
            echo ""
            
            # Extract with progress simulation
            tar -xzf "$MIGRATION_FILE" -C / 2>/dev/null &
            local pid=$!
            local i=0
            while kill -0 $pid 2>/dev/null; do
                progress $i 100
                sleep 0.3
                i=$((i + 2))
                [ $i -gt 95 ] && i=95
            done
            wait $pid 2>/dev/null
            progress 100 100
            echo ""
            echo ""
            
            ok "extraction complete"
            
            # Re-scan after extraction
            echo ""
            dim "re-scanning components..."
            echo ""
            
            [ -f "$HOME/xus-https/docker-compose.yml" ] && HAS_COMPOSE=true
            [ -f "$HOME/xus-https/Caddyfile" ] && HAS_CADDY=true
            [ -f "$HOME/xus-https/.env" ] && HAS_ENV=true
            [ -f "$HOME/xus-https/backup_total.sql" ] && HAS_BACKUP_SQL=true
            [ -d "$HOME/.n8n" ] && HAS_DOT_N8N=true
            [ -d "$HOME/whatsapp-bridge" ] && HAS_WHATSAPP=true
            [ -d "$HOME/tv-bridge" ] && HAS_TV_BRIDGE=true
            [ -d "$HOME/.lgtv2" ] && HAS_LGTV=true
            
            ok "components updated"
        else
            dim "skipping archive extraction"
        fi
    else
        dim "no migration archives found — proceeding with existing files"
    fi
    
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# DOCKER INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════

install_docker() {
    if [ "$HAS_DOCKER" = true ]; then
        return
    fi
    
    heading "INSTALLING DOCKER"
    
    dim "downloading docker engine..."
    echo ""
    
    curl -fsSL https://get.docker.com -o /tmp/get-docker.sh 2>/dev/null
    
    sudo sh /tmp/get-docker.sh > /dev/null 2>&1 &
    local pid=$!
    local i=0
    while kill -0 $pid 2>/dev/null; do
        progress $i 100
        sleep 0.5
        i=$((i + 2))
        [ $i -gt 95 ] && i=95
    done
    wait $pid 2>/dev/null
    progress 100 100
    echo ""
    echo ""
    
    sudo usermod -aG docker $USER 2>/dev/null
    
    ok "docker installed"
    HAS_DOCKER=true
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# INSTALL MISSING COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

install_missing() {
    heading "INSTALLING MISSING COMPONENTS"
    
    # ── WHATSAPP BRIDGE (Evolution API) ──────────────────────────────────
    
    if [ "$HAS_WHATSAPP" = false ]; then
        dim "setting up whatsapp bridge (evolution api)..."
        
        mkdir -p "$HOME/whatsapp-bridge"
        
        # Generate API key
        local wa_key=$(openssl rand -hex 16 2>/dev/null || date +%s%N | sha256sum | head -c 32)
        
        cat > "$HOME/whatsapp-bridge/docker-compose.yml" << WAEOF
version: '3.8'

services:
  evolution:
    image: atendai/evolution-api:v2.2.3
    container_name: nova.whatsapp
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      SERVER_URL: http://localhost:8080
      SERVER_TYPE: http
      SERVER_PORT: 8080
      AUTHENTICATION_API_KEY: ${wa_key}
      AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES: "true"
      DATABASE_ENABLED: "false"
      CACHE_REDIS_ENABLED: "false"
      CACHE_LOCAL_ENABLED: "true"
      DEL_INSTANCE: "false"
      QRCODE_LIMIT: 30
      QRCODE_COLOR: "#000000"
      CONFIG_SESSION_PHONE_CLIENT: "NOVA"
      CONFIG_SESSION_PHONE_NAME: "Chrome"
      LOG_LEVEL: "ERROR,WARN"
    volumes:
      - ./instances:/evolution/instances
      - ./store:/evolution/store
    networks:
      - nova_network

networks:
  nova_network:
    external: true
    name: nova_network
WAEOF
        
        echo "$wa_key" > "$HOME/whatsapp-bridge/.api_key"
        chmod 600 "$HOME/whatsapp-bridge/.api_key"
        
        ok "whatsapp bridge configured"
        info "api key: ${W}${wa_key}${R}"
        HAS_WHATSAPP=true
        echo ""
    fi
    
    # ── BROWSERLESS ──────────────────────────────────────────────────────
    
    if [ "$HAS_BROWSERLESS" = false ]; then
        dim "setting up browserless chrome..."
        
        mkdir -p "$HOME/browserless"
        
        cat > "$HOME/browserless/docker-compose.yml" << BREOF
version: '3.8'

services:
  browserless:
    image: browserless/chrome:1.61-puppeteer-21.9.0
    container_name: nova.stealth
    restart: unless-stopped
    ports:
      - "3001:3000"
    environment:
      MAX_CONCURRENT_SESSIONS: 10
      CONNECTION_TIMEOUT: 60000
      MAX_QUEUE_LENGTH: 20
      PREBOOT_CHROME: "true"
      KEEP_ALIVE: "true"
    deploy:
      resources:
        limits:
          memory: 2G
    networks:
      - nova_network

networks:
  nova_network:
    external: true
    name: nova_network
BREOF
        
        ok "browserless configured"
        HAS_BROWSERLESS=true
        echo ""
    fi
    
    # ── CADDY (if missing, replace nginx) ────────────────────────────────
    
    if [ "$HAS_CADDY" = false ]; then
        dim "generating caddyfile..."
        
        local caddy_dir="$HOME/xus-https"
        mkdir -p "$caddy_dir"
        
        read -p "$(echo -e "    ${W}${AR}${R} ${S}domain for n8n${R} ${G}[leave empty for IP]${R} ")" n8n_domain
        echo ""
        
        if [ -n "$n8n_domain" ]; then
            cat > "$caddy_dir/Caddyfile" << CADDYEOF
# NOVA OS — Caddy Gateway
# SSL certificates are fully automatic

${n8n_domain} {
    reverse_proxy localhost:5678
}
CADDYEOF
        else
            cat > "$caddy_dir/Caddyfile" << CADDYEOF
# NOVA OS — Caddy Gateway
# Using IP mode (no SSL)

:80 {
    reverse_proxy localhost:5678
}
CADDYEOF
        fi
        
        ok "caddyfile generated"
        HAS_CADDY=true
        echo ""
    fi
}

# ═══════════════════════════════════════════════════════════════════════════════
# DEPLOY EVERYTHING
# ═══════════════════════════════════════════════════════════════════════════════

deploy_all() {
    heading "DEPLOYING NOVA OS"
    
    # Create shared network
    docker network create nova_network 2>/dev/null || true
    ok "network: nova_network"
    sleep 0.2
    
    # ── Deploy main stack (xus-https) ────────────────────────────────────
    
    if [ "$HAS_COMPOSE" = true ]; then
        dim "deploying main infrastructure..."
        
        local compose_dir=""
        [ -f "$HOME/xus-https/docker-compose.yml" ] && compose_dir="$HOME/xus-https"
        [ -f "$NOVA_DIR/docker-compose.yml" ] && compose_dir="$NOVA_DIR"
        
        if [ -n "$compose_dir" ]; then
            cd "$compose_dir"
            
            docker compose pull 2>&1 | while IFS= read -r line; do
                [[ "$line" == *"Pull"* ]] && echo -e "    ${G}${AR}${R} ${D}${line}${R}"
            done
            
            docker compose up -d 2>/dev/null
            ok "main stack deployed"
        fi
        echo ""
    fi
    
    # ── Deploy WhatsApp Bridge ───────────────────────────────────────────
    
    if [ -f "$HOME/whatsapp-bridge/docker-compose.yml" ]; then
        dim "deploying whatsapp bridge..."
        cd "$HOME/whatsapp-bridge"
        docker compose up -d 2>/dev/null
        ok "whatsapp bridge deployed"
        echo ""
    fi
    
    # ── Deploy Browserless ───────────────────────────────────────────────
    
    if [ -f "$HOME/browserless/docker-compose.yml" ]; then
        dim "deploying browserless..."
        cd "$HOME/browserless"
        docker compose up -d 2>/dev/null
        ok "browserless deployed"
        echo ""
    fi
    
    # ── Restore Database ─────────────────────────────────────────────────
    
    if [ "$HAS_BACKUP_SQL" = true ]; then
        echo ""
        read -p "$(echo -e "    ${W}${AR}${R} ${S}restore database from backup_total.sql?${R} ${G}[Y/n]${R} ")" restore_db
        restore_db=${restore_db:-Y}
        
        if [[ "$restore_db" =~ ^[Yy]$ ]]; then
            dim "waiting for postgresql to be ready..."
            sleep 8
            
            # Find postgres container
            local pg_container=$(docker ps --format "{{.Names}}" 2>/dev/null | grep -i "postgres" | head -1)
            
            if [ -n "$pg_container" ]; then
                dim "restoring database..."
                
                cat "$HOME/xus-https/backup_total.sql" | \
                    docker exec -i "$pg_container" psql -U nova -d nova_n8n 2>/dev/null
                
                if [ $? -eq 0 ]; then
                    ok "database restored from backup_total.sql"
                else
                    fail "database restore had warnings (may be normal)"
                fi
            else
                fail "no postgres container found — manual restore needed"
            fi
        fi
        echo ""
    fi
    
    # ── Wait and verify ──────────────────────────────────────────────────
    
    dim "waiting for services to initialize..."
    echo ""
    
    for i in $(seq 1 20); do
        progress $i 20
        sleep 1
    done
    echo ""
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# GENERATE NOVA CLI
# ═══════════════════════════════════════════════════════════════════════════════

generate_cli() {
    heading "INSTALLING NOVA CLI"
    
    sudo tee /usr/local/bin/nova > /dev/null << 'NOVAEOF'
#!/bin/bash
W='\033[1;97m' w='\033[0;97m' S='\033[0;37m' G='\033[0;90m' D='\033[2;37m' R='\033[0m'

logo() { echo -e "\n    ${G}◉${R} ${W}NOVA${R} ${G}v3.0${R}\n"; }

case "${1:-help}" in
    status)
        logo
        echo -e "    ${W}services${R}"
        echo -e "    ${G}────────────────────────────────────────────────────${R}\n"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null | while read l; do
            echo -e "    ${S}${l}${R}"
        done
        echo "" ;;
    start)
        logo
        for d in ~/xus-https ~/whatsapp-bridge ~/browserless; do
            [ -f "$d/docker-compose.yml" ] && (cd "$d" && docker compose up -d 2>/dev/null)
        done
        echo -e "    ${w}✓${R} ${S}all services started${R}\n" ;;
    stop)
        logo
        for d in ~/xus-https ~/whatsapp-bridge ~/browserless; do
            [ -f "$d/docker-compose.yml" ] && (cd "$d" && docker compose down 2>/dev/null)
        done
        echo -e "    ${w}✓${R} ${S}all services stopped${R}\n" ;;
    restart)
        logo
        for d in ~/xus-https ~/whatsapp-bridge ~/browserless; do
            [ -f "$d/docker-compose.yml" ] && (cd "$d" && docker compose restart 2>/dev/null)
        done
        echo -e "    ${w}✓${R} ${S}all services restarted${R}\n" ;;
    logs)
        logo
        if [ -n "$2" ]; then
            docker logs -f --tail=50 "$2" 2>/dev/null
        else
            echo -e "    ${S}usage:${R} ${W}nova logs <container_name>${R}"
            echo -e "    ${S}       nova logs nova.whatsapp${R}\n"
            docker ps --format "    ${G}▸${R} {{.Names}}" 2>/dev/null
            echo ""
        fi ;;
    backup)
        logo
        local ts=$(date +%Y%m%d_%H%M%S)
        echo -e "    ${D}creating full backup...${R}"
        tar -czf ~/nova_backup_${ts}.tar.gz \
            ~/xus-https ~/whatsapp-bridge ~/browserless \
            ~/.n8n ~/.lgtv2 ~/tv-bridge 2>/dev/null
        local sz=$(du -sh ~/nova_backup_${ts}.tar.gz 2>/dev/null | cut -f1)
        echo -e "    ${w}✓${R} ${S}backup created${R} ${G}(${sz})${R}"
        echo -e "    ${D}~/nova_backup_${ts}.tar.gz${R}\n" ;;
    whatsapp)
        logo
        local ip=$(curl -s -4 ifconfig.me 2>/dev/null || echo "localhost")
        echo -e "    ${W}WhatsApp Bridge${R}"
        echo -e "    ${G}────────────────────────────────────────────────────${R}\n"
        echo -e "    ${S}dashboard${R}      ${W}http://${ip}:8080${R}"
        echo -e "    ${S}manager${R}        ${W}http://${ip}:8080/manager${R}"
        if [ -f ~/whatsapp-bridge/.api_key ]; then
            local key=$(cat ~/whatsapp-bridge/.api_key)
            echo -e "    ${S}api key${R}        ${W}${key}${R}"
        fi
        echo "" ;;
    creds)
        logo
        echo -e "    ${W}credentials${R}"
        echo -e "    ${G}────────────────────────────────────────────────────${R}\n"
        [ -f ~/xus-https/.env ] && echo -e "    ${S}.env${R}" && cat ~/xus-https/.env | while read l; do
            [[ -n "$l" && "$l" != \#* ]] && echo -e "    ${D}${l}${R}"
        done
        [ -f ~/whatsapp-bridge/.api_key ] && echo -e "\n    ${S}wa api key${R}  ${W}$(cat ~/whatsapp-bridge/.api_key)${R}"
        echo "" ;;
    migrate)
        logo
        local ts=$(date +%Y%m%d_%H%M%S)
        echo -e "    ${D}creating full migration package...${R}\n"
        tar -czf ~/nova_migrate_${ts}.tar.gz \
            ~/xus-https ~/whatsapp-bridge ~/browserless \
            ~/.n8n ~/.lgtv2 ~/tv-bridge \
            /usr/local/bin/nova 2>/dev/null
        local sz=$(du -sh ~/nova_migrate_${ts}.tar.gz 2>/dev/null | cut -f1)
        echo -e "    ${w}✓${R} ${S}migration package created${R} ${G}(${sz})${R}"
        echo -e "    ${D}~/nova_migrate_${ts}.tar.gz${R}\n"
        echo -e "    ${W}on the new server:${R}"
        echo -e "    ${G}  1.${R} ${S}scp the file to the new server${R}"
        echo -e "    ${G}  2.${R} ${w}tar xzf nova_migrate_${ts}.tar.gz -C /${R}"
        echo -e "    ${G}  3.${R} ${w}./install.sh${R}\n" ;;
    update)
        logo
        echo -e "    ${D}pulling latest images...${R}"
        for d in ~/xus-https ~/whatsapp-bridge ~/browserless; do
            [ -f "$d/docker-compose.yml" ] && (cd "$d" && docker compose pull 2>/dev/null)
        done
        echo -e "    ${D}restarting...${R}"
        for d in ~/xus-https ~/whatsapp-bridge ~/browserless; do
            [ -f "$d/docker-compose.yml" ] && (cd "$d" && docker compose up -d 2>/dev/null)
        done
        echo -e "    ${w}✓${R} ${S}updated${R}\n" ;;
    destroy)
        logo
        echo -e "    ${W}this will stop and remove all containers${R}\n"
        read -p "$(echo -e "    ${W}▸${R} ${S}type DESTROY to confirm:${R} ")" c
        if [ "$c" = "DESTROY" ]; then
            for d in ~/xus-https ~/whatsapp-bridge ~/browserless; do
                [ -f "$d/docker-compose.yml" ] && (cd "$d" && docker compose down -v 2>/dev/null)
            done
            echo -e "    ${w}✓${R} ${S}destroyed${R}"
        else echo -e "    ${D}cancelled${R}"; fi
        echo "" ;;
    help|*)
        logo
        echo -e "    ${W}commands${R}"
        echo -e "    ${G}────────────────────────────────────────────────────${R}\n"
        echo -e "    ${w}nova status${R}       ${G}all services status${R}"
        echo -e "    ${w}nova start${R}        ${G}start everything${R}"
        echo -e "    ${w}nova stop${R}         ${G}stop everything${R}"
        echo -e "    ${w}nova restart${R}      ${G}restart everything${R}"
        echo -e "    ${w}nova logs${R}         ${G}view container logs${R}"
        echo ""
        echo -e "    ${w}nova whatsapp${R}     ${G}whatsapp bridge info + QR${R}"
        echo -e "    ${w}nova creds${R}        ${G}show all credentials${R}"
        echo ""
        echo -e "    ${w}nova backup${R}       ${G}create full backup${R}"
        echo -e "    ${w}nova migrate${R}      ${G}export for server move${R}"
        echo -e "    ${w}nova update${R}       ${G}pull latest images${R}"
        echo -e "    ${w}nova destroy${R}      ${G}remove everything${R}\n" ;;
esac
NOVAEOF
    
    sudo chmod +x /usr/local/bin/nova
    ok "nova command installed"
    dim "type 'nova' from anywhere"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# FIX PERMISSIONS
# ═══════════════════════════════════════════════════════════════════════════════

fix_permissions() {
    heading "FIXING PERMISSIONS"
    
    local user=$(whoami)
    
    for dir in xus-https whatsapp-bridge browserless tv-bridge .n8n .lgtv2; do
        if [ -e "$HOME/$dir" ]; then
            sudo chown -R ${user}:${user} "$HOME/$dir" 2>/dev/null
            ok "$dir ${G}→ ${user}${R}"
        fi
    done
    
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY — THE NEW STAR
# ═══════════════════════════════════════════════════════════════════════════════

finale() {
    local ip=$(curl -s -4 ifconfig.me 2>/dev/null || echo "localhost")
    
    echo ""
    starfield 1 50
    echo ""
    
    # The box
    echo -e "    ${W}${DTL}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DTR}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${W}N O V A   O S${R}                                            ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${G}deployed successfully${R}                                      ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${G}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${R}    ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    
    # Show endpoints
    echo -e "    ${W}${DV}${R}    ${W}ENDPOINTS${R}                                                  ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    
    # n8n
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "n8n"; then
        echo -e "    ${W}${DV}${R}    ${w}${DF}${R}  ${S}n8n${R}              ${W}http://${ip}:5678${R}               ${W}${DV}${R}"
    fi
    
    # WhatsApp
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "whatsapp\|evolution"; then
        echo -e "    ${W}${DV}${R}    ${w}${DF}${R}  ${S}whatsapp${R}         ${W}http://${ip}:8080${R}               ${W}${DV}${R}"
        echo -e "    ${W}${DV}${R}         ${D}qr scan${R}         ${W}http://${ip}:8080/manager${R}       ${W}${DV}${R}"
    fi
    
    # Browserless
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "stealth\|browser"; then
        echo -e "    ${W}${DV}${R}    ${w}${DF}${R}  ${S}browserless${R}      ${W}http://${ip}:3001${R}               ${W}${DV}${R}"
    fi
    
    # PostgreSQL
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "postgres"; then
        echo -e "    ${W}${DV}${R}    ${w}${DF}${R}  ${S}postgresql${R}       ${W}${ip}:5432${R}                     ${W}${DV}${R}"
    fi
    
    # Redis
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "redis"; then
        echo -e "    ${W}${DV}${R}    ${w}${DF}${R}  ${S}redis${R}            ${W}${ip}:6379${R}                     ${W}${DV}${R}"
    fi
    
    # Caddy
    if docker ps --format "{{.Names}}" 2>/dev/null | grep -qi "caddy"; then
        echo -e "    ${W}${DV}${R}    ${w}${DF}${R}  ${S}caddy${R}            ${W}:80 / :443${R}                    ${W}${DV}${R}"
    fi
    
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${G}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${R}    ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${W}FILESYSTEM${R}                                                 ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    
    [ -d "$HOME/xus-https" ] &&        echo -e "    ${W}${DV}${R}    ${S}core${R}             ${D}~/xus-https/${R}                       ${W}${DV}${R}"
    [ -d "$HOME/whatsapp-bridge" ] &&   echo -e "    ${W}${DV}${R}    ${S}whatsapp${R}         ${D}~/whatsapp-bridge/${R}                 ${W}${DV}${R}"
    [ -d "$HOME/browserless" ] &&       echo -e "    ${W}${DV}${R}    ${S}stealth${R}          ${D}~/browserless/${R}                     ${W}${DV}${R}"
    [ -d "$HOME/.n8n" ] &&              echo -e "    ${W}${DV}${R}    ${S}n8n data${R}         ${D}~/.n8n/${R}                            ${W}${DV}${R}"
    [ -d "$HOME/tv-bridge" ] &&         echo -e "    ${W}${DV}${R}    ${S}tv bridge${R}        ${D}~/tv-bridge/${R}                       ${W}${DV}${R}"
    [ -d "$HOME/.lgtv2" ] &&            echo -e "    ${W}${DV}${R}    ${S}lgtv2${R}            ${D}~/.lgtv2/${R}                          ${W}${DV}${R}"
    
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${G}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${LH}${R}    ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${W}COMMANDS${R}                                                    ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${w}nova status${R}         ${G}service overview${R}                     ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${w}nova whatsapp${R}       ${G}scan QR code${R}                        ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${w}nova backup${R}         ${G}full system backup${R}                   ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${w}nova migrate${R}        ${G}prepare for server move${R}              ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${w}nova logs${R}           ${G}live container logs${R}                  ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}    ${w}nova creds${R}          ${G}show all credentials${R}                 ${W}${DV}${R}"
    echo -e "    ${W}${DV}${R}                                                              ${W}${DV}${R}"
    echo -e "    ${W}${DBL}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DH2}${DBR}${R}"
    
    echo ""
    starfield 2 50
    echo ""
    
    center "${G}a   n e w   s t a r   h a s   b e e n   i g n i t e d${R}"
    
    echo ""
    starfield 1 60
    echo ""
}

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — THE SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════════

main() {
    # The first light
    boot
    
    # Know the territory
    deep_scan
    
    # Gate
    read -p "$(echo -e "    ${W}${AR}${R} ${S}begin deployment?${R} ${G}[Y/n]${R} ")" go
    go=${go:-Y}
    [[ ! "$go" =~ ^[Yy]$ ]] && echo -e "\n    ${D}the star dims.${R}\n" && exit 0
    
    # Migration extraction
    extract_migration
    
    # Component detection (after possible extraction)
    detect_components
    
    # Docker
    install_docker
    
    # Fix what's missing
    install_missing
    
    # Fix ownership
    fix_permissions
    
    # Deploy everything
    deploy_all
    
    # Install CLI
    generate_cli
    
    # The new star
    finale
}

main "$@"
