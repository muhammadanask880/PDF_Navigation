# import streamlit as st
# import base64
# import os

# st.set_page_config(page_title="Zoomable PDF Viewer", layout="wide")
# st.title("Zoomable Scrollable PDF Viewer — Corrected")

# # --- Load PDF ---
# uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
# pdf_bytes = None
# if uploaded is not None:
#     pdf_bytes = uploaded.read()
# else:
#     sample_path = "sample.pdf"
#     if os.path.exists(sample_path):
#         with open(sample_path, "rb") as f:
#             pdf_bytes = f.read()

# if pdf_bytes is None:
#     st.info("No PDF provided. Upload a file or place 'sample.pdf' next to this app.")
#     st.stop()

# b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

# # Sidebar initial zoom
# with st.sidebar:
#     st.markdown("### Viewer Settings")
#     initial_scale = st.slider("Initial zoom", 0.25, 3.0, 0.25, 0.05)

# html = f"""
# <!doctype html>
# <html>
# <head>
# <meta charset="utf-8">
# <title>Zoomable PDF Viewer</title>
# <style>
# * {{ box-sizing: border-box; }}
# body {{ margin:0; font-family:Arial, sans-serif; background:#f5f5f5; height:100vh; overflow:hidden; }}

# .container {{ display: flex; height: 100vh; }}

# .left-sidebar {{ 
#   width: 250px; 
#   background: #fff; 
#   border-right: 2px solid #ddd; 
#   display: flex; 
#   flex-direction: column;
#   overflow: hidden;
#   position: fixed;
#   left: 0;
#   top: 0;
#   height: 100vh;
#   z-index: 100;
# }}

# .sidebar-header {{
#   padding: 16px;
#   background: #111827;
#   color: #fff;
#   font-weight: 600;
#   font-size: 16px;
#   border-bottom: 1px solid #333;
# }}

# .history {{ 
#   flex: 1;
#   overflow-y: auto; 
#   padding: 8px;
# }}

# .history-entry {{ 
#   padding: 10px 12px; 
#   cursor: pointer; 
#   border-radius: 6px;
#   margin-bottom: 4px;
#   background: #f9fafb;
#   border: 1px solid #e5e7eb;
#   transition: all 0.2s;
# }}

# .history-entry:hover {{ 
#   background: #e0e7ff; 
#   border-color: #818cf8;
# }}

# .history-entry.active {{
#   background: #818cf8;
#   color: #fff;
#   border-color: #6366f1;
# }}

# .main-content {{ 
#   flex: 1; 
#   display: flex; 
#   flex-direction: column;
#   overflow: hidden;
#   margin-left: 250px;
# }}

# .toolbar {{ 
#   padding: 12px 16px; 
#   background: #fff; 
#   display: flex; 
#   flex-wrap: wrap; 
#   gap: 10px; 
#   align-items: center; 
#   border-bottom: 2px solid #ddd;
#   flex-shrink: 0;
# }}

# .toolbar input[type=number] {{ 
#   width: 70px; 
#   padding: 6px 8px;
#   border: 1px solid #ccc;
#   border-radius: 6px;
# }}

# .toolbar button {{ 
#   padding: 6px 14px; 
#   border-radius: 6px; 
#   border: none; 
#   cursor: pointer; 
#   background: #111827; 
#   color: #fff; 
#   font-weight: 600;
#   transition: background 0.2s;
# }}

# .toolbar button:hover {{
#   background: #374151;
# }}

# .toolbar button.secondary {{ 
#   background: #fff; 
#   border: 1px solid #ccc; 
#   color: #111827; 
# }}

# .toolbar button.secondary:hover {{
#   background: #f3f4f6;
# }}

# .toolbar .scale-display {{ 
#   font-weight: 600; 
#   color: #111827;
#   min-width: 50px;
# }}

# .viewer {{ 
#   flex: 1;
#   overflow: auto; 
#   padding: 20px; 
#   background: #f5f5f5;
# }}

# #pages {{ 
#   display: flex; 
#   flex-direction: column; 
#   gap: 20px; 
#   align-items: flex-start;
#   min-width: min-content;
# }}

# .page-card {{ 
#   background: #fff; 
#   padding: 0; 
#   box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
#   border-radius: 8px; 
#   overflow: hidden;
#   display: inline-block;
# }}

# canvas {{ 
#   display: block;
# }}
# </style>
# </head>
# <body>

# <div class="container">
#   <!-- Left Sidebar for History - Always Visible -->
#   <div class="left-sidebar">
#     <div class="sidebar-header">Page History</div>
#     <div class="history" id="history"></div>
#   </div>

#   <!-- Main Content -->
#   <div class="main-content">
#     <!-- Toolbar -->
#     <div class="toolbar">
#       <label style="font-weight:600;">Page:</label>
#       <input type="number" id="pageInput" min="1" value="1">
#       <button id="goBtn" class="secondary">Go</button>
#       <button id="backBtn" class="secondary">← Back</button>
      
#       <div style="flex:1;"></div>
      
#       <label style="font-weight:600;">Zoom:</label>
#       <input type="range" id="scaleInput" min="0.25" max="3.0" step="0.05" value="{initial_scale}" style="width:150px;">
#       <span id="scaleDisplay" class="scale-display">{initial_scale}×</span>
#     </div>

#     <!-- PDF Viewer with horizontal scroll -->
#     <div class="viewer" id="viewer">
#       <div id="pages"></div>
#     </div>
#   </div>
# </div>

# <script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
# <script>
# const b64="{b64_pdf}";
# const pdfData=atob(b64);
# const pdfBytes=new Uint8Array(pdfData.length);
# for(let i=0;i<pdfData.length;i++) pdfBytes[i]=pdfData.charCodeAt(i);

# const pdfjsLib=window['pdfjs-dist/build/pdf'];
# pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

# let pdfDoc=null;
# let scale={initial_scale};
# let pagesContainer=document.getElementById('pages');
# let pageInput=document.getElementById('pageInput');
# let scaleInput=document.getElementById('scaleInput');
# let scaleDisplay=document.getElementById('scaleDisplay');
# let historyContainer=document.getElementById('history');
# let visitedHistory=[];
# let currentPage=1;

# // Create canvas elements for all pages
# function createPages(total){{
#   pagesContainer.innerHTML='';
#   for(let i=1;i<=total;i++){{
#     const card=document.createElement('div');
#     card.className='page-card';
#     card.id=`page-card-${{i}}`;
#     const canvas=document.createElement('canvas');
#     canvas.id=`page-canvas-${{i}}`;
#     canvas.setAttribute('data-page-number',i);
#     card.appendChild(canvas);
#     pagesContainer.appendChild(card);
#   }}
# }}

# // Render a single page - NO max-width so it stays crisp at any zoom
# function renderPage(pageNum){{
#   return pdfDoc.getPage(pageNum).then(page=>{{
#     const viewport=page.getViewport({{scale:scale}});
#     const canvas=document.getElementById(`page-canvas-${{pageNum}}`);
#     const ctx=canvas.getContext('2d');
#     const outputScale=window.devicePixelRatio||1;
    
#     // Set actual canvas dimensions (high DPI)
#     canvas.width=Math.floor(viewport.width*outputScale);
#     canvas.height=Math.floor(viewport.height*outputScale);
    
#     // Set display dimensions (actual size, no stretching)
#     canvas.style.width=Math.floor(viewport.width)+'px';
#     canvas.style.height=Math.floor(viewport.height)+'px';
    
#     const transform=outputScale!==1?[outputScale,0,0,outputScale,0,0]:null;
#     return page.render({{canvasContext:ctx, viewport:viewport, transform:transform}}).promise;
#   }});
# }}

# // Render all pages
# function renderAllPages(){{
#   let p=Promise.resolve();
#   for(let i=1;i<=pdfDoc.numPages;i++) p=p.then(()=>renderPage(i));
#   return p;
# }}

# // Record page in history
# function recordVisited(pageNum){{
#   if(visitedHistory.length===0 || visitedHistory[visitedHistory.length-1]!==pageNum){{
#     const idx=visitedHistory.indexOf(pageNum);
#     if(idx!==-1) visitedHistory=visitedHistory.slice(0,idx+1);
#     else visitedHistory.push(pageNum);
#   }}
#   currentPage=pageNum;
#   updateHistoryDisplay();
# }}

# // Update history display
# function updateHistoryDisplay(){{
#   historyContainer.innerHTML='';
#   visitedHistory.forEach(p=>{{
#     const div=document.createElement('div');
#     div.className='history-entry';
#     if(p===currentPage) div.classList.add('active');
#     div.innerHTML=`<strong>Page ${{p}}</strong>`;
#     div.onclick=()=>{{ 
#       scrollToPage(p); 
#     }};
#     historyContainer.appendChild(div);
#   }});
# }}

# // Scroll to page and record history
# function scrollToPage(p){{
#   if(p>=1 && p<=pdfDoc.numPages){{
#     const card=document.getElementById(`page-card-${{p}}`);
#     const viewer=document.getElementById('viewer');
    
#     // Scroll to top of page
#     const cardTop=card.offsetTop;
#     viewer.scrollTop=cardTop - 20;
    
#     recordVisited(p);
#     pageInput.value=p;
#   }}
# }}

# // Toolbar events
# scaleInput.addEventListener('input',()=>{{ 
#   scale=parseFloat(scaleInput.value); 
#   scaleDisplay.innerText=scale.toFixed(2)+'×'; 
#   renderAllPages(); 
# }});

# document.getElementById('goBtn').addEventListener('click',()=>{{ 
#   scrollToPage(parseInt(pageInput.value)); 
# }});

# document.getElementById('backBtn').addEventListener('click',()=>{{ 
#   if(visitedHistory.length>1){{ 
#     visitedHistory.pop(); 
#     const prevPage=visitedHistory[visitedHistory.length-1];
#     currentPage=prevPage;
#     scrollToPage(prevPage); 
#   }} 
# }});

# pageInput.addEventListener('keypress', (e)=>{{
#   if(e.key==='Enter') scrollToPage(parseInt(pageInput.value));
# }});

# // Load PDF
# pdfjsLib.getDocument({{data: pdfBytes}}).promise.then(doc=>{{
#   pdfDoc=doc;
#   pageInput.max=pdfDoc.numPages;
#   createPages(pdfDoc.numPages);
#   renderAllPages().then(()=>{{ 
#     recordVisited(1); 
#   }});

#   // Track visible page using IntersectionObserver
#   const observer=new IntersectionObserver(entries=>{{
#     entries.forEach(entry=>{{
#       if(entry.isIntersecting){{
#         const p=parseInt(entry.target.querySelector('canvas').getAttribute('data-page-number'));
#         if(!isNaN(p) && p!==currentPage){{
#           recordVisited(p);
#           pageInput.value=p;
#         }}
#       }}
#     }});
#   }}, {{root: document.getElementById('viewer'), threshold:0.5}});

#   setTimeout(()=>{{ 
#     for(let i=1;i<=pdfDoc.numPages;i++) 
#       observer.observe(document.getElementById(`page-card-${{i}}`));
#   }}, 500);
# }}).catch(err=>{{ 
#   document.body.innerHTML='<div style="color:red;padding:20px;">Error loading PDF: '+err.message+'</div>'; 
# }});
# </script>
# </body>
# </html>
# """

# st.components.v1.html(html, height=900, scrolling=False)















































import streamlit as st
import base64
import os

st.set_page_config(page_title="Zoomable PDF Viewer", layout="wide")
st.title("Zoomable Scrollable PDF Viewer — Corrected")

# --- Load PDF ---
uploaded = st.file_uploader("Upload a PDF", type=["pdf"])
pdf_bytes = None
if uploaded is not None:
    pdf_bytes = uploaded.read()
else:
    sample_path = "sample.pdf"
    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            pdf_bytes = f.read()

if pdf_bytes is None:
    st.info("No PDF provided. Upload a file or place 'sample.pdf' next to this app.")
    st.stop()

b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

# Sidebar initial zoom
with st.sidebar:
    st.markdown("### Viewer Settings")
    initial_scale = st.slider("Initial zoom", 0.25, 3.0, 0.25, 0.05)

html = f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Zoomable PDF Viewer</title>
<style>
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:Arial, sans-serif; background:#f5f5f5; height:100vh; overflow:hidden; }}

.container {{ display: flex; height: 100vh; }}

.left-sidebar {{ 
  width: 250px; 
  background: #fff; 
  border-right: 2px solid #ddd; 
  display: flex; 
  flex-direction: column;
  overflow: hidden;
  position: fixed;
  left: 0;
  top: 0;
  height: 100vh;
  z-index: 100;
}}

.sidebar-header {{
  padding: 16px;
  background: #111827;
  color: #fff;
  font-weight: 600;
  font-size: 16px;
  border-bottom: 1px solid #333;
}}

.history {{ 
  flex: 1;
  overflow-y: auto; 
  padding: 8px;
}}

.history-entry {{ 
  padding: 10px 12px; 
  cursor: pointer; 
  border-radius: 6px;
  margin-bottom: 4px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
}}

.history-entry:hover {{ 
  background: #e0e7ff; 
  border-color: #818cf8;
}}

.history-entry.active {{
  background: #818cf8;
  color: #fff;
  border-color: #6366f1;
}}

.main-content {{ 
  flex: 1; 
  display: flex; 
  flex-direction: column;
  overflow: hidden;
  margin-left: 250px;
}}

.toolbar {{ 
  padding: 12px 16px; 
  background: #fff; 
  display: flex; 
  flex-wrap: wrap; 
  gap: 10px; 
  align-items: center; 
  border-bottom: 2px solid #ddd;
  flex-shrink: 0;
}}

.toolbar input[type=number] {{ 
  width: 70px; 
  padding: 6px 8px;
  border: 1px solid #ccc;
  border-radius: 6px;
}}

.toolbar button {{ 
  padding: 6px 14px; 
  border-radius: 6px; 
  border: none; 
  cursor: pointer; 
  background: #111827; 
  color: #fff; 
  font-weight: 600;
  transition: background 0.2s;
}}

.toolbar button:hover {{
  background: #374151;
}}

.toolbar button.secondary {{ 
  background: #fff; 
  border: 1px solid #ccc; 
  color: #111827; 
}}

.toolbar button.secondary:hover {{
  background: #f3f4f6;
}}

.toolbar .scale-display {{ 
  font-weight: 600; 
  color: #111827;
  min-width: 50px;
}}

.viewer {{ 
  flex: 1;
  overflow: auto; 
  padding: 20px; 
  background: #f5f5f5;
}}

#pages {{ 
  display: flex; 
  flex-direction: column; 
  gap: 20px; 
  align-items: flex-start;
  min-width: min-content;
}}

.page-card {{ 
  background: #fff; 
  padding: 0; 
  box-shadow: 0 4px 12px rgba(0,0,0,0.1); 
  border-radius: 8px; 
  overflow: hidden;
  display: inline-block;
}}

canvas {{ 
  display: block;
}}
</style>
</head>
<body>

<div class="container">
  <!-- Left Sidebar for History - Always Visible -->
  <div class="left-sidebar">
    <div class="sidebar-header">Page History</div>
    <div class="history" id="history"></div>
  </div>

  <!-- Main Content -->
  <div class="main-content">
    <!-- Toolbar -->
    <div class="toolbar">
      <label style="font-weight:600;">Page:</label>
      <input type="number" id="pageInput" min="1" value="1">
      <button id="goBtn" class="secondary">Go</button>
      <button id="backBtn" class="secondary">← Back</button>
      
      <div style="flex:1;"></div>
      
      <label style="font-weight:600;">Zoom:</label>
      <input type="range" id="scaleInput" min="0.25" max="3.0" step="0.05" value="{initial_scale}" style="width:150px;">
      <span id="scaleDisplay" class="scale-display">{initial_scale}×</span>
    </div>

    <!-- PDF Viewer with horizontal scroll -->
    <div class="viewer" id="viewer">
      <div id="pages"></div>
    </div>
  </div>
</div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.min.js"></script>
<script>
const b64="{b64_pdf}";
const pdfData=atob(b64);
const pdfBytes=new Uint8Array(pdfData.length);
for(let i=0;i<pdfData.length;i++) pdfBytes[i]=pdfData.charCodeAt(i);

const pdfjsLib=window['pdfjs-dist/build/pdf'];
pdfjsLib.GlobalWorkerOptions.workerSrc='https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';

let pdfDoc=null;
let scale={initial_scale};
let pagesContainer=document.getElementById('pages');
let pageInput=document.getElementById('pageInput');
let scaleInput=document.getElementById('scaleInput');
let scaleDisplay=document.getElementById('scaleDisplay');
let historyContainer=document.getElementById('history');
let visitedHistory=[];
let currentPage=1;

// Create canvas elements for all pages
function createPages(total){{
  pagesContainer.innerHTML='';
  for(let i=1;i<=total;i++){{
    const card=document.createElement('div');
    card.className='page-card';
    card.id=`page-card-${{i}}`;
    const canvas=document.createElement('canvas');
    canvas.id=`page-canvas-${{i}}`;
    canvas.setAttribute('data-page-number',i);
    card.appendChild(canvas);
    pagesContainer.appendChild(card);
  }}
}}

// Render a single page - NO max-width so it stays crisp at any zoom
function renderPage(pageNum){{
  return pdfDoc.getPage(pageNum).then(page=>{{
    const viewport=page.getViewport({{scale:scale}});
    const canvas=document.getElementById(`page-canvas-${{pageNum}}`);
    const ctx=canvas.getContext('2d');
    const outputScale=window.devicePixelRatio||1;
    
    // Set actual canvas dimensions (high DPI)
    canvas.width=Math.floor(viewport.width*outputScale);
    canvas.height=Math.floor(viewport.height*outputScale);
    
    // Set display dimensions (actual size, no stretching)
    canvas.style.width=Math.floor(viewport.width)+'px';
    canvas.style.height=Math.floor(viewport.height)+'px';
    
    const transform=outputScale!==1?[outputScale,0,0,outputScale,0,0]:null;
    return page.render({{canvasContext:ctx, viewport:viewport, transform:transform}}).promise;
  }});
}}

// Render all pages and preserve scroll position
function renderAllPages(){{
  const viewer=document.getElementById('viewer');
  const scrollTop=viewer.scrollTop;
  const scrollLeft=viewer.scrollLeft;
  
  let p=Promise.resolve();
  for(let i=1;i<=pdfDoc.numPages;i++) p=p.then(()=>renderPage(i));
  
  return p.then(()=>{{
    // Restore scroll position after rendering
    setTimeout(()=>{{
      viewer.scrollTop=scrollTop;
      viewer.scrollLeft=scrollLeft;
    }}, 50);
  }});
}}

// Record page in history - only when explicitly navigating
function recordVisited(pageNum, fromScroll){{
  // Don't add to history if it's from scrolling
  if(fromScroll) {{
    currentPage=pageNum;
    updateHistoryDisplay();
    return;
  }}
  
  if(visitedHistory.length===0 || visitedHistory[visitedHistory.length-1]!==pageNum){{
    const idx=visitedHistory.indexOf(pageNum);
    if(idx!==-1) visitedHistory=visitedHistory.slice(0,idx+1);
    else visitedHistory.push(pageNum);
  }}
  currentPage=pageNum;
  updateHistoryDisplay();
}}

// Update history display
function updateHistoryDisplay(){{
  historyContainer.innerHTML='';
  visitedHistory.forEach(p=>{{
    const div=document.createElement('div');
    div.className='history-entry';
    if(p===currentPage) div.classList.add('active');
    div.innerHTML=`<strong>Page ${{p}}</strong>`;
    div.onclick=()=>{{ 
      scrollToPage(p); 
    }};
    historyContainer.appendChild(div);
  }});
}}

// Scroll to page and record history (from manual navigation)
function scrollToPage(p, addToHistory){{
  if(p>=1 && p<=pdfDoc.numPages){{
    const card=document.getElementById(`page-card-${{p}}`);
    const viewer=document.getElementById('viewer');
    
    // Scroll to top of page
    const cardTop=card.offsetTop;
    viewer.scrollTop=cardTop - 20;
    
    if(addToHistory!==false){{
      recordVisited(p, false);
    }}
    pageInput.value=p;
  }}
}}

// Toolbar events
scaleInput.addEventListener('input',()=>{{ 
  scale=parseFloat(scaleInput.value); 
  scaleDisplay.innerText=scale.toFixed(2)+'×'; 
  renderAllPages(); 
}});

document.getElementById('goBtn').addEventListener('click',()=>{{ 
  scrollToPage(parseInt(pageInput.value)); 
}});

document.getElementById('backBtn').addEventListener('click',()=>{{ 
  if(visitedHistory.length>1){{ 
    visitedHistory.pop(); 
    const prevPage=visitedHistory[visitedHistory.length-1];
    currentPage=prevPage;
    scrollToPage(prevPage); 
  }} 
}});

pageInput.addEventListener('keypress', (e)=>{{
  if(e.key==='Enter') scrollToPage(parseInt(pageInput.value));
}});

// Load PDF
pdfjsLib.getDocument({{data: pdfBytes}}).promise.then(doc=>{{
  pdfDoc=doc;
  pageInput.max=pdfDoc.numPages;
  createPages(pdfDoc.numPages);
  renderAllPages().then(()=>{{ 
    recordVisited(1, false); // Add page 1 to history on load
  }});

  // Track visible page using IntersectionObserver
  const observer=new IntersectionObserver(entries=>{{
    entries.forEach(entry=>{{
      if(entry.isIntersecting){{
        const p=parseInt(entry.target.querySelector('canvas').getAttribute('data-page-number'));
        if(!isNaN(p) && p!==currentPage){{
          // Update current page from scrolling but don't add to history
          recordVisited(p, true);
          pageInput.value=p;
        }}
      }}
    }});
  }}, {{root: document.getElementById('viewer'), threshold:0.5}});

  setTimeout(()=>{{ 
    for(let i=1;i<=pdfDoc.numPages;i++) 
      observer.observe(document.getElementById(`page-card-${{i}}`));
  }}, 500);
}}).catch(err=>{{ 
  document.body.innerHTML='<div style="color:red;padding:20px;">Error loading PDF: '+err.message+'</div>'; 
}});
</script>
</body>
</html>
"""

st.components.v1.html(html, height=900, scrolling=False)