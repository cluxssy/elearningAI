# 📖 User Guide
## AI Instructional Design Tool — v3.0

> **Audience:** Instructional Designers and Learning Content Creators  
> **Last Updated:** April 2026

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Creating a New Project](#2-creating-a-new-project)
3. [Uploading Source Content](#3-uploading-source-content)
4. [Filling in the Intake Form](#4-filling-in-the-intake-form)
5. [Generating the Design Document](#5-generating-the-design-document)
6. [Generating the Storyboard](#6-generating-the-storyboard)
7. [Editing AI-Generated Content](#7-editing-ai-generated-content)
8. [Exporting Your Work](#8-exporting-your-work)
9. [Tips for High-Quality Output](#9-tips-for-high-quality-output)
10. [Understanding Interactivity Levels](#10-understanding-interactivity-levels)
11. [Common Questions](#11-common-questions)

---

## 1. Getting Started

Open your browser and navigate to the application URL:

- **On AWS:** `http://[your-server-ip]:5173`
- **Local:** `http://localhost:5173`

**Create an Account** (first time only):
1. Click **Sign Up** on the login page.
2. Enter your full name, email address, and a password.
3. Click **Register** — you will be logged in immediately.

On subsequent visits, use **Log In** with your email and password.

---

## 2. Creating a New Project

1. On your **Dashboard**, click the **+ New Project** button.
2. Give it a name (usually the course title).
3. The system creates a unique project workspace — this is where all your documents for this course will live.
4. Click on the project to open its **workspace**.

> 💡 Your projects are saved automatically. You can close the browser and return later — everything will be exactly where you left it.

---

## 3. Uploading Source Content

The AI uses your source material to generate **specific, accurate** content instead of generic filler text. The richer your source content, the better the output.

**Supported Formats:**
- 📄 PDF documents
- 📊 PowerPoint (`.pptx`)
- 📑 Word documents (`.docx`)
- 📋 Excel spreadsheets (`.xlsx`)
- ✍️ Plain text (paste directly)

**How to Upload:**
1. In the project workspace, find the **"Content"** or **"Upload"** section.
2. Drag-and-drop your file or click to browse.
3. Click **"Extract"** — the system will read your file and convert it to AI-ready text.
4. Review the extracted text and remove any irrelevant sections (headers, footers, page numbers) for cleaner output.

> ⚠️ **Tip:** The more specific your source material, the less generic the AI's output. A 20-page SME document will produce far better results than a 2-paragraph synopsis.

---

## 4. Filling in the Intake Form

The Intake Form is the project brief for the AI. Think of it as the project kickoff document you would normally send to an SME.

### Required Fields

| Field | What to Enter | Example |
|-------|--------------|---------|
| **Course Title** | Full official name of the course | *"Anti-Money Laundering for Branch Staff"* |
| **Business Unit** | The department requesting the training | *"Compliance & Risk"* |
| **Course Type** | The format of delivery | *"Self-paced eLearning"* |
| **Target Audience** | Who will take this course? | *"Front-line branch staff with 1–3 years experience"* |
| **Experience Level** | Learner familiarity with the topic | *"Beginner — No prior AML training"* |
| **Number of Modules** | How many modules you need | `9` |
| **Interactivity Level** | See Section 10 for guidance | *"Level 2 — Engaging"* |

### Learning Objectives
Enter **3 specific learning objectives** using strong action verbs.

❌ **Avoid:** *"Learners will understand AML regulations"*  
✅ **Use:** *"Apply a 3-step process to report suspicious transactions to the compliance team"*

Strong verbs to use: *Apply, Identify, Analyse, Differentiate, Evaluate, Demonstrate, Construct, Classify*

---

## 5. Generating the Design Document

The Design Document (DD) is the master blueprint: module breakdown, learning objectives per module, recommended strategies, and assessment methods — all in one professional table.

### Step-by-Step

1. Ensure your **Intake Form is complete** and **Source Content is uploaded**.
2. Click the **"Generate Design Document"** button.
3. Wait for generation to complete.
   - For **9 modules**: expect **25–40 seconds** (the system makes 11 focused API calls — one per section, one per module row).
4. Your Design Document appears in the editor.

### What the AI Generates

- ✅ **Project Information** — Title, business unit, audience, date
- ✅ **Course Overview** — Context, goals, estimated duration
- ✅ **Learning Objectives** — Your objectives, formatted professionally
- ✅ **Module Breakdown Table** — One row per module with: delivery mode, objectives, topics, strategies, activities, duration
- ✅ **Knowledge Check row** — Auto-appended with MCQ/scenario assessment details
- ✅ **Summary & Conclusion row** — Certificate and recap activity
- ✅ **Instructional Strategy** — Pedagogy and media approach based on your interactivity level
- ✅ **Assessment Strategy** — Formative, summative, and pass criteria
- ✅ **Technical Specifications** — LMS compatibility, devices, authoring tools

> ⚠️ **Why it takes longer for many modules:** The system generates each module row as a **separate, dedicated call** to the AI. This is intentional — it ensures that row 8 gets the same attention as row 1, and no modules are ever skipped or truncated.

---

## 6. Generating the Storyboard

The Storyboard transforms the Design Document into a detailed, screen-by-screen production script ready for a developer to build in Storyline or Rise.

### Step-by-Step

1. You must have a **Design Document generated first** — the AI uses it to source module titles and topics.
2. Choose your Storyboard format:
   - **Type 1 (Full Screen):** Traditional format. Each screen gets its own section with a title, OST table, narration, and visual notes.
   - **Type 2 (Tabular):** A condensed 7-column table per module. Better for quick stakeholder reviews.
3. Click **"Generate Storyboard"**.
4. The system generates **one module at a time** with a short delay between each to manage API limits.
   - For a 9-module course: expect **3–5 minutes**.

### What Each Module Contains

**Type 1 (Per Screen):**
- Screen number (e.g. `Screen 3.4`)
- On-Screen Text (OST) with 3–5 bullet points
- Full audio narration script (5–8 sentences)
- Visual/developer notes

**Type 2 (Tabular):**
| Section | Topics | Visual Instructions | On-Screen Text | Audio Narration | Status | Actions |
|---------|--------|---------------------|----------------|-----------------|--------|---------|

---

## 7. Editing AI-Generated Content

Both the Design Document and Storyboard have an **AI chat editor** integrated directly into the workspace.

### How to Use

1. In the document view, type a natural language instruction into the chat box:
   - *"Make the strategy for Module 3 focus more on case studies"*
   - *"Rewrite the narration for Screen 2.3 to be more formal"*
   - *"Add a scenario-based interaction to Module 5"*
2. Click **Send** — the AI will edit only the relevant section and return the updated document.
3. Your edit history is saved so you can review what changed.

> 💡 **Tip:** Be specific. "Make it better" gives the AI too much freedom. "Rewrite Module 2's strategy to use a problem-solution approach targeting compliance managers" produces a precise, high-quality result.

---

## 8. Exporting Your Work

Once you are happy with the generated content:

| Export Option | Best For | How to Use |
|--------------|---------|------------|
| **Download Markdown** | Archiving, future AI edits, technical handoff | Click "Export" → "Download .md" |
| **Print / Save as PDF** | Stakeholder review, sign-off, email attachments | Use your browser's `Ctrl+P` / `Cmd+P` → "Save as PDF" |
| **Copy to Clipboard** | Quick paste into Word or PowerPoint for manual formatting | Click "Copy" icon in the toolbar |

---

## 9. Tips for High-Quality Output

### Write Specific Learning Objectives
The AI mirrors the quality of your objectives. If you provide precise, behaviour-based objectives, every module row will be specific and measurable.

### Use Real Source Material
Upload the actual SME document, compliance policy, or SOPs — not a summary. The AI extracts real terminology, processes, and context from your files.

### Choose the Right Interactivity Level
- **Brand new topic for all learners?** → Level 1 (clear, simple, knowledge-focused)
- **Compliance or process training?** → Level 2 (scenarios and decision points)
- **Skill/performance training?** → Level 3 (simulations and branching)

### Review the Module Table First
Before generating the storyboard, read through the Design Document module table. If a module title or topic looks off, edit it first — the storyboard AI reads the DD to get its content direction.

---

## 10. Understanding Interactivity Levels

The interactivity level you choose in the intake form determines which visual and interaction strategies the AI recommends across the entire course.

### Level 1 — Awareness
Best for: Policy acknowledgements, general awareness campaigns  
Visual: Icons, infographics, charts, process diagrams  
Interactions: Click-reveal, tabs, accordion, hotspots  
Assessments: Multiple choice, True/False, Fill-in-blank, Matching

### Level 2 — Engaging ⭐ (Most Common)
Best for: Compliance training, onboarding, process training  
Adds: Character illustrations, demo videos, animations, before/after comparisons  
Adds: News incidents, mini case studies, decision points  
Adds: Scenario-based MCQs, drag-and-drop, sequencing

### Level 3 — Applied / Simulation
Best for: Sales skills, customer handling, technical procedures  
Adds: Realistic branching scenarios, software simulations, role-play  
Adds: Show-me / Try-me simulations  
Adds: Simulation-based performance assessments, branching scenario scoring

If unsure which to use, **Level 2** is the professional standard for most workplace eLearning projects.

---

## 11. Common Questions

**Q: My generation seems to be taking a long time. Is it stuck?**  
A: No — for 9 modules, the system makes 11 separate AI requests. This is normal and takes 25–40 seconds for Design Documents and 3–5 minutes for Storyboards. Do not refresh the page.

**Q: I saw an error mentioning "Groq" in the logs. Should I be worried?**  
A: No. The system automatically switches to a backup AI provider (Pico) when Groq's free tier limit is reached. Your generation completes successfully. The warning is informational only.

**Q: Can I regenerate just one module?**  
A: Not yet — the current version regenerates the full document. Use the AI chat editor to make targeted changes to specific sections instead.

**Q: Why did only 5 modules generate when I requested 9?**  
A: This was a known issue in earlier versions. Version 3.0 of this tool resolves it permanently by generating each module row as a separate AI call. If you're on v3.0 and still see this, try regenerating — the system has automatic retry logic built in.

**Q: Is my data secure?**  
A: Your documents are stored on your private AWS RDS database. No data is permanently retained by the AI providers (Groq, Pico). Ensure your RDS Security Group does not expose port 3306 to the public internet.

**Q: Can I share a project with a colleague?**  
A: Not in the current version — projects are tied to individual user accounts. Export the document as a PDF or Markdown file and share that instead.
