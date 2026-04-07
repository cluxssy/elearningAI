"""
StoryBoard AI — Document Editing Engine v4
==========================================
- Structural cell navigation (no search/replace guessing)
- Bulk edits: "change all OSTs in module 1"
- Hallucination detection
- Word-level diff for track changes
- Selection-aware: accepts selected_text + screen_num + col_index from frontend
- Intent classifier won't fire on casual messages
"""

import json, re, os, difflib
from typing import List, Dict, Tuple
import requests

# ─────────────────────────────────────────────────────────────
# 1. Document Parsing
# ─────────────────────────────────────────────────────────────

def parse_document_into_sections(doc: str) -> List[Dict]:
    sections, lines, current_raw = [], doc.split("\n"), []
    # Support Markdown headers (# Module, ## Screen, etc.) and optional whitespace
    screen_re = re.compile(r"^\s*\**\s*#*\s*(Screen\s+(\d+(?:\.\d+)*)\s*(?:Title\s*)?[:\-|]\s*(.*))\**", re.IGNORECASE)
    module_re = re.compile(r"^\s*#*\s*(Module\s+(\d+|[A-Z]):\s+.*)", re.IGNORECASE)
    i = 0
    while i < len(lines):
        m_screen = screen_re.match(lines[i])
        m_module = module_re.match(lines[i])
        
        if m_screen or m_module:
            if current_raw:
                sections.append({"type": "raw", "content": "\n".join(current_raw)})
                current_raw = []
            
            title_line = lines[i]
            if m_screen:
                # Capture the full label but also the clean ID (e.g. 1.1)
                full_label, target_id = m_screen.group(1), m_screen.group(2)
                type_name = "screen"
            else:
                # Capture the full label (e.g. Module 1: Intro)
                full_label = m_module.group(1)
                # Strip leading # and whitespace for the ID
                target_id = full_label.strip("# ").split(":", 1)[0].strip()
                type_name = "module"
                
            i += 1
            table_lines = []
            while i < len(lines):
                # Peak ahead to stop at next header
                next_line = lines[i].strip()
                if screen_re.match(next_line) or module_re.match(next_line): break
                table_lines.append(lines[i])
                i += 1
            
            sections.append({
                "type": type_name, 
                "id": target_id,
                "title_line": title_line, 
                "table_lines": table_lines
            })
        elif lines[i].strip().startswith("|") and (i+1 < len(lines) and re.match(r"^|[\s\-:|]+\|$", lines[i+1].strip())):
            # This is a standalone table (not under a specific Screen/Module heading)
            if current_raw:
                sections.append({"type": "raw", "content": "\n".join(current_raw)})
                current_raw = []
            
            table_lines = []
            while i < len(lines) and (lines[i].strip().startswith("|") or (not lines[i].strip() and i+1 < len(lines) and lines[i+1].strip().startswith("|"))):
                table_lines.append(lines[i])
                i += 1
            sections.append({"type": "table", "table_lines": table_lines})
        else:
            current_raw.append(lines[i]); i += 1
            
    if current_raw:
        sections.append({"type": "raw", "content": "\n".join(current_raw)})
    return sections


def get_table_rows(table_lines: List[str]) -> List[Tuple[int, List[str]]]:
    rows = []
    pipe_lines_count = 0
    for idx, line in enumerate(table_lines):
        s = line.strip()
        if not s.startswith("|"): continue
        pipe_lines_count += 1
        
        # Skip the first two | lines (usually header and divider)
        if pipe_lines_count <= 2: continue
        
        # Divider check as a fallback
        if re.search(r":?-{2,}:?", s): continue
        
        # More robust splitting (handles missing trailing pipes better)
        cells = [c.strip() for c in s.split("|")]
        if s.startswith("|"): cells = cells[1:]
        if s.endswith("|"): cells = cells[:-1]
        
        if not cells: continue
        rows.append((idx, cells))
    return rows


def _normalize_label(text: str) -> str:
    """Aggressively normalizes labels to avoid mismatches due to bullets, newlines, HTML tags, or whitespace."""
    if not text: return ""
    # Lowercase, strip HTML tags (like <br>), then remove symbols/bullets
    t = text.lower()
    t = re.sub(r'<[^>]+>', '', t) # Strip HTML tags
    t = re.sub(r'[^a-z0-9]', '', t)
    return t


def get_cell(sections: List[Dict], target_id: str, col_index: int) -> str:
    """Finds a cell in a section or table row matching the target_id (Screen or Module)."""
    # Split "Header | Row" if present for unambiguous targeting
    header_target = target_id
    row_target = None
    if " | " in target_id:
        header_target, row_target = target_id.split(" | ", 1)

    norm_header = _normalize_label(header_target)
    norm_row = _normalize_label(row_target) if row_target else None

    for s in sections:
        tl = s.get("table_lines")
        if not tl: continue
        
        # 1. Match Header (Screen/Module ID or Header Text)
        sect_id = s.get("id") or ""
        sect_title = s.get("title_line") or ""
        
        # Fuzzy match header
        match_header = (norm_header in _normalize_label(sect_id) or 
                        norm_header in _normalize_label(sect_title) or
                        _normalize_label(sect_id) in norm_header)
        
        if match_header:
            rows = get_table_rows(tl)
            if not rows: continue
            
            # If no row_target, usually means it's a single-row section (Type 1)
            if not row_target:
                _, cells = rows[0]
                if col_index < len(cells): return cells[col_index].strip()
            else:
                # For Type 1: row_target may be the screen title, not a row label.
                # If section has only 1 data row, use it directly when header matched.
                if len(rows) == 1:
                    _, cells = rows[0]
                    if col_index < len(cells): return cells[col_index].strip()
                
                # Search for specific row within this section (Type 2 / Design Doc)
                for _, cells in rows:
                    if cells:
                        norm_cell = _normalize_label(cells[0].strip())
                        if norm_row == norm_cell or norm_row in norm_cell or norm_cell in norm_row:
                            if col_index < len(cells): return cells[col_index].strip()
        
        # Fallback for standalone tables if row_target matches first cell
        if not match_header and not row_target:
            rows = get_table_rows(tl)
            for _, cells in rows:
                if cells:
                    norm_cell = _normalize_label(cells[0])
                    if norm_header == norm_cell or norm_header in norm_cell or norm_cell in norm_header:
                        if col_index < len(cells): return cells[col_index].strip()
    return ""


def replace_cell(section: Dict, target_row_id: str, col_index: int, new_content: str) -> bool:
    """Replaces content in a specific row and column."""
    tl = section.get("table_lines")
    if not tl: return False
    rows = get_table_rows(tl)
    if not rows: return False
    
    # Handle "Header | Row" combined ID
    row_match_target = target_row_id
    if " | " in target_row_id:
        _, row_match_target = target_row_id.split(" | ", 1)

    norm_row_target = _normalize_label(row_match_target)
    line_idx_to_update = -1
    cells_to_update = []
    
    # If it's a specific screen/module section with exactly one data row (Type 1 Storyboard)
    if not " | " in target_row_id and len(rows) == 1 and (section.get("id") == target_row_id or section.get("type") in ["screen", "module"]):
        line_idx_to_update, cells_to_update = rows[0]
    elif " | " in target_row_id and section.get("type") in ["screen", "module"] and len(rows) == 1:
        # Type 1 storyboard: "Screen 1.6 | Title" — the section has only 1 data row
        line_idx_to_update, cells_to_update = rows[0]
    else:
        # Search for the row within the table (Type 2 or Design Doc)
        norm_row_target = _normalize_label(row_match_target)
        
        for idx, cells in rows:
            if cells:
                norm_cell = _normalize_label(cells[0])
                # Exact or fuzzy match (contains)
                if norm_row_target == norm_cell or norm_row_target in norm_cell or norm_cell in norm_row_target:
                    line_idx_to_update, cells_to_update = idx, cells
                    break
                
                # Fallback: if row_match_target is very short (shorthand), check if it matches start of cell
                if len(norm_row_target) > 3 and norm_cell.startswith(norm_row_target):
                    line_idx_to_update, cells_to_update = idx, cells
                    break
    
    if line_idx_to_update == -1:
        return False

    # INDEX SAFETY: If the AI hallucinations an index out of bounds, 
    # try to map it back to the last valid column (usually Actions or Visuals)
    # BUT ONLY if it's very close or clearly a mapping error. 
    # For storyboards with 3 columns, index 4 (from Type 2) should NOT clip to index 2 (Visuals).
    if col_index >= len(cells_to_update):
        # If it's way out of bounds, it's likely a Type 1/2 confusion.
        # We should try to find the "Audio" or "OST" column by name if possible?
        # For now, let's just be safer: if it's a 3-col table and index is 4+, it's a failure.
        if len(cells_to_update) <= 3 and col_index >= 3:
            return False 
        col_index = len(cells_to_update) - 1
        
    cells_to_update[col_index] = f" {new_content.strip().replace(chr(10), ' ')} "
    section["table_lines"][line_idx_to_update] = "|" + "|".join(cells_to_update) + "|"
    return True


def sections_to_doc(sections: List[Dict]) -> str:
    parts = []
    for s in sections:
        if s["type"] == "raw":
            parts.append(s["content"])
        else:
            header = s.get("title_line", "")
            table = "\n".join(s.get("table_lines", []))
            parts.append(f"{header}\n{table}" if header else table)
    return "\n".join(parts)


def doc_summary(sections: List[Dict], doc_type: str = "Design Document") -> str:
    out = []
    dt_lower = doc_type.lower()
    is_sb_type2 = "type 2" in dt_lower
    is_storyboard = "storyboard" in dt_lower and not is_sb_type2
    
    if is_storyboard:
        cn = ["OST", "Audio", "Visual"]
    elif is_sb_type2:
        cn = ["Section", "Topics", "Visuals", "OST", "Audio", "Status", "Actions"]
    else: # Design Doc
        cn = ["Module", "Delivery", "Obj", "Topics", "Strategy", "Activities", "Duration"]
    
    for s in sections:
        if s["type"] in ["screen", "module", "table"]:
            rows = get_table_rows(s.get("table_lines", []))
            for _, cells in rows:
                base_label = s.get("id") or "Table"
                row_label = cells[0].strip() if cells else "Row"
                
                # If it's Type 1, the base_label is already unique (e.g. Screen 1.1)
                # If it's Type 2, the rows need the base_label + row_label for uniqueness
                if len(rows) > 1 and row_label:
                    label = f"{base_label} | {row_label}"
                else:
                    label = base_label
                
                out.append(f"\n--- {label} ---")
                for i, c in enumerate(cells[:7]):
                    col_name = cn[i] if i < len(cn) else f"col{i}"
                    out.append(f"  {col_name}: {c.strip()[:200]}")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────────
# 2. Diff
# ─────────────────────────────────────────────────────────────

def diff_strings(old: str, new: str) -> List[Dict]:
    old, new = old.strip(), new.strip()
    if old == new: return [{"type": "equal", "text": old}]
    if not old: return [{"type": "insert", "text": new}]
    if not new: return [{"type": "delete", "text": old}]
    ow, nw = re.split(r"(\s+)", old), re.split(r"(\s+)", new)
    sm, result = difflib.SequenceMatcher(None, ow, nw, autojunk=False), []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":   result.append({"type": "equal",  "text": "".join(ow[i1:i2])})
        elif op == "replace":
            result.append({"type": "delete", "text": "".join(ow[i1:i2])})
            result.append({"type": "insert", "text": "".join(nw[j1:j2])})
        elif op == "delete": result.append({"type": "delete", "text": "".join(ow[i1:i2])})
        elif op == "insert": result.append({"type": "insert", "text": "".join(nw[j1:j2])})
    return result


# ─────────────────────────────────────────────────────────────
# 3. Hallucination Guard
# ─────────────────────────────────────────────────────────────

BAD = ["please review", "updated content", "i have updated", "here is the updated",
       "as requested", "!--", "[updated", "content goes here", "insert content",
       "shortened version", "expanded version", "see above", "see below",
       "change for screen", "edit for screen"]

def is_placeholder(text: str) -> bool:
    lower = text.lower().strip()
    if lower.startswith("!--"): return True
    if len(text) < 100 and any(p in lower for p in BAD): return True
    return False


# ─────────────────────────────────────────────────────────────
# 4. Intent Classifier
# ─────────────────────────────────────────────────────────────

CLASSIFIER_SYS = """Classify the user message as EDIT or CHAT.

**TARGETS:**
- Storyboards (Type 1): "Screen 1.1", "Screen 2.3", etc.
- Storyboards (Type 2): "Intro", "History", "Concept", "Quiz" (Section names).
- Design Documents: "Module 1", "Module 2", etc.

**RULES:**
- EDIT = explicit request to change/update/fix specific content.
- CHAT = greetings, thanks, general help, or vague requests.

**INTENT CLASSIFICATION:**
- If the user says "thanks", "ok", "cool", "done" after an edit, it's CHAT.
- If referring to "it/its/that", use the most recent screen/module/section from history.
- "target_screens" should contain the label: "1.1", "Module 1", "Intro", etc.

**DYNAMIC CHAT REPLY:**
- If intent is CHAT, generate a natural, context-aware response.

Return ONLY JSON:
{
  "intent": "EDIT" or "CHAT",
  "target_screens": ["1.1"] or ["Module 1"] or ["Intro"] or ["ALL"] or [],
  "col_hint": "ost"|"audio"|"visual"|"topics"|"strategy"|"all"|null,
  "chat_reply": "..."
}"""


def classify_intent(instruction: str, history: List[Dict], groq_key: str) -> Dict:
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)
        msgs = [{"role": "system", "content": CLASSIFIER_SYS}]
        if history:
            for m in history[-6:]: msgs.append({"role": m["role"], "content": m["content"]})
        msgs.append({"role": "user", "content": f"CLASSIFY: {instruction}"})
        r = client.chat.completions.create(model="llama-3.1-8b-instant", messages=msgs,
                                           response_format={"type": "json_object"}, max_tokens=250)
        return json.loads(r.choices[0].message.content)
    except Exception as e:
        print(f"Classifier error: {e}")
        action_words = ["change","update","edit","fix","make","rewrite","shorten","expand",
                        "replace","modify","improve","creative","shorter","longer","rephrase"]
        if any(w in instruction.lower() for w in action_words):
            screen = None
            for msg in reversed(history or []):
                m = re.search(r"screen\s+(\d+\.\d+)", msg["content"], re.IGNORECASE)
                if m: screen = m.group(1); break
            return {"intent":"EDIT","target_screens":[screen] if screen else [],
                    "col_hint":None,"chat_reply":""}
        return {"intent":"CHAT","target_screens":[],"col_hint":None,
                "chat_reply":"I'm here to help! I can update your storyboard screens — just let me know what needs to change."}


# ─────────────────────────────────────────────────────────────
# 5. Edit LLM Prompt
# ─────────────────────────────────────────────────────────────

EDIT_SYS = """You are an expert Instructional Design Assistant.

COLUMN INDICES (STORYBOARD / TYPE 1):
  0 = OST, 1 = Audio, 2 = Visual

COLUMN INDICES (STORYBOARD TYPE 2):
  0 = Section Title, 1 = Topics, 2 = Visuals/Developer Notes, 3 = OST, 4 = Audio, 5 = Status, 6 = Actions

COLUMN INDICES (DESIGN DOCUMENT):
  0 = Module Title, 1 = Delivery, 2 = Objectives, 3 = Topics, 4 = Strategy, 5 = Activities, 6 = Duration

STORYBOARD TYPE 2 SPECIFICS:
- Column 0 (Section) is the primary row label (e.g. "Intro", "History").
- If the user asks to "change visuals for Intro", use row "Intro" and col_index 2.
- If the user selects text in "Audio Narration", col_index will be 4.

RULES:
1. new_content = COMPLETE ACTUAL TEXT for the targeted cell.
2. ONLY transform the EXISTING content shown.
3. NEVER use placeholders ("Updated here", etc.).
4. screen_num MUST match the exact label from the context. If the context uses "Header | Row" (e.g., "Module 1 | Intro"), you MUST return that exact combined string as the screen_num. THIS IS CRITICAL FOR TYPE 2 DOCS.
5. When doc_type is "Storyboard Type 2", you MUST strictly follow the 7-column map.
6. CRITICAL: If the user asks to edit MULTIPLE columns (e.g. "update OST and Audio"), you MUST return MULTIPLE separate objects in the `edits` array (one for each `col_index`).
7. Read the user's request carefully. Do not miss requested columns. If a request fits multiple rows (e.g. "update all activities"), return an object for EACH row.

RESPONSE — STRICT JSON ONLY:
{
  "reasoning": "...", "assistant_reply": "...",
  "edits": [
    {"screen_num": "LabelOfRow", "col_index": 0, "new_content": "..."},
    {"screen_num": "LabelOfRow", "col_index": 1, "new_content": "..."}
  ],
  "is_edit": true
}"""


# ─────────────────────────────────────────────────────────────
# 6. Main Entry Point
# ─────────────────────────────────────────────────────────────

def ai_edit_document(
    api_key: str,
    current_doc: str,
    user_instruction: str,
    doc_type: str = "Design Document",
    chat_history: List[Dict] = None,
    # New: frontend passes these when user selects text in a cell
    selected_text: str = None,
    selected_screen_num: str = None,
    selected_col_index: int = None,
    selected_col_name: str = None,
) -> Dict:
    groq_key = api_key or os.environ.get("GROQ_API_KEY", "")
    history = chat_history or []
    API_URL = "https://backend.buildpicoapps.com/aero/run/llm-api?pk=v1-Z0FBQUFBQnBtS2ptdFNtblZXcldCVV80M2ZLbElhOHhGMzd1Z1c1NWpiMXdfMU5uX3VVWkR5Q0N3OGEwUElfNWRIWVI3QkFxQ2FCU2ZRV0JLSVBja2dBaXR6dTN2WktVZVE9PQ=="

    def fail(msg): return {"assistant_reply": msg, "updated_document": current_doc,
                           "original_document": current_doc, "is_edit": False, "diff": []}

    # ── Step 1: Intent ──
    dt_lower = doc_type.lower()
    is_sb_type2 = "type 2" in dt_lower
    is_storyboard = "storyboard" in dt_lower and not is_sb_type2

    # If frontend provides explicit selection context, skip classifier — it's always an EDIT
    if selected_screen_num is not None and selected_col_index is not None:
        col_name = selected_col_name
        if not col_name:
            if is_storyboard:
                map_cols = ["ost", "audio", "visual"]
            elif is_sb_type2:
                map_cols = ["section", "topics", "visual", "ost", "audio", "status", "actions"]
            else: # Design Doc
                map_cols = ["module", "delivery", "objectives", "topics", "strategy", "activities", "duration"]
            
            if selected_col_index < len(map_cols):
                col_name = map_cols[selected_col_index]

        intent_data = {
            "intent": "EDIT",
            "target_screens": [selected_screen_num],
            "col_hint": col_name,
            "chat_reply": ""
        }
    else:
        intent_data = classify_intent(user_instruction, history, groq_key)

    if intent_data.get("intent") == "CHAT":
        return {
            "assistant_reply": intent_data.get("chat_reply") or "I'm here to help! Let me know if you want to edit any part of the storyboard.",
            "updated_document": current_doc,
            "original_document": current_doc,
            "is_edit": False,
            "diff": []
        }

    # ── Step 2: Resolve screens/modules ──
    sections = parse_document_into_sections(current_doc)
    dt_lower = doc_type.lower()
    is_sb_type2 = "type 2" in dt_lower
    is_storyboard = "storyboard" in dt_lower and not is_sb_type2
    
    all_targets = [s["id"] for s in sections if s.get("id")]
    # If it's a Design Doc or Type 2 SB, we also look into tables for modules/sections
    if not is_storyboard:
        for s in sections:
            if s["type"] == "table":
                rows = get_table_rows(s["table_lines"])
                for _, cells in rows:
                    if cells and cells[0].strip():
                        all_targets.append(cells[0].strip())

    targets = intent_data.get("target_screens") or []
    
    # Always check if the user specifically mentions screen numbers in the instruction
    found = re.findall(r"(Screen\s+\d+\.\d+|Module\s+(\d+|[A-Z])|Section\s+\w+)", user_instruction, re.IGNORECASE)
    if found: 
        for m in found:
            t = m[0]
            if not any(t.lower() in existing.lower() for existing in targets):
                targets.append(t)
                
    # Also actively look for row labels (Type 2 / Design Doc) in the user's instruction
    # to support multi-row editing when a single cell is selected.
    if not is_storyboard:
        for s in sections:
            rows = get_table_rows(s.get("table_lines", []))
            for _, cells in rows:
                if cells and len(cells[0].strip()) > 2:
                    lbl = cells[0].strip()
                    # If lbl is "Intro" or "Summary" and exists in user instruction
                    if re.search(r'\b' + re.escape(lbl) + r'\b', user_instruction, re.IGNORECASE):
                        # Avoid duplicates
                        has_lbl = any(lbl.lower() in existing.lower() for existing in targets)
                        if not has_lbl:
                            mod_id = s.get("id")
                            if mod_id:
                                targets.append(f"{mod_id} | {lbl}")
                            else:
                                targets.append(lbl)

    if not targets:
        # Fallback to any distinct word that might be a section label in Type 2
        if is_sb_type2:
            for s in sections:
                rows = get_table_rows(s.get("table_lines", []))
                for _, cells in rows:
                    if cells and cells[0].strip().lower() in user_instruction.lower():
                        targets.append(cells[0].strip())
            
            if not targets:
                for msg in reversed(history):
                    found = re.findall(r"(Screen\s+\d+\.\d+|Module\s+(\d+|[A-Z]))", msg["content"], re.IGNORECASE)
                    if found: targets = [m[0] for m in found]; break

    expanded = []
    for t in targets:
        if t == "ALL": expanded = all_targets; break
        elif t.startswith("ALL_MODULE_"):
            mod = t.replace("ALL_MODULE_", "")
            expanded += [s for s in all_targets if s.startswith(mod + ".")]
        else:
            # Normalize target (e.g. "1.1" -> "Screen 1.1" if storyboard)
            if is_storyboard and re.match(r"^\d+\.\d+$", t): expanded.append(f"{t}") # Keep raw as we match on id
            else: expanded.append(t)

    # ── Step 3: Build LLM context ──
    if is_storyboard:
        cn = ["OST", "Audio Narration", "Visual Instructions"]
    elif is_sb_type2:
        cn = ["Section", "Topics", "Visual Instructions/Developer Notes", "On-screen text", "Audio Narration", "Status", "Actions"]
    else:
        cn = ["Module", "Delivery Mode", "Learning Objectives", "Topics", "Recommended Strategy", "Activities", "Duration"]

    # Selection context
    selection_ctx = ""
    if selected_text and selected_screen_num is not None and selected_col_index is not None:
        full_cell = get_cell(sections, str(selected_screen_num), int(selected_col_index))
        # Use provided col_name from frontend for maximum accuracy
        col_display_name = selected_col_name or (cn[selected_col_index] if selected_col_index < len(cn) else f"Column {selected_col_index}")
        selection_ctx = f"### USER HAS SELECTED THIS SPECIFIC TEXT ###\nSelected text: \"{selected_text}\"\nTarget: {selected_screen_num}\nPrimary Column selected: {col_display_name} (Index: {selected_col_index})\n\nINSTRUCTION: The user selected this text, but they might ask you to edit this column OR multiple columns in the row. Return an edit object for EVERY column that needs to change based on their request."

    # Target content
    ctx = "\n### CURRENT CONTENT ###\n"
    found_targets = False
    for t in expanded:
        header_t = t
        row_t = None
        if " | " in t:
            header_t, row_t = t.split(" | ", 1)

        for s in sections:
            sect_id = s.get("id") or ""
            sect_title = s.get("title_line") or ""
            match_header = (header_t.lower() in sect_id.lower() or 
                            header_t.lower() in sect_title.lower() or
                            sect_id.lower() in header_t.lower())
            
            if match_header:
                rows = get_table_rows(s.get("table_lines", []))
                for _, cells in rows:
                    row_label = cells[0] if cells else ""
                    # Match row if row_t is present, otherwise match any row (standard behavior)
                    if not row_t or (row_label.lower() == row_t.lower() or 
                                    re.search(r'\b' + re.escape(row_t) + r'\b', row_label, re.IGNORECASE)):
                        found_targets = True
                        label = f"{sect_id} | {row_label}" if sect_id else row_label
                        ctx += f"\n--- {label} ---\n"
                        for i, c in enumerate(cells[:len(cn)]):
                            ctx += f"  col_index {i} ({cn[i]}): {c.strip()}\n"
    
    if not found_targets or len(expanded) > 10:
        ctx = f"\n### DOCUMENT SUMMARY ###\n{doc_summary(sections, doc_type)}"

    hist_str = ""
    if history:
        hist_str = "\n### RECENT CONVERSATION ###\n"
        for m in history[-6:]:
            hist_str += f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}\n"

    # Add specific hint for Type 2
    type2_hint = ""
    if is_sb_type2:
        type2_hint = "\nIMPORTANT: This is a Storyboard Type 2 (7 columns). Ensure you map the row 'Header | Row' label correctly and use the specific column indices (Topics=1, Visuals=2, OST=3, Audio=4)."

    user_prompt = f"USER REQUEST: {user_instruction}\n{hist_str}\n{selection_ctx}\n{ctx}{type2_hint}\nTARGETS: {expanded or 'Determine from request'}\nCOL HINT: {intent_data.get('col_hint')}\nDOCUMENT TYPE: {doc_type}"

    # ── Step 4: Call LLM ──
    try:
        full_prompt = EDIT_SYS + "\n\n" + user_prompt
        resp = requests.post(API_URL, json={"prompt": full_prompt},
                             headers={"Content-Type": "application/json"}, timeout=60)
        data = resp.json()
        if data.get("status") != "success": raise Exception(str(data))
        parsed = _extract_json(data.get("text", ""))
    except Exception as e:
        return fail(f"AI call failed: {str(e)}")

    # ── Step 5: Apply ──
    if not parsed.get("is_edit") or not parsed.get("edits"):
        return {"assistant_reply": parsed.get("assistant_reply", "No changes made."),
                "updated_document": current_doc, "original_document": current_doc,
                "is_edit": False, "diff": []}

    if is_storyboard:
        CN_DISPLAY = ["ON-SCREEN TEXT (OST)", "Audio Narration", "Visual Instructions"]
    elif is_sb_type2:
        CN_DISPLAY = ["Section", "Topics", "Visual Instructions/Developer Notes", "On-screen text", "Audio Narration", "Status", "Actions"]
    else:
        CN_DISPLAY = ["Module", "Delivery Mode", "Learning Objectives", "Topics", "Recommended Strategy", "Activities", "Duration"]
        
    diffs, applied, warns = [], False, []

    for edit in parsed.get("edits", []):
        sn = str(edit.get("screen_num", "")).strip()
        ci = edit.get("col_index")
        nc = re.sub(r"^!--\s*", "", str(edit.get("new_content", ""))).strip()

        # CRITICAL: Only override `sn` if it is explicitly missing or empty.
        if selected_screen_num is not None:
            if not sn or sn.lower() in ["none", "null"]:
                sn = str(selected_screen_num).strip()
            
            if ci is None and selected_col_index is not None:
                ci = int(selected_col_index)

        if not sn or ci is None or not nc:
            warns.append(f"Skipped invalid edit: {edit}"); continue
            
        try:
            ci = int(ci)
            if is_storyboard and ci >= len(CN_DISPLAY):
                if ci == 4 or "audio" in nc.lower()[:20]: ci = 1  # Audio
                elif ci == 3 or "ost" in nc.lower()[:20]: ci = 0  # OST
                elif selected_col_index is not None: ci = int(selected_col_index)
                else: ci = len(CN_DISPLAY) - 1
        except (ValueError, TypeError):
            if selected_col_index is not None: ci = int(selected_col_index)
            else: warns.append(f"Skipped invalid col_index: {edit}"); continue
                
        if is_placeholder(nc):
            warns.append(f"Skipped placeholder for {sn} col {ci}"); continue

        # ── Find correct section target ──
        target_sect = None
        header_sn = sn
        row_sn = None
        if " | " in sn:
            header_sn, row_sn = sn.split(" | ", 1)

        for s in sections:
            sect_id = s.get("id") or ""
            sect_title = s.get("title_line") or ""
            
            norm_sect_id = _normalize_label(sect_id)
            norm_sect_title = _normalize_label(sect_title)
            norm_header_sn = _normalize_label(header_sn)

            match_header = (norm_header_sn in norm_sect_id or 
                            norm_header_sn in norm_sect_title or
                            norm_sect_id in norm_header_sn)
            
            if match_header:
                if not row_sn:
                    if s.get("table_lines"): 
                        target_sect = s; break
                else:
                    norm_row_sn = _normalize_label(row_sn)
                    if norm_row_sn in norm_sect_title:
                        if s.get("table_lines"):
                            target_sect = s; break
                    
                    rows = get_table_rows(s.get("table_lines", []))
                    if len(rows) == 1 and s.get("table_lines"):
                        target_sect = s; break
                    
                    for _, cells in rows:
                        if cells:
                            norm_cell = _normalize_label(cells[0])
                            if norm_row_sn == norm_cell or norm_row_sn in norm_cell or norm_cell in norm_row_sn:
                                target_sect = s; break
                    if target_sect: break
            
        if not target_sect:
            # Fallback: Deep search for matching row label in any section if no pipe was used
            norm_sn = _normalize_label(sn)
            for s in sections:
                rows = get_table_rows(s.get("table_lines", []))
                for _, cells in rows:
                    if cells:
                        norm_cell = _normalize_label(cells[0])
                        if norm_sn == norm_cell or (len(norm_sn) > 3 and norm_sn in norm_cell):
                            target_sect = s; break
                if target_sect: break

        if not target_sect:
            warns.append(f"Target '{sn}' not found"); continue

        old = get_cell([target_sect], sn, ci)

        if replace_cell(target_sect, sn, ci, nc):
            applied = True
            diffs.append({
                "screen_num": sn, "col_index": ci,
                "col_name": CN_DISPLAY[ci] if ci < len(CN_DISPLAY) else f"Column {ci}",
                "old_content": old, "new_content": nc,
                "diff_tokens": diff_strings(old, nc)
            })
        else:
            warns.append(f"Failed to replace {sn} col {ci}")

    updated = sections_to_doc(sections)
    reply = parsed.get("assistant_reply", "Done! Review the highlighted changes.")
    if warns: reply += "\n\n⚠️ " + " | ".join(warns)

    return {"assistant_reply": reply,
            "updated_document": updated if applied else current_doc,
            "original_document": current_doc,
            "is_edit": applied, "diff": diffs}


def accept_edits(updated_document: str) -> str: return updated_document
def reject_edits(original_document: str) -> str: return original_document


def _extract_json(raw: str) -> Dict:
    try:
        import json_repair
        s, e = raw.find("{"), raw.rfind("}")
        if s != -1 and e != -1:
            p = json_repair.loads(raw[s:e+1])
            if isinstance(p, dict): return p
    except Exception: pass
    return {"reasoning":"","assistant_reply":raw.strip(),"edits":[],"is_edit":False}
