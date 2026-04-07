# 🛠️ Technical Documentation
## AI Instructional Design System — v3.0

> **Audience:** Developers, DevOps, and Technical Administrators  
> **Last Updated:** April 2026

---

## Table of Contents

1. [System Architecture](#1-system-architecture)
2. [Project Structure](#2-project-structure)
3. [Database Schema](#3-database-schema)
4. [API Reference](#4-api-reference)
5. [AI Generation Pipeline](#5-ai-generation-pipeline)
6. [Interactivity Level System](#6-interactivity-level-system)
7. [Environment Variables](#7-environment-variables)
8. [AWS Deployment Guide](#8-aws-deployment-guide)
9. [PM2 Process Management](#9-pm2-process-management)
10. [Troubleshooting Reference](#10-troubleshooting-reference)

---

## 1. System Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│  CLIENT (Browser)                                                    │
│  Vite + React SPA  ·  Port 5173                                      │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTP (REST)
                             ▼
┌──────────────────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI)   ·  Port 8000                                    │
│                                                                      │
│  Routers: auth · intake · design · storyboard                        │
│           edit · export · extraction · files · folders               │
│                                                                      │
│  Services:                                                           │
│   ┌─────────────────────┐    ┌───────────────────────────────────┐   │
│   │  ai_generation.py   │    │  ai_editing.py                    │   │
│   │                     │    │                                   │   │
│   │  Phase 1: Header    │    │  Document polish, minor edits,    │   │
│   │  Phase 2: Row Loop  │    │  file beautification (XLSX/PPTX)  │   │
│   │  Phase 3: Footer    │    │                                   │   │
│   └──────────┬──────────┘    └─────────────────┬─────────────────┘   │
└──────────────┼───────────────────────────────── ┼───────────────────┘
               │                                  │
      ┌────────▼──────────┐             ┌──────────▼──────────────┐
      │   GROQ API        │             │   PICO LLM API          │
      │  (Primary LLM)    │  fallback → │   (Fallback LLM)        │
      │  llama-3.1-8b     │             │  backend.buildpicoapps  │
      └───────────────────┘             └─────────────────────────┘
               │
      ┌────────▼──────────────────────────────────────────────────┐
      │  DATABASE (SQLAlchemy)                                     │
      │  AWS RDS MySQL  —  or—  Local SQLite (dev/test)           │
      │  Tables: users · projects · chat_messages                  │
      │          folders · user_files                              │
      └───────────────────────────────────────────────────────────┘
```

### Key Design Principles
- **Zero-Truncation**: Storyboards and Design Docs are generated in **parallel API loops** — one call per module row — so the model can never "run out of budget" mid-table.
- **Fault Tolerant**: Every LLM call has an automatic `try → Groq → except → Pico` fallback pattern.
- **Persistent Storage**: All generated content (Design Docs, Storyboards) is stored as `LONGTEXT` in MySQL so nothing is lost on page refresh.

---

## 2. Project Structure

```
instructional_ai_system/
├── start.sh                      # Interactive startup script (local + AWS)
├── README.md                     # Project overview
├── docs/
│   ├── TECHNICAL.md              # This file
│   └── USER_GUIDE.md             # End-user documentation
│
├── backend/
│   ├── .env                      # Secret keys (not committed to git)
│   ├── .env.example              # Template for .env setup
│   ├── requirements.txt          # Python dependencies
│   └── app/
│       ├── main.py               # FastAPI app entrypoint, CORS config
│       ├── database.py           # SQLAlchemy engine setup
│       ├── models.py             # ORM table definitions
│       ├── schemas.py            # Pydantic request/response models
│       ├── auth.py               # JWT token utilities
│       ├── dependencies.py       # Shared FastAPI dependencies (get_db, get_user)
│       ├── routers/
│       │   ├── auth.py           # POST /register, /login, /me
│       │   ├── intake.py         # POST/GET project intake forms
│       │   ├── design.py         # POST /design/{id}/generate
│       │   ├── storyboard.py     # POST /storyboard/{id}/generate
│       │   ├── edit.py           # POST /edit/{id}/design, /edit/{id}/storyboard
│       │   ├── export.py         # GET /export/{id}/design, /export/{id}/storyboard
│       │   ├── extraction.py     # POST /extract (file → text pipeline)
│       │   ├── files.py          # File library management
│       │   ├── folders.py        # Folder management
│       │   └── history.py        # Chat history for AI edits
│       └── services/
│           ├── ai_generation.py  # Core AI engine (3-phase loop + fallback)
│           └── ai_editing.py     # Document editing & beautification
│
└── frontend_react/
    ├── .env                      # VITE_API_URL (not committed to git)
    ├── .env.example              # Template for frontend .env
    ├── src/
    │   ├── api.js                # Central Axios instance (reads VITE_API_URL)
    │   ├── components/
    │   │   └── ProjectView.jsx   # Main project workspace UI
    │   └── ...
    └── ...
```

---

## 3. Database Schema

All tables are created automatically on first boot via `models.Base.metadata.create_all(bind=engine)`.

### `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INT (PK) | Auto-increment |
| `name` | VARCHAR(100) | Full name |
| `email` | VARCHAR(100) | Unique, used as login |
| `hashed_password` | VARCHAR(255) | bcrypt hashed |
| `created_at` | DATETIME | Server default: `NOW()` |

### `projects`
| Column | Type | Notes |
|--------|------|-------|
| `id` | VARCHAR(36) (PK) | UUID string |
| `user_id` | INT (FK → users) | Owner |
| `title` | VARCHAR(255) | Course title |
| `business_unit` | VARCHAR(150) | Optional |
| `intake_data` | LONGTEXT | JSON-serialized intake form fields |
| `extracted_content` | LONGTEXT | Raw text extracted from uploaded files |
| `design_doc` | LONGTEXT | Full generated Markdown Design Document |
| `storyboard` | LONGTEXT | Full generated Markdown Storyboard |
| `created_at` | DATETIME | Server default |
| `updated_at` | DATETIME | Auto-updated on change |

### `chat_messages`
| Column | Type | Notes |
|--------|------|-------|
| `id` | INT (PK) | Auto-increment |
| `project_id` | VARCHAR(36) (FK → projects) | |
| `type` | VARCHAR(50) | `"design"` or `"storyboard"` |
| `role` | VARCHAR(50) | `"user"` or `"assistant"` |
| `content` | LONGTEXT | Full message body |
| `timestamp` | DATETIME | Server default |

### `folders` and `user_files`
Hierarchical file library. Folders support nesting via `parent_id` self-reference. `user_files` holds references to uploaded source files.

---

## 4. API Reference

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create a new user account |
| POST | `/api/auth/login` | Returns JWT access token |
| GET | `/api/auth/me` | Get current authenticated user |

### Intake
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/intake/` | Create or update intake for a project |
| GET | `/api/intake/{project_id}` | Retrieve current intake fields |

### Content Extraction
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/extract/` | Upload file (PDF, PPTX, XLSX, DOCX) → extract raw text |

### Design Document
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/design/{project_id}/generate` | Run the 3-phase AI design document generator |
| GET | `/api/design/{project_id}` | Retrieve current stored design document |

### Storyboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/storyboard/{project_id}/generate?storyboard_type=Type 1` | Generate per-module storyboard |
| GET | `/api/storyboard/{project_id}` | Retrieve current stored storyboard |

### Editing
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/edit/{project_id}/design` | Edit design doc based on user instruction |
| POST | `/api/edit/{project_id}/storyboard` | Edit storyboard based on user instruction |

### Export
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/{project_id}/design` | Download design doc as `.md` file |
| GET | `/api/export/{project_id}/storyboard` | Download storyboard as `.md` file |

All endpoints (except `/api/auth/register` and `/api/auth/login`) require `Authorization: Bearer <token>` header.

---

## 5. AI Generation Pipeline

### Design Document (3-Phase Multi-Call Architecture)

The design document generator is the most critical component. It avoids the "5-module ceiling" seen with naive single-prompt approaches by splitting generation across many focused API calls.

```
generate_design_document(api_key, intake_data, content)
    │
    ├─► PHASE 1: Header
    │   └─ One LLM call → Sections 1-3 (Project Info, Overview, Objectives)
    │      max_tokens: 1,000
    │
    ├─► PHASE 2: Module Row Loop  ← The key innovation
    │   └─ for i in range(1, num_modules + 1):
    │         _generate_module_row(client, i, m_count, ...)
    │         │  One focused LLM call per module row
    │         │  max_tokens: 800 per row
    │         │  2-second delay between calls (rate limit protection)
    │         └─ Cleaned, validated, appended to table
    │
    └─► PHASE 3: Footer
        └─ One LLM call → Sections 5-7 (Strategy, Assessment, Technical Specs)
           max_tokens: 600
```

**Total API calls for a 9-module course:** `1 (header) + 9 (rows) + 1 (footer) = 11 calls`  
**Estimated generation time:** ~25–40 seconds

### Storyboard Generation

```
generate_storyboard(api_key, design_doc, intake_data, content, storyboard_type)
    │
    └─► for i in range(1, num_modules + 1):
           _call_module_with_retry(generate_fn, ...)
           │  └─ @retry(attempts=5, exponential_backoff)
           │     _generate_single_module_type1 OR _generate_single_module_type2
           │     max_tokens: 8,000 per module
           │     3-second delay between modules
           └─ fix_markdown_tables(module_content) applied to each result
```

### Dual-Provider Fallback

Every LLM call follows this exact pattern:

```python
def _llm_call(client, system_content, prompt, max_tokens):
    try:
        # 1. Attempt with Groq (fast, free tier)
        response = client.chat.completions.create(...)
        return response.choices[0].message.content
    except Exception as groq_error:
        # 2. Groq failed (413, rate limit, timeout) → silently switch to Pico
        print(f"Groq failed, switching to Pico: {groq_error}")
        return _call_pico_llm(prompt, system_content)
```

The `413 "Request too large"` errors you see in PM2 logs are completely handled. They are informational — the Pico call immediately follows and completes the generation.

### Markdown Table Post-Processor (`fix_markdown_tables`)

AI models frequently break markdown table formatting by:
- Adding `##` heading markers before pipe rows
- Wrapping `**bold**` around entire rows
- Splitting a single cell value across two lines

The post-processor runs two passes on every storyboard module output:
1. **Pass 1 – Normalize**: Strips heading markers and bold wrappers from table lines.
2. **Pass 2 – Reconstruct**: Detects "continuation rows" (lines that split from the previous cell) and merges them onto the correct parent row using `<br>`.

---

## 6. Interactivity Level System

Interactivity level is set during intake and controls which strategies are injected into the AI prompt.

| Level | Visual Strategies | Interaction Types | Assessment Types |
|-------|------------------|-------------------|-----------------|
| **Level 1** | Icons, infographics, charts, process diagrams | Click-reveal, tabs, accordion, hotspots | MCQ, True/False, Fill-in-blank, Matching |
| **Level 2** | + Characters, before/after, demo videos, animations | + News incidents, mini case studies, decision points | + Scenario MCQ, sequencing, drag-and-drop |
| **Level 3** | + Realistic scenarios, complex simulations, branching visuals | + Branching scenarios, software simulation, role simulation | + Branching scenario assessments, simulation-based |

If no level is provided, the system defaults to **Level 2**.

---

## 7. Environment Variables

### `backend/.env`

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `GROQ_API_KEY` | ✅ Yes | `gsk_abc123...` | From console.groq.com |
| `DATABASE_URL` | ✅ Yes | `mysql+pymysql://admin:pass@rds-endpoint:3306/idtool-db` | Or `sqlite:///./test.db` for local |
| `SECRET_KEY` | ✅ Yes | `a-long-random-string` | Used for JWT signing. Run `openssl rand -hex 32` to generate |
| `ALGORITHM` | ✅ Yes | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | `1440` | Default: 24 hours |
| `MAIL_USERNAME` | Optional | `you@gmail.com` | SMTP sender for email features |
| `MAIL_PASSWORD` | Optional | `your-app-password` | Gmail App Password (not your login password) |
| `MAIL_FROM` | Optional | `you@gmail.com` | Displayed sender address |
| `MAIL_PORT` | Optional | `587` | SMTP port |
| `MAIL_SERVER` | Optional | `smtp.gmail.com` | SMTP host |

### `frontend_react/.env`

| Variable | Required | Example | Notes |
|----------|----------|---------|-------|
| `VITE_API_URL` | ✅ Yes | `http://34.203.223.159:8000/api` | Must end with `/api`. Must be the public IP of your EC2 backend. |

---

## 8. AWS Deployment Guide

### Infrastructure Requirements

| Resource | Minimum Spec | Recommended |
|----------|-------------|-------------|
| EC2 Instance | `t3.micro` | `t3.small` |
| OS | Ubuntu 24.04 LTS | Ubuntu 24.04 LTS |
| RDS | `db.t3.micro` MySQL 8.0 | `db.t3.small` |

### Security Group Configuration

**EC2 Security Group (Inbound):**
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 22 | TCP | Your IP | SSH access |
| 8000 | TCP | 0.0.0.0/0 | FastAPI backend |
| 5173 | TCP | 0.0.0.0/0 | Vite frontend |

**RDS Security Group (Inbound):**
| Port | Protocol | Source | Purpose |
|------|----------|--------|---------|
| 3306 | TCP | **EC2 Security Group ID** (e.g. `sg-0abc123`) | MySQL access — never use 0.0.0.0/0 |

### First-Time Database Setup

After RDS is provisioned and the Security Group is correctly configured:
```bash
# Install MySQL client
sudo apt install mysql-client-core-8.0 -y

# Connect to RDS
mysql -h your-rds-endpoint.rds.amazonaws.com -u admin -p

# Inside the MySQL prompt:
CREATE DATABASE `idtool-db`;
SHOW DATABASES;  -- verify
EXIT;
```

### Node.js Installation (Required on Fresh EC2)
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
node -v && npm -v  # Verify
```

### Starting the App for the First Time
```bash
cd ~/elearningAI/instructional_ai_system
./start.sh
# The interactive wizard will ask for all .env values
```

---

## 9. PM2 Process Management

### Starting Services Persistently

```bash
# Backend
cd ~/elearningAI/instructional_ai_system/backend
pm2 start "venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000" --name idtool-backend

# Frontend
cd ~/elearningAI/instructional_ai_system/frontend_react
pm2 start "npm run dev -- --host 0.0.0.0" --name idtool-frontend

# Save processes to survive server reboot
pm2 save
pm2 startup  # Follow the output instructions
```

### Managing Processes

| Command | Action |
|---------|--------|
| `pm2 list` | Show all running processes and their status |
| `pm2 logs` | Stream live logs from all processes |
| `pm2 logs idtool-backend` | Stream backend logs only |
| `pm2 logs idtool-backend --lines 200` | Last 200 lines of backend logs |
| `pm2 restart idtool-backend` | Restart the backend without downtime |
| `pm2 stop all` | Stop everything |
| `pm2 delete all` | Remove all processes from PM2 list |
| `pm2 flush` | Clear all stored log files |

---

## 10. Troubleshooting Reference

| Error | Cause | Solution |
|-------|-------|----------|
| `Could not parse SQLAlchemy URL` | `DATABASE_URL` is empty or malformed in `backend/.env` | Check the format: `mysql+pymysql://user:pass@host:port/db` or use `sqlite:///./test.db` |
| `Unknown database 'idtool-db'` | Database container does not exist on the RDS server | Connect via `mysql` CLI and run `CREATE DATABASE \`idtool-db\`;` |
| MySQL connection hangs indefinitely | RDS Security Group does not allow port 3306 from the EC2 | Add an inbound rule to the RDS Security Group: port 3306, source = EC2 Security Group ID |
| `npm: command not found` | Node.js is not installed on EC2 | Install using the `nodesource` script (see Section 8) |
| `strategies is not defined` | `get_strategy_for_level()` call was accidentally removed | It must be called before building the AI prompt inside `generate_design_document()` |
| Groq 413 error in logs | Request too large for Groq free tier (6,000 TPM) | **This is handled automatically.** Pico fallback completes the request. No action needed. |
| Storyboard stops at 5 modules | Model hits response budget in a single call | Resolved in v3.0 by the per-module row loop in `generate_design_document`. |
| Frontend shows blank page | `VITE_API_URL` is wrong or backend is not running | Check PM2 (`pm2 list`), verify the IP in `frontend_react/.env`, ensure port 8000 is open in EC2 Security Group |
