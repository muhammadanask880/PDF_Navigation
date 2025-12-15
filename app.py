import streamlit as st
import base64
import os
import fitz  # PyMuPDF
import json
import re
 
# ---------------- Streamlit Config ----------------
st.set_page_config(page_title="Zoomable PDF Viewer", layout="wide")
st.title("Sheet Navigator")
 
# ---------------- Session State for History ----------------
# List of {sheet: str, page: int}
if 'nav_history' not in st.session_state:
    st.session_state.nav_history = []  
 
# ---------------- Load PDF ----------------
uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
pdf_bytes = None
 
if uploaded is not None:
    pdf_bytes = uploaded.read()
elif os.path.exists("sample.pdf"):
    try:
        with open("sample.pdf", "rb") as f:
            pdf_bytes = f.read()
    except FileNotFoundError:
        pass # Allow the st.info message below to run
 
if pdf_bytes is None:
    st.info("Upload a PDF or place sample.pdf next to this app")
    st.stop()
 
# ---------------- Extract Sheet/Section IDs ----------------
@st.cache_data(show_spinner=True)
def extract_sheet_map(pdf_bytes):
    """
    Extract all section IDs from the bottom 20% of each page.
    Returns: { "SECTION-ID": page_number }
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    sheet_map = {}
    
    # Regex matches: S-6, A-201, S-6.0, FX001, FX-002, etc.
    pattern = re.compile(r"\b(?:[A-Z]{1,4}-?\d+(?:\.\d+)?|[A-Z]{2,5}\d{1,4})\b")
 
    for page_index, page in enumerate(doc):
        height = page.rect.height
        candidates = []
        text_dict = page.get_text("dict")
        
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    raw = span.get("text", "").strip()
                    size = span.get("size", 0)
                    x0, y0, x1, y1 = span.get("bbox", (0, 0, 0, 0))
                    
                    # Only consider bottom 20% of page
                    if y0 < height * 0.80:
                        continue
                    
                    if pattern.fullmatch(raw):
                        norm = raw.upper()
                        # Add .0 only for standard dash-number sections like S-6 -> S-6.0
                        if re.match(r"^[A-Z]{1,4}-\d+$", norm):
                            norm += ".0"
                        candidates.append({"norm": norm, "size": size, "y": y0})
        
        if candidates:
            candidates.sort(key=lambda c: (c["size"], c["y"]), reverse=True)
            best = candidates[0]
            sheet_map[best["norm"]] = page_index + 1  # store page number
            
    return sheet_map
 
# Extract all sections first
with st.spinner("Extracting sections from PDF..."):
    sheet_map = extract_sheet_map(pdf_bytes)
 
# ---------------- Sidebar Input & History Update Logic ----------------
normalized_sheet_id = "" # Default to empty
 
def reset_history():
    """Clears the breadcrumb history."""
    st.session_state.nav_history = []
    
# Use a key to prevent re-running the input and causing a history loop
input_key = "sheet_input_field"
 
with st.sidebar:
    st.markdown("### Sheet/Section Navigation")
    st.markdown(f"**Total Sections:** {len(sheet_map)}")
    
    # User Input
    sheet_input = st.text_input("Enter Sheet/Section ID (e.g., S-6, S-6.0)", key=input_key)
    
    if st.button("Reset Breadcrumbs"):
        reset_history()
        # Rerun to update the history in the component
        st.rerun()
 
    # 1. Validation Logic
    if sheet_input:
        key = sheet_input.strip().upper()
        # Normalization logic
        if re.match(r"^[A-Z]{1,4}-\d+$", key):
            key += ".0"
            
        if key in sheet_map:
            normalized_sheet_id = key
            page_num = sheet_map[key]
            
            # 2. History Management (Append New Entry)
            last_entry = st.session_state.nav_history[-1] if st.session_state.nav_history else None
            
            # Append only if it's a new, valid sheet ID
            if last_entry is None or last_entry['sheet'] != normalized_sheet_id:
                st.session_state.nav_history.append({"sheet": normalized_sheet_id, "page": page_num})
                
        else:
            st.error(f"Sheet '{sheet_input}' not found in extracted data.")
 
    st.caption("Detected sections (auto-extracted):")
    if sheet_map:
        st.code(", ".join(sorted(sheet_map.keys())))
    else:
        st.warning("No sections detected")
 
# ---------------- Prepare Data for JS ----------------
b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
sheet_map_json = json.dumps(sheet_map)
history_json = json.dumps(st.session_state.nav_history)
 
# ---------------- HTML + JS Viewer ----------------
html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>PDF Viewer</title>
<style>
  /* Reset and Basic Setup */
  body, html {{ margin:0; padding: 0; height: 100vh; overflow: hidden; font-family: sans-serif; background: #525659; }}
  
  .container {{
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100%;
  }}
  
  /* Breadcrumb & Toolbar Styles */
  .header-ui {{
    background: #f9fafb;
    border-bottom: 1px solid #ccc;
    flex-shrink: 0;
  }}
 
  .breadcrumb {{
    padding: 8px 16px;
    display:flex;
    align-items:center;
    gap:8px;
    flex-wrap:wrap;
    border-bottom: 1px solid #eee;
  }}
  
  .breadcrumb-item {{
    padding: 4px 10px;
    background:#fff;
    border:1px solid #d1d5db;
    border-radius:4px;
    cursor:pointer;
    font-size:13px;
    white-space: nowrap; /* Prevent sheet IDs from wrapping */
  }}
  .breadcrumb-item:hover {{ background:#e0e7ff; }}
  .breadcrumb-item.active {{ background:#4f46e5; color:#fff; border-color:#4f46e5; }}
  .breadcrumb-separator {{ color:#9ca3af; font-weight:bold; font-size: 12px; }}
 
  .toolbar {{
    padding: 8px 16px;
    display:flex;
    gap:10px;
    align-items:center;
    background: white;
  }}
 
  /* VIEWER CONTAINER - The Scrollable Area */
  .viewer {{
      flex: 1;
      overflow: auto; /* Enable Scrollbars for X and Y */
      padding: 20px;
      position: relative;
      background-color: #525659;
  }}
 
  /* PAGE CARD - Holds the Canvas */
  .page-card {{
      background: white;
      box-shadow: 0 4px 8px rgba(0,0,0,0.3);
      margin: 0 auto 20px auto;
      
      width: fit-content;
      max-width: none;
      display: block;
  }}
  
  canvas {{ display: block; }}
</style>
</head>
<body>
 
<div class="container">
  
  <div class="header-ui">
    <div class="breadcrumb" id="breadcrumb"></div>
 
    <div class="toolbar">
      <label>Page:</label>
      <input type="number" id="pageInput" min="1" value="1" style="width:50px;">
      <button id="goBtn">Go</button>
      <button id="backBtn">← Back</button>
      <div style="flex:1"></div>
      <label>Zoom:</label>
      <input type="range" id="scaleInput" min="0.25" max="4.0" step="0.25" value="0.25">
      <span id="scaleDisplay">0.25×</span>
    </div>
  </div>
 
  <div class="viewer" id="viewer">
      <div id="pages"></div>
  </div>
</div>
 
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
<script>
const pdfBytes = Uint8Array.from(atob("{b64_pdf}"), c => c.charCodeAt(0));
const sheetMap = {sheet_map_json};
let navigationHistory = {history_json}; // Use the history passed from Python
const pendingSheetID = "{normalized_sheet_id}";
 
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
 
let pdfDoc = null;
let scale = 1.0;
let currentPage = 1;
const pagesDiv = document.getElementById('pages');
const breadcrumbDiv = document.getElementById('breadcrumb');
const viewerDiv = document.getElementById('viewer');
 
 
// Function to inform Streamlit to update its session state (used for history manipulation)
function updateStreamlitHistory(history, newPage) {{
    // Post the new history state back to Streamlit
    const newHistoryJson = JSON.stringify(history);
    
    // This is a minimal way to send data back to Streamlit
    // We send a JSON stringified object containing the new history and the page to jump to
    // Streamlit doesn't natively handle two-way communication easily, so we use a trick:
    // We update the local history here, but to persist it, Streamlit needs to re-render.
    // For this demonstration, we'll keep the history manipulation local in JS
    // and rely on Streamlit's full re-run only when the Python input changes.
    // The breadcrumb logic is purely visual here, based on the initial state.
}}
 
// 1. Setup Breadcrumbs
function renderBreadcrumb() {{
    breadcrumbDiv.innerHTML = '';
    if (navigationHistory.length === 0) {{
        let item = document.createElement('div');
        item.className = 'breadcrumb-item active';
        item.innerText = 'Start';
        breadcrumbDiv.appendChild(item);
        return;
    }}
 
    navigationHistory.forEach((entry, idx) => {{
        if (idx > 0) {{
            let sep = document.createElement('span');
            sep.className = 'breadcrumb-separator';
            sep.innerText = '→';
            breadcrumbDiv.appendChild(sep);
        }}
        
        let item = document.createElement('div');
        const isActive = (idx === navigationHistory.length - 1 && entry.page === currentPage);
        item.className = 'breadcrumb-item' + (isActive ? ' active' : '');
        item.innerText = entry.sheet || `Page ${{entry.page}}`;
        
        // --- Breadcrumb Trimming Logic ---
        item.onclick = () => {{
            // 1. Trim the history array up to and including the clicked index
            navigationHistory = navigationHistory.slice(0, idx + 1);
            
            // 2. Navigate to the page
            gotoPage(entry.page);
            
            // 3. Re-render breadcrumb to show the new, trimmed state
            renderBreadcrumb();
        }};
        
        breadcrumbDiv.appendChild(item);
    }});
}}
 
// 2. Create Empty Page Containers
function createPages(numPages) {{
    pagesDiv.innerHTML = '';
    for(let i=1; i<=numPages; i++) {{
        let card = document.createElement('div');
        card.className = 'page-card';
        card.id = 'page-card-' + i;
        
        let canvas = document.createElement('canvas');
        canvas.id = 'canvas-' + i;
        canvas.dataset.page = i;
        
        card.appendChild(canvas);
        pagesDiv.appendChild(card);
    }}
}}
 
// 3. Render a Single Page (Fixes Rotation Issue)
function renderPage(n) {{
    if(!pdfDoc) return Promise.resolve();
    return pdfDoc.getPage(n).then(p => {{
        let v = p.getViewport({{scale}});
        let c = document.getElementById('canvas-' + n);
        let ctx = c.getContext('2d');
        
        let dpr = window.devicePixelRatio || 1;
        c.width = v.width * dpr;
        c.height = v.height * dpr;
        
        // CSS dimensions control the visible size (Crucial for horizontal scroll)
        c.style.width = v.width + 'px';
        c.style.height = v.height + 'px';
        
        // Ensure standard transform matrix (no rotation or skewing)
        return p.render({{
            canvasContext: ctx,
            viewport: v,
            transform: [dpr, 0, 0, dpr, 0, 0] // dpr scaling, no rotation
        }}).promise;
    }});
}}
 
// 4. Scroll Logic
function scrollToPage(p) {{
    const card = document.getElementById('page-card-' + p);
    if(card) {{
        card.scrollIntoView({{block: 'start', inline: 'nearest', behavior: 'auto'}});
        
        // Minor adjustment for top toolbar
        if(viewerDiv.scrollTop > 0) viewerDiv.scrollTop -= 10;
 
        currentPage = p;
        document.getElementById('pageInput').value = p;
        
        // Ensure breadcrumb active state is correct after jump
        renderBreadcrumb();
    }}
}}
 
// 5. Smart Loading Sequence
async function loadDocument() {{
    pdfDoc = await pdfjsLib.getDocument({{data: pdfBytes}}).promise;
    createPages(pdfDoc.numPages);
    
    let targetPage = 1;
    // Prioritize the latest history entry
    if (navigationHistory.length > 0) {{
        targetPage = navigationHistory[navigationHistory.length - 1].page;
    }} else if (pendingSheetID && sheetMap[pendingSheetID]) {{
        // Fallback for first run with a direct input
        targetPage = sheetMap[pendingSheetID];
    }}
 
    // Render target page immediately
    await renderPage(targetPage);
    scrollToPage(targetPage);
    
    // Render rest in background
    for(let i=1; i<=pdfDoc.numPages; i++) {{
        if(i !== targetPage) {{
            setTimeout(() => {{ renderPage(i); }}, 0);
        }}
    }}
}}
 
function gotoPage(p) {{
    if(p < 1 || p > pdfDoc.numPages) return;
    scrollToPage(p);
}}
 
// Initialization
renderBreadcrumb();
loadDocument();
 
// Event Listeners
document.getElementById('goBtn').onclick = () => {{
    const p = parseInt(document.getElementById('pageInput').value);
    if (p >= 1 && p <= pdfDoc.numPages) {{
        // Note: We don't update navigationHistory here because this button
        // is for scrolling, not formal sheet navigation. History is handled by
        // sidebar input or breadcrumb clicks.
        gotoPage(p);
    }}
}};
 
document.getElementById('backBtn').onclick = () => {{
    if(navigationHistory.length > 1) {{
        // Remove the current (last) entry
        navigationHistory.pop();
        
        // Get the new last entry
        const lastEntry = navigationHistory[navigationHistory.length - 1];
        
        // Go back to the previous page
        gotoPage(lastEntry.page);
        
        // Update breadcrumb
        renderBreadcrumb();
    }}
}};
 
document.getElementById('scaleInput').oninput = (e) => {{
    scale = parseFloat(e.target.value);
    document.getElementById('scaleDisplay').innerText = scale.toFixed(2) + '×';
    
    // Update all pages with new scale
    renderPage(currentPage).then(() => {{
         for(let i=1; i<=pdfDoc.numPages; i++) {{
             if(i !== currentPage) renderPage(i);
         }}
    }});
}};
 
</script>
</body>
</html>
"""
 
st.components.v1.html(html, height=800, scrolling=True)
