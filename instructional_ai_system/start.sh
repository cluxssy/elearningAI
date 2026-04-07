#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# AI Instructional Design System —  Script
# Handles: env setup, dependency checks, backend + frontend launch
# ─────────────────────────────────────────────────────────────────────────────

BACKEND_DIR="backend"
FRONTEND_DIR="frontend_react"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo "🛑 Shutting down all services..."
    kill $(jobs -p) 2>/dev/null
    exit
}
trap cleanup SIGINT SIGTERM

# ─────────────────────────────────────────────────────────────────────────────
# ENV SETUP FUNCTION
# Asks for every variable in .env.example, skipping ones already filled in.
# Pass --force to re-ask all values even if .env already exists.
# ─────────────────────────────────────────────────────────────────────────────
setup_env() {
    local dir=$1
    local force=${2:-""}
    local env_file="$dir/.env"
    local example_file="$dir/.env.example"

    if [ ! -f "$example_file" ]; then
        echo -e "${YELLOW}⚠️  No .env.example found in $dir — skipping.${NC}"
        return
    fi

    # Check if .env is missing OR if --force flag is used
    local needs_setup=false
    if [ ! -f "$env_file" ]; then
        needs_setup=true
        echo -e "${CYAN}📝 No .env found in $dir. Let's set it up now.${NC}"
    elif [ "$force" = "--force" ]; then
        needs_setup=true
        echo -e "${CYAN}📝 Re-configuring .env for: $dir${NC}"
    else
        # Check if any required key has an empty or placeholder value
        while IFS= read -r line || [ -n "$line" ]; do
            [[ -z "$line" || "$line" =~ ^# ]] && continue
            key=$(echo "$line" | cut -d '=' -f 1)
            [ -z "$key" ] && continue
            current_val=$(grep "^${key}=" "$env_file" 2>/dev/null | cut -d '=' -f 2-)
            if [ -z "$current_val" ]; then
                needs_setup=true
                echo -e "${YELLOW}⚠️  Missing value for '$key' in $dir/.env${NC}"
            fi
        done < "$example_file"
    fi

    if [ "$needs_setup" = false ]; then
        echo -e "${GREEN}✅ $env_file already configured.${NC}"
        return
    fi

    echo ""
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}  Setting up environment for: ${CYAN}$dir${NC}"
    echo -e "${BLUE}  Press ENTER to keep the value shown in [brackets].${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
    echo ""

    # Build a temp file so we overwrite cleanly
    local tmp_file="${env_file}.tmp"
    > "$tmp_file"

    while IFS= read -r line || [ -n "$line" ]; do
        # Preserve blank lines
        if [[ -z "$line" ]]; then
            echo "" >> "$tmp_file"
            continue
        fi

        # Preserve comments
        if [[ "$line" =~ ^# ]]; then
            echo -e "${YELLOW}  $line${NC}"
            echo "$line" >> "$tmp_file"
            continue
        fi

        key=$(echo "$line" | cut -d '=' -f 1)
        example_val=$(echo "$line" | cut -d '=' -f 2-)

        [ -z "$key" ] && continue

        # Use existing .env value as default if available
        existing_val=""
        if [ -f "$env_file" ]; then
            existing_val=$(grep "^${key}=" "$env_file" 2>/dev/null | cut -d '=' -f 2-)
        fi
        default_val="${existing_val:-$example_val}"

        printf "  🔹 %-35s [${CYAN}%s${NC}]: " "$key" "$default_val"
        read -r user_val < /dev/tty

        if [ -z "$user_val" ]; then
            echo "$key=$default_val" >> "$tmp_file"
        else
            echo "$key=$user_val" >> "$tmp_file"
        fi

    done < "$example_file"

    mv "$tmp_file" "$env_file"
    echo ""
    echo -e "${GREEN}✅ $env_file saved!${NC}"
    echo ""
}

# ─────────────────────────────────────────────────────────────────────────────
# PRE-FLIGHT CHECKS
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BLUE}🚀 AI Instructional Design System — up${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo ""

echo "🔍 Checking system dependencies..."

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ python3 is not installed.${NC}"
    echo "   Run: sudo apt update && sudo apt install -y python3 python3-venv"
    exit 1
fi
echo -e "   ${GREEN}✓ Python3 found: $(python3 --version)${NC}"

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ npm / Node.js is not installed.${NC}"
    echo "   Run the following commands to install on Ubuntu/AWS:"
    echo "   curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "   sudo apt-get install -y nodejs"
    exit 1
fi
echo -e "   ${GREEN}✓ Node.js found: $(node --version) | npm: $(npm --version)${NC}"
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# AUTO-DETECT PUBLIC IP (used to suggest correct VITE_API_URL)
# ─────────────────────────────────────────────────────────────────────────────
PUBLIC_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || echo "")
if [ -n "$PUBLIC_IP" ]; then
    # Temporarily patch the frontend .env.example default to show the real IP
    sed -i.bak "s|VITE_API_URL=.*|VITE_API_URL=http://$PUBLIC_IP:8000/api|" "$FRONTEND_DIR/.env.example" 2>/dev/null || true
fi

# ─────────────────────────────────────────────────────────────────────────────
# ENV SETUP — ALWAYS RUN (will skip fields already filled in)
# ─────────────────────────────────────────────────────────────────────────────
setup_env "$BACKEND_DIR"
setup_env "$FRONTEND_DIR"

# Restore .env.example to its original localhost default after setup
if [ -f "$FRONTEND_DIR/.env.example.bak" ]; then
    mv "$FRONTEND_DIR/.env.example.bak" "$FRONTEND_DIR/.env.example"
fi

# ─────────────────────────────────────────────────────────────────────────────
# VALIDATE DATABASE_URL before booting backend
# ─────────────────────────────────────────────────────────────────────────────
DB_URL=$(grep "^DATABASE_URL=" "$BACKEND_DIR/.env" 2>/dev/null | cut -d '=' -f 2-)
if [ -z "$DB_URL" ] || [[ "$DB_URL" == *"your_"* ]] || [[ "$DB_URL" == *"password@localhost"* && "$DB_URL" == *"root:password"* ]]; then
    echo -e "${YELLOW}⚠️  WARNING: DATABASE_URL looks like it may still be a placeholder.${NC}"
    echo -e "   Current value: ${CYAN}$DB_URL${NC}"
    echo ""
    echo "   For a quick local test, use: sqlite:///./test.db"
    printf "   Re-enter DATABASE_URL (or press ENTER to continue anyway): "
    read -r new_db < /dev/tty
    if [ -n "$new_db" ]; then
        # Update the value in .env
        sed -i "s|^DATABASE_URL=.*|DATABASE_URL=$new_db|" "$BACKEND_DIR/.env"
        echo -e "${GREEN}   ✅ DATABASE_URL updated.${NC}"
    fi
    echo ""
fi

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND SETUP & LAUNCH
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}📡 Setting up Backend (FastAPI)...${NC}"
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    echo "📥 Installing Python dependencies..."
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
else
    source venv/bin/activate
fi

echo "🚀 Launching FastAPI on 0.0.0.0:8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# ─────────────────────────────────────────────────────────────────────────────
# FRONTEND SETUP & LAUNCH
# ─────────────────────────────────────────────────────────────────────────────
echo -e "${BLUE}💻 Setting up Frontend (Vite/React)...${NC}"
cd "$FRONTEND_DIR"

if [ ! -d "node_modules" ]; then
    echo "📦 Installing npm dependencies (this may take a minute)..."
    npm install --silent
fi

echo "🚀 Launching Vite on 0.0.0.0:5173..."
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
cd ..

# ─────────────────────────────────────────────────────────────────────────────
# SHOW ACCESS URLs
# ─────────────────────────────────────────────────────────────────────────────
PUBLIC_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || echo "YOUR_SERVER_IP")

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ System is ing!${NC}"
echo -e "   ${CYAN}📡 Backend API : http://$PUBLIC_IP:8000${NC}"
echo -e "   ${CYAN}💻 Frontend UI : http://$PUBLIC_IP:5173${NC}"
echo -e "   ${CYAN}📖 API Docs    : http://$PUBLIC_IP:8000/docs${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}💡 AWS Tip: Make sure ports 8000 & 5173 are open in your Security Group.${NC}"
echo ""
echo "   Press Ctrl+C to stop all services."
echo ""

wait
