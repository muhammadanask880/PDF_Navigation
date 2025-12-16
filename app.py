import streamlit as st
import base64
import os
import fitz  # PyMuPDF
import json
import re
 
# ---------------- Streamlit Config ----------------
st.set_page_config(page_title="Smart PDF Navigator", layout="wide")
st.title("Sheet Navigator")
 
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
        pass
 
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
    
    # Regex matches: S-6, A-201, S-6.0, FX001, etc.
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
                    _, y0, _, _ = span.get("bbox", (0, 0, 0, 0))
                    
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
 
with st.spinner("Extracting sections from PDF..."):
    sheet_map = extract_sheet_map(pdf_bytes)
 
# ---------------- Sidebar Logic ----------------
# We communicate via "Commands" to the JS frontend.
target_sheet_id = ""
target_page_num = 0
 
with st.sidebar:
    st.markdown("### Sheet/Section Navigation")
    st.markdown(f"**Total Sections:** {len(sheet_map)}")
    
    # Input field
    sheet_input = st.text_input("Enter Sheet/Section ID (e.g., S-6)", key="sheet_input_field")
    
    # Reset Button sends a specific flag to JS to clear local storage
    if st.button("Reset History"):
        target_sheet_id = "RESET"
 
    # Process Input
    if sheet_input:
        key = sheet_input.strip().upper()
        # Normalize S-6 to S-6.0
        if re.match(r"^[A-Z]{1,4}-\d+$", key):
            key += ".0"
            
        if key in sheet_map:
            target_sheet_id = key
            target_page_num = sheet_map[key]
        else:
            st.error(f"Sheet '{sheet_input}' not found.")
 
    st.divider()
    st.caption("Detected sections (auto-extracted):")
    if sheet_map:
        st.code(", ".join(sorted(sheet_map.keys())))
    else:
        st.warning("No sections detected")
 
# ---------------- Prepare Data for JS ----------------
b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
sheet_map_json = json.dumps(sheet_map)
 
# ---------------- HTML + JS Viewer ----------------
html_code = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>PDF Viewer</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
<style>
  /* --- STYLES --- */
  body, html {{ margin:0; padding: 0; height: 100vh; overflow: hidden; font-family: sans-serif; background: #525659; }}
  
  .container {{
    display: flex; flex-direction: column; height: 100vh; width: 100%;
  }}
  
  /* Header UI */
  .header-ui {{
    background: #f9fafb; border-bottom: 1px solid #ccc; flex-shrink: 0; padding: 8px 16px;
    display: flex; gap: 15px; align-items: center; justify-content: space-between;
  }}
 
  /* Breadcrumb Area */
  .breadcrumb {{
    display:flex; align-items:center; gap:6px; flex-wrap:wrap; flex: 1;
  }}
  
  .breadcrumb-item {{
    padding: 4px 10px; background:#fff; border:1px solid #d1d5db; border-radius:4px;
    cursor:pointer; font-size:13px; white-space: nowrap; user-select: none;
  }}
  .breadcrumb-item:hover {{ background:#e0e7ff; }}
  .breadcrumb-item.active {{ background:#4f46e5; color:#fff; border-color:#4f46e5; }}
  .breadcrumb-separator {{ color:#9ca3af; font-weight:bold; font-size: 12px; }}
 
  /* Controls */
  .controls {{ display: flex; gap: 10px; align-items: center; }}
  
  /* Viewer Area */
  .viewer {{
      flex: 1; overflow: auto; padding: 20px; position: relative; background-color: #525659;
      display: block; /* Changed from flex to block for better scroll handling */
  }}
  
  /* Custom Scrollbar Styling */
  .viewer::-webkit-scrollbar {{
    width: 10px;
    height: 10px;
  }}
  .viewer::-webkit-scrollbar-track {{
    background: transparent;
  }}
  .viewer::-webkit-scrollbar-thumb {{
    background: rgba(255, 255, 255, 0.2);
    border-radius: 5px;
  }}
  .viewer::-webkit-scrollbar-thumb:hover {{
    background: rgba(255, 255, 255, 0.4);
  }}
 
  canvas {{
      display: block; margin: 0 auto 20px auto; /* Center horizontally safely */
      box-shadow: 0 4px 8px rgba(0,0,0,0.3); background: white;
  }}
</style>
</head>
<body>
 
<div class="container">
  <div class="header-ui">
    <div class="breadcrumb" id="breadcrumb"></div>
    
    <div class="controls">
        <span style="font-size: 12px; font-weight: bold; color: #555;">Current Page: <span id="pg-disp">1</span></span>
        <label style="font-size: 12px; color: #555;">Zoom:</label>
        <input type="range" id="scaleInput" min="0.5" max="3.0" step="0.5" value="1.0" style="width: 80px;">
    </div>
  </div>
 
  <div class="viewer" id="viewer">
      <div id="pages"></div>
  </div>
</div>
 
<script>
// --- PYTHON DATA BRIDGE ---
const pdfData = "{b64_pdf}";
// If user typed "S-5", this will be "S-5.0". Otherwise empty string.
const pendingSheetID = "{target_sheet_id}";
// If user typed "S-5", this will be the page number (e.g. 8). Otherwise 0.
const pendingPage = {target_page_num};
 
// --- CONSTANTS ---
const KEY_HISTORY = 'pdf_nav_history_v2';
const KEY_LAST_PAGE = 'pdf_last_viewed_page_v2';
 
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
 
let pdfDoc = null;
let scale = 1.0;
let navHistory = [];
 
// =========================================================
// 1. HISTORY & NAVIGATION LOGIC
// =========================================================
 
// Load history from SessionStorage (survives Python re-runs)
try {{
    navHistory = JSON.parse(sessionStorage.getItem(KEY_HISTORY) || '[]');
}} catch(e) {{ navHistory = []; }}
 
// Handle RESET command
if (pendingSheetID === "RESET") {{
    navHistory = [];
    sessionStorage.removeItem(KEY_HISTORY);
    sessionStorage.removeItem(KEY_LAST_PAGE);
}}
 
// Determine where we were BEFORE this reload
// Default to 1 if no history
let lastViewedPage = parseInt(sessionStorage.getItem(KEY_LAST_PAGE) || '1');
 
// === CRITICAL FIX: Update History based on Python Input ===
if (pendingPage > 0 && pendingSheetID !== "RESET") {{
    
    // Check if this is a repeat command (e.g. user refreshed browser)
    const lastEntry = navHistory.length > 0 ? navHistory[navHistory.length - 1] : null;
    
    // Only update history if the destination is different from the current top entry
    // OR if history is empty
    if (!lastEntry || (lastEntry.sheet !== pendingSheetID)) {{
        
        // A. Add "FROM" Page (Where we scrolled to manually)
        // Check if we are actually moving away from a different page
        // AND ensure the last entry isn't already the page we are on
        if (!lastEntry || lastEntry.page !== lastViewedPage) {{
             navHistory.push({{ sheet: "Page " + lastViewedPage, page: lastViewedPage }});
        }}
 
        // B. Add "TO" Page (The target from Python)
        navHistory.push({{ sheet: pendingSheetID, page: pendingPage }});
        
        // C. Save & Update
        sessionStorage.setItem(KEY_HISTORY, JSON.stringify(navHistory));
        
        // Update current position immediately to avoid jitter
        lastViewedPage = pendingPage;
        sessionStorage.setItem(KEY_LAST_PAGE, pendingPage);
    }}
}}
 
// =========================================================
// 2. UI RENDERING
// =========================================================
 
function renderBreadcrumb() {{
    const bc = document.getElementById('breadcrumb');
    bc.innerHTML = '';
 
    if (navHistory.length === 0) {{
         bc.innerHTML = '<div class="breadcrumb-item active">Start</div>';
         return;
    }}
 
    navHistory.forEach((item, idx) => {{
        if (idx > 0) {{
            let sep = document.createElement('span');
            sep.className = 'breadcrumb-separator';
            sep.innerText = '→';
            bc.appendChild(sep);
        }}
        
        let el = document.createElement('div');
        el.className = 'breadcrumb-item';
        if (idx === navHistory.length - 1 && item.page === lastViewedPage) {{
            el.classList.add('active');
        }}
        
        el.innerText = item.sheet;
        
        // Click to navigate back
        el.onclick = () => {{
            // Trim history forward of this point
            navHistory = navHistory.slice(0, idx + 1);
            sessionStorage.setItem(KEY_HISTORY, JSON.stringify(navHistory));
            
            // Go to that page
            scrollToPage(item.page);
            renderBreadcrumb();
        }};
        
        bc.appendChild(el);
    }});
}}
 
// =========================================================
// 3. PDF RENDERING & SCROLLING
// =========================================================
 
async function loadDocument() {{
    const pdfBytes = Uint8Array.from(atob(pdfData), c => c.charCodeAt(0));
    pdfDoc = await pdfjsLib.getDocument({{ data: pdfBytes }}).promise;
    
    const pagesContainer = document.getElementById('pages');
    
    // Render all pages
    for(let i=1; i<=pdfDoc.numPages; i++) {{
        let canvas = document.createElement('canvas');
        canvas.id = 'canvas-' + i;
        
        // Initial render logic
        // We use a simple strategy: render visible pages later for performance,
        // but for this demo, we render all sequentially or on demand.
        // Here we create the structure first.
        pagesContainer.appendChild(canvas);
        renderPage(i);
    }}
 
    // Jump to the calculated start page
    // (Either the target from Python OR the last remembered scroll position)
    setTimeout(() => {{
        scrollToPage(lastViewedPage);
    }}, 500); // Small delay to allow rendering to settle
}}
 
async function renderPage(num) {{
    const page = await pdfDoc.getPage(num);
    const viewport = page.getViewport({{ scale: scale }});
    const canvas = document.getElementById('canvas-' + num);
    const context = canvas.getContext('2d');
 
    canvas.height = viewport.height;
    canvas.width = viewport.width;
    
    // Adjust CSS width for zoom effect
    canvas.style.width = viewport.width + "px";
    canvas.style.height = viewport.height + "px";
 
    await page.render({{ canvasContext: context, viewport: viewport }}).promise;
}}
 
function scrollToPage(p) {{
    const canvas = document.getElementById('canvas-' + p);
    if(canvas) {{
        canvas.scrollIntoView({{block: 'start', inline: 'nearest', behavior: 'auto'}});
        updateScrollState(p);
    }}
}}
 
// =========================================================
// 4. SCROLL DETECTION (The Magic Part)
// =========================================================
 
let scrollTimeout;
document.getElementById('viewer').addEventListener('scroll', () => {{
    clearTimeout(scrollTimeout);
    // Debounce to avoid constant updates
    scrollTimeout = setTimeout(() => {{
        detectCurrentPage();
    }}, 150);
}});
 
function detectCurrentPage() {{
    const viewer = document.getElementById('viewer');
    const viewerRect = viewer.getBoundingClientRect();
    const midPoint = viewerRect.top + (viewerRect.height / 3); // Check near top third
 
    // Loop through canvases to find which one is visible
    for(let i=1; i<=pdfDoc.numPages; i++) {{
        const canvas = document.getElementById('canvas-' + i);
        const rect = canvas.getBoundingClientRect();
        
        // If the top of the page is within the viewer or just above it
        // (Simple visibility check)
        if (rect.top <= midPoint && rect.bottom >= midPoint) {{
            if (lastViewedPage !== i) {{
                updateScrollState(i);
            }}
            break;
        }}
    }}
}}
 
function updateScrollState(p) {{
    lastViewedPage = p;
    document.getElementById('pg-disp').innerText = p;
    // Save to session immediately so Python reload knows where we were
    sessionStorage.setItem(KEY_LAST_PAGE, p);
    
    // Optional: Update breadcrumb active state visually if matches
    renderBreadcrumb();
}}
 
// Zoom Logic
document.getElementById('scaleInput').oninput = (e) => {{
    scale = parseFloat(e.target.value);
    // Re-render all pages (simple approach)
    // In production, you might only re-render visible ones
    for(let i=1; i<=pdfDoc.numPages; i++) {{
        renderPage(i);
    }}
}};
 
// Init
renderBreadcrumb();
loadDocument();
 
</script>
</body>
</html>
"""
 
st.components.v1.html(html_code, height=800)
