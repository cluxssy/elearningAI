# AI Instructional Design Automation System

## Overview
A full-stack, scalable application for automating the creation of Instructional Design documents (Design Docs and Storyboards). Built with FastAPI, MySQL, and Vanilla JS/HTML/CSS.

## Project Structure
```text
instructional_ai_system/
├── backend/          # FastAPI server, SQLAlchemy models, API endpoints
└── frontend/         # Vanilla JS, HTML, CSS UI
```

## Setup Instructions

### 1. Database Configuration
1. Install and start MySQL server.
2. Create a generic database:
   ```sql
   CREATE DATABASE instructional_ai;
   ```

### 2. Backend Setup
1. Open a terminal and navigate to the `backend` directory:
   ```bash
   cd instructional_ai_system/backend
   ```
2. Create and activate a Python virtual environment:
   - **Windows:** `python -m venv venv` and `.\venv\Scripts\activate`
   - **macOS/Linux:** `python3 -m venv venv` and `source venv/bin/activate`
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file from the provided `.env` format:
   ```env
   GROQ_API_KEY=your_groq_api_key_here
   DATABASE_URL=mysql+pymysql://root:@localhost:3306/instructional_ai
   SECRET_KEY=generate_a_random_character_string_here_like_using_openssl
   ALGORITHM=HS256
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ```
5. Run the server (will automatically create database tables):
   ```bash
   uvicorn app.main:app --reload
   ```
   - The API will be available at `http://localhost:8000`
   - Interactive API docs at `http://localhost:8000/docs`

### 3. Frontend Setup
1. Standard React application.
2. Navigate to `frontend_react`:
   ```bash
   cd instructional_ai_system/frontend_react
   ```
3. Install dependencies:
   ```bash
   npm install
   ```
4. Run in development mode:
   ```bash
   npm run dev
   ```
5. Open `http://localhost:5173` to begin.

## Architecture & Infrastructure

### Technical Stack
- **Frontend**: React (Vite) with Vanilla CSS (Glassmorphic Design).
- **Backend**: FastAPI (Python) for high-performance asynchronous API handling.
- **Database**: MySQL (relational storage for projects, folders, and documents).
- **AI Engine**: Groq (Llama 3 models) for ultra-fast document generation and editing.

### AI Infrastructure & Tools
1. **Groq Cloud (LLM Provider)**:
   - **Role**: Primary engine for all AI generations and "Surgical Edits".
   - **Models Used**: `llama-3.3-70b-versatile` (Large-scale generation) and `llama-3.1-8b-instant` (Fast classification).
   - **Pricing**: Pay-as-you-go based on tokens. Has a generous free tier for developers. Check [Groq Pricing](https://groq.com/pricing/) for enterprise details.
   - **API Key**: Required in `.env` as `GROQ_API_KEY`.

2. **PicoApps LLM API**:
   - **Role**: Secondary fallback / specialized utility for intent classification and quick chat responses.
   - **Infrastructure**: Handles fast, stateless LLM requests. Currently free-to-use endpoint integrated into `ai_editing.py`.

### Pricing & Scalability Notes
- **Hosting**: The system is self-hosted (FastAPI + MySQL). Costs depend on your cloud provider (AWS, Azure, Vercel, etc.).
- **AI Costs**: Groq is significantly cheaper and faster than GPT-4, offering "Instant" generation speeds (300+ tokens/sec). For high-volume enterprise use, a paid Groq production tier is recommended.
- **Security**: All API keys are stored server-side in `.env`, never exposed to the frontend.
# 🎓 AI Instructional Design Tool (AWS / Production)

This is a professional-grade AI tool for instructional designers. It converts raw project data into comprehensive **Design Documents** and detailed **Tabular Storyboards**.

## 🚀 Deployment (AWS / Persistence)

The project is configured for **EC2 / RDS** and runs persistently using **PM2**.

| Command | Action |
|---------|--------|
| `./start.sh` | Setup .env interactively & launch both services locally |
| `pm2 status` | Check status of persistent processes |
| `pm2 logs` | View generation logs and fallback success |

## 📁 Key Documentation

| Document | Purpose |
|----------|---------|
| [📖 User Guide](./docs/USER_GUIDE.md) | For Instructional Designers: How to use the app to generate 9 modules. |
| [🛠️ Technical Specs](./docs/TECHNICAL.md) | For Developers: Architecture, AI fallback logic, and token limits. |

## 🌟 Enhanced Intelligence Features

- **9-Module Persistence**: Never skips table rows, even for large courses.
- **Extreme Detail Mode**: Unlocks up to **40,000 characters** of processing context.
- **Zero-Failure AI**: Automatically switches from **Groq (Fast)** to **Pico (Stable)** if the request is too large.
- **Smart Formatting**: Post-processes AI tables to ensure clean Markdown/Tabular export.
