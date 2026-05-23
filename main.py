import streamlit as st
import sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location("eta", "ETA.1.7.3.1.8.py")
eta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(eta)
from pages.login import show_login_page
# Import all page functions to globals
login_page = eta.login_page
bau_app_page = eta.bau_app_page
mitarbeiter_page = eta.mitarbeiter_page
mitarbeiter_projekt_auswahl_page = eta.mitarbeiter_projekt_auswahl_page
profil_page = eta.profil_page
settings_page = eta.settings_page
dev_auth_page = eta.dev_auth_page
dev_page = eta.dev_page

# Make boxes stand out in both light and dark themes by default (stronger border + shadow)
st.markdown(
    """
    <style>
    /* Theme variables (default = light) */
    :root {
        --app-bg: #ffffff;
        --text-color: #111111;
        --box-bg: #ffffff;
        --box-border: rgba(0,0,0,0.08);
        --box-shadow: 0 6px 18px rgba(0,0,0,0.06);
        --button-bg: linear-gradient(180deg,#ffb400,#e09a00);
        --button-text: #111;
        --table-header-bg: #eee;
        --breakdown-bg: #fff;
        --breakdown-border: #ddd;
    }
    /* Default (light) theme box styling so expanders and containers are visibly elevated */
    .stExpander, .streamlit-expander, details[role="group"] > summary, .stExpander > div, .st-expander, .css-1lcbmhc { 
        background: var(--box-bg) !important;
        border: 1px solid var(--box-border) !important;
        box-shadow: var(--box-shadow) !important;
        border-radius: 8px !important;
        color: var(--text-color) !important;
    }
    /* Make inputs clear and boxed in light mode */
    input, textarea, select, .stTextInput>div>input, .stNumberInput>div>input, .stTextArea>div>textarea {
        background: var(--box-bg) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--box-border) !important;
        box-shadow: none !important;
        padding: 6px 8px !important;
        border-radius: 6px !important;
    }
    /* Buttons: Orange-yellow mix (Mars/Orange blended) with dark text */
    .stButton>button, .stDownloadButton>button { background: var(--button-bg) !important; color: var(--button-text) !important; border: 1px solid #e09a00 !important; box-shadow: 0 6px 16px rgba(0,0,0,0.12) !important; border-radius:6px !important; padding:6px 12px !important; }
    .stButton>button * , .stDownloadButton>button * { background: transparent !important; color: inherit !important; }
    .stButton>button:hover, .stDownloadButton>button:hover { filter:brightness(0.98) !important; }
    .stButton>button:active, .stDownloadButton>button:active { transform: translateY(1px) !important; }
    .stButton>button:focus, .stDownloadButton>button:focus { outline: none !important; box-shadow: 0 0 0 3px rgba(255,180,0,0.16) !important; }

    /* Dataframes, tables and common elements should honor the theme variables (fixes pages that still render light) */
    [data-testid="stDataFrame"], .stDataFrame, .stTable, .element-container, div[data-testid="stTable"] {
        background: var(--box-bg) !important;
        color: var(--text-color) !important;
    }
    .stDataFrame div[role="grid"], .stDataFrame table, .stTable table { background: var(--box-bg) !important; color: var(--text-color) !important; }
    .stDataFrame th, .stDataFrame td, .stTable th, .stTable td { background: transparent !important; color: var(--text-color) !important; border-color: var(--box-border) !important; }

    /* Fallback for inline styles that hard-code white backgrounds */
    *[style*="#fff"], *[style*="#ffffff"], *[style*="#f7faff"], *[style*="#f0f2f6"] {
        background: var(--box-bg) !important;
        color: var(--text-color) !important;
    }

    /* Ensure headings and markdown respect theme colors */
    h1, h2, h3, h4, h5, h6, .stMarkdown { color: var(--text-color) !important; }
    </style>
    """,
    unsafe_allow_html=True,
) 

# Apply per-user theme (loaded from DB) if available. This runs before page routing so the theme applies globally.
try:
    if 'user' in st.session_state and 'theme' not in st.session_state:
        try:
            df_theme = pd.read_sql("SELECT theme FROM benutzer WHERE benutzername = ?", engine, params=(st.session_state.user,))
            if not df_theme.empty and pd.notnull(df_theme['theme'].iloc[0]):
                st.session_state['theme'] = df_theme['theme'].iloc[0]
        except Exception:
            pass
except Exception:
    pass

# If user requested 'black' and we're not on login, set attribute and force overrides as early as possible
if st.session_state.get('theme') == 'black' and st.session_state.get('page') != 'login':
    st.markdown(
        """
        <script>
        (function(){
            try{
                document.documentElement.setAttribute('data-theme','black');
                if(!document.getElementById('theme-force-overrides')){
                    var s = document.createElement('style'); s.id = 'theme-force-overrides';
                    s.innerHTML = 'html[data-theme="black"] *:not(button):not(.stButton *):not(input):not(textarea):not(svg){background:var(--box-bg) !important;color:var(--text-color) !important;border-color:var(--box-border) !important;} html[data-theme="black"] th, html[data-theme="black"] .scroll-table th { background: var(--table-header-bg) !important; color: var(--text-color) !important; }';
                    document.head.appendChild(s);
                }
            }catch(e){}
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

# Dark-mode rules applied when the document root has data-theme="black". This keeps CSS present for all pages but only active when the client sets the attribute (we'll set the attribute via JS, excluding the login page).
st.markdown(
    """
    <style>
    /* Apply all dark theme variable overrides when html has data-theme="black" */
    html[data-theme="black"] {
        --app-bg: #121212;
        --text-color: #eaeaea;
        --box-bg: #1e1e1e;
        --box-border: rgba(255,255,255,0.06);
        --box-shadow: 0 8px 24px rgba(0,0,0,0.6);
        --button-bg: linear-gradient(180deg,#ffb400,#e09a00);
        --button-text: #111;
        --table-header-bg: #1b1b1b;
        --breakdown-bg: #1e1e1e;
        --breakdown-border: rgba(255,255,255,0.06);
    }
    /* Ensure UI elements look dark when data-theme="black" is set */
    html[data-theme="black"], html[data-theme="black"] body, html[data-theme="black"] .stApp, html[data-theme="black"] .block-container, html[data-theme="black"] [data-testid="stMarkdownContainer"] {
        background: var(--app-bg) !important;
        color: var(--text-color) !important;
    }
    html[data-theme="black"] a, html[data-theme="black"] a:link, html[data-theme="black"] a:visited { color: #ffb400 !important; }
    html[data-theme="black"] .stExpander, html[data-theme="black"] .streamlit-expander, html[data-theme="black"] details[role="group"] > summary, html[data-theme="black"] .stExpander > div, html[data-theme="black"] .st-expander, html[data-theme="black"] .css-1lcbmhc {
        background: var(--box-bg) !important;
        color: var(--text-color) !important;
        border: 1px solid var(--box-border) !important;
        box-shadow: var(--box-shadow) !important;
        border-radius: 8px !important;
    }
    html[data-theme="black"] .stButton>button, html[data-theme="black"] .stDownloadButton>button, html[data-theme="black"] button, html[data-theme="black"] input[type="button"], html[data-theme="black"] input[type="submit"] {
        background: var(--button-bg) !important; color: var(--button-text) !important; border: 1px solid #e09a00 !important; box-shadow: 0 6px 16px rgba(0,0,0,0.6) !important; border-radius:6px !important; padding:6px 12px !important;
    }
    html[data-theme="black"] .stButton>button * , html[data-theme="black"] .stDownloadButton>button * { background: transparent !important; color: inherit !important; }
    html[data-theme="black"] .stButton>button:hover, html[data-theme="black"] .stDownloadButton>button:hover, html[data-theme="black"] button:hover, html[data-theme="black"] input[type="button"]:hover, html[data-theme="black"] input[type="submit"]:hover { filter: brightness(0.95) !important; }
    html[data-theme="black"] .stButton>button:active, html[data-theme="black"] .stDownloadButton>button:active, html[data-theme="black"] button:active { transform: translateY(1px) !important; }
    html[data-theme="black"] .stButton>button:focus, html[data-theme="black"] .stDownloadButton>button:focus, html[data-theme="black"] button:focus { outline: none !important; box-shadow: 0 0 0 4px rgba(255,180,0,0.12) !important; }
    html[data-theme="black"] .stTextInput>div>input, html[data-theme="black"] .stNumberInput>div>input, html[data-theme="black"] .stTextArea>div>textarea, html[data-theme="black"] input, html[data-theme="black"] textarea, html[data-theme="black"] select, html[data-theme="black"] .stSelectbox {
        background: #1b1b1b !important; color: var(--text-color) !important; border: 1px solid var(--box-border) !important; box-shadow: none !important; outline: none !important; padding:6px 8px !important; border-radius:6px !important;
    }
    html[data-theme="black"] table, html[data-theme="black"] th, html[data-theme="black"] td { border-color: var(--box-border) !important; color: var(--text-color) !important; }
    html[data-theme="black"] .stCheckbox>div, html[data-theme="black"] .stRadio>div { color: var(--text-color) !important; }
    html[data-theme="black"] [data-testid="stDataFrame"], html[data-theme="black"] .stDataFrame, html[data-theme="black"] .stTable, html[data-theme="black"] .element-container, html[data-theme="black"] div[data-testid="stTable"] { background: var(--box-bg) !important; color: var(--text-color) !important; }
    html[data-theme="black"] .stDataFrame div[role="grid"], html[data-theme="black"] .stDataFrame table, html[data-theme="black"] .stTable table { background: var(--box-bg) !important; }
    html[data-theme="black"] .stDataFrame th, html[data-theme="black"] .stDataFrame td, html[data-theme="black"] .stTable th, html[data-theme="black"] .stTable td { background: transparent !important; color: var(--text-color) !important; border-color: var(--box-border) !important; }
    html[data-theme="black"] .js-plotly-plot, html[data-theme="black"] .plotly, html[data-theme="black"] .stPlotlyChart, html[data-theme="black"] div[data-testid="stPlotlyChart"] svg, html[data-theme="black"] div[data-testid="stPlotlyChart"] canvas { background: transparent !important; }
    /* Also target SVG rects and backgrounds used by Plotly and other svg-based components */
    html[data-theme="black"] div[data-testid="stPlotlyChart"] svg rect, html[data-theme="black"] svg rect { fill: var(--box-bg) !important; background: transparent !important; }
    html[data-theme="black"] canvas { background: transparent !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# Ensure the theme variables are applied at the document root via JS (overrides page-level inline CSS)
# Also add a small dev sidebar link so the Theme Debug page is reachable from anywhere for testing
if st.session_state.get('user'):
    # Theme Debug buttons/links removed — diagnostics shown on the Einstellungen page
    pass

st.markdown(
    f"""
    <script>
    (function(){{
        try{{
            var stored = localStorage.getItem('app_theme');
            var page = "{st.session_state.get('page','')}";
            var theme = (page === 'login') ? 'white' : (stored || "{st.session_state.get('theme','white')}");
            var root = document.documentElement;
            // Apply data-theme attribute (skip on login) so CSS selectors prefixed with [data-theme="black"] work globally
            if(page !== 'login'){
                var applied = (theme === 'black');
                if(applied) root.setAttribute('data-theme', 'black'); else root.removeAttribute('data-theme');
            } else {
                root.removeAttribute('data-theme');
            }
            // Force inject an override style when dark theme is active so pages that add late inline styles are covered
            var forceId = 'theme-force-overrides';
            function ensureForceStyles(applied){
                var existing = document.getElementById(forceId);
                if(applied){
                    // Stronger set of selectors to catch inline styles and common white/bg patterns
                    var css = ''+
                        'html[data-theme="black"] *:not(button):not(.stButton *):not(input):not(textarea):not(svg){background:var(--box-bg) !important;color:var(--text-color) !important;border-color:var(--box-border) !important;}'+
                        'html[data-theme="black"] th, html[data-theme="black"] .scroll-table th { background: var(--table-header-bg) !important; color: var(--text-color) !important; }'+
                        'html[data-theme="black"] .scroll-table, html[data-theme="black"] .scroll-table-wrapper, html[data-theme="black"] .stDataFrame, html[data-theme="black"] .stTable, html[data-theme="black"] [data-testid="stDataFrame"] { background: var(--box-bg) !important; color: var(--text-color) !important; }'+
                        'html[data-theme="black"] .scroll-table th, html[data-theme="black"] .scroll-table td { color: var(--text-color) !important; border-color: var(--box-border) !important; }'+
                        'html[data-theme="black"] .stExpander, html[data-theme="black"] .streamlit-expander, html[data-theme="black"] .stExpander > div, html[data-theme="black"] .st-expander { background: var(--box-bg) !important; color: var(--text-color) !important; }'+
                        'html[data-theme="black"] .option-menu, html[data-theme="black"] .option-menu li, html[data-theme="black"] .option-menu a, html[data-theme="black"] .option-menu .nav { background: var(--box-bg) !important; color: var(--text-color) !important; }'+
                        'html[data-theme="black"] *[style*="#fff" i], html[data-theme="black"] *[style*="#ffffff" i], html[data-theme="black"] *[style*="rgb(255,255,255)" i], html[data-theme="black"] *[style*="background: white" i], html[data-theme="black"] *[style*="background:#ffffff" i], html[data-theme="black"] *[style*="#ccc" i], html[data-theme="black"] *[style*="#ddd" i], html[data-theme="black"] *[style*="#cccccc" i] { background: var(--box-bg) !important; color: var(--text-color) !important; }'+
                        'html[data-theme="black"] div[data-testid="stPlotlyChart"], html[data-theme="black"] .js-plotly-plot, html[data-theme="black"] .js-plotly-plot svg, html[data-theme="black"] .js-plotly-plot canvas { background: var(--box-bg) !important; }'+
                        'html[data-theme="black"] div[data-testid="stPlotlyChart"] svg rect, html[data-theme="black"] div[data-testid="stPlotlyChart"] canvas, html[data-theme="black"] svg rect { fill: var(--box-bg) !important; background: transparent !important; }'+
                        'html[data-theme="black"] .stButton>button, html[data-theme="black"] .stDownloadButton>button, html[data-theme="black"] button, html[data-theme="black"] input[type="button"], html[data-theme="black"] input[type="submit"] { background: var(--button-bg) !important; color: var(--button-text) !important; }';
                    if(!existing){
                        var s = document.createElement('style'); s.id = forceId; s.innerHTML = css; document.head.appendChild(s);
                    } else { existing.innerHTML = css; }

                    // Also perform a per-node fix for elements whose effective background is very light (walk parents)
                    function isVeryLightComputed(bg){
                        if(!bg) return false;
                        var m = bg.match(/\d+/g);
                        if(!m) return false;
                        var r = parseInt(m[0],10), g = parseInt(m[1],10), b = parseInt(m[2],10);
                        return r >= 200 && g >= 200 && b >= 200; // slightly less strict to catch faint whites
                    }
                    function effectiveBackground(el){
                        try{
                            var cur = el;
                            while(cur && cur !== document && cur.nodeType === 1){
                                var cs = window.getComputedStyle(cur);
                                var bg = cs && (cs.backgroundColor || cs.background);
                                if(bg && bg !== 'transparent' && !(bg.match(/rgba\(\s*0,\s*0,\s*0,\s*0\)/))) return bg;
                                cur = cur.parentElement;
                            }
                        }catch(e){}
                        return null;
                    }
                    function scanAndFix(){
                        try{
                            var nodes = document.querySelectorAll('*');
                            var results = [];
                            var fixedCount = 0;
                            for(var i=0;i<nodes.length;i++){
                                var el = nodes[i];
                                try{
                                    var bg = effectiveBackground(el);
                                    // fallback to direct computed style (for svg/canvas)
                                    if(!bg){ var cs2 = window.getComputedStyle(el); bg = cs2 && (cs2.backgroundColor || cs2.background); }
                                    if(isVeryLightComputed(bg)){
                                        // Record a selector sample for diagnostics
                                        try{ results.push({sel: selectorFor(el), bg: bg}); }catch(e){}
                                        // Only apply once per element
                                        try{
                                            if(!el.dataset || el.dataset.themeFixed !== '1'){
                                                // Force inline CSS using CSS vars with !important
                                                el.style.setProperty('background','var(--box-bg)','important');
                                                el.style.setProperty('color','var(--text-color)','important');
                                                el.style.setProperty('border-color','var(--box-border)','important');
                                                // Visual marker so the user can see the fixed elements on the page
                                                el.style.setProperty('outline','3px dashed rgba(255,180,0,0.95)','important');
                                                if(el.dataset) el.dataset.themeFixed = '1';
                                                fixedCount++;
                                            }
                                        }catch(e){}
                                    }
                                    // Special handling for svg/canvas elements which may not expose computed background
                                    if(el.tagName && (el.tagName.toLowerCase() === 'svg' || el.tagName.toLowerCase() === 'canvas')){
                                        try{
                                            el.style.background = 'var(--box-bg)';
                                            el.style.color = 'var(--text-color)';
                                            if(el.tagName.toLowerCase() === 'svg'){
                                                // try to colour rects (plotly etc)
                                                var rects = el.querySelectorAll('rect');
                                                for(var ri=0; ri<rects.length; ri++){
                                                    rects[ri].style.fill = 'var(--box-bg)';
                                                }
                                            }
                                        }catch(e){}
                                    }
                                }catch(e){}
                                if(results.length>60) break;
                            }

                            // Persist a compact summary for cross-page visibility
                            try{
                                var rootTheme = document.documentElement.getAttribute('data-theme') || 'none';
                                var rootAppBg = getComputedStyle(document.documentElement).getPropertyValue('--app-bg') || '';
                                var summary = { rootTheme: rootTheme, appBg: rootAppBg, issues: results.slice(0,12), fixed: fixedCount };
                                localStorage.setItem('app_theme_debug', JSON.stringify(summary));
                            }catch(e){/* ignore localStorage errors */}
                            // Run a couple of delayed retries to catch late-rendered elements
                            setTimeout(scanAndFix, 250);
                            setTimeout(scanAndFix, 800);
                            setTimeout(scanAndFix, 2000);

                            // Update or create a small global badge that shows status and links to settings
                            try{
                                var badge = document.getElementById('theme-debug-badge');
                                if(!badge){
                                    badge = document.createElement('div'); badge.id = 'theme-debug-badge';
                                    badge.style.position = 'fixed'; badge.style.bottom = '12px'; badge.style.right = '12px'; badge.style.zIndex = 2147483647;
                                    badge.style.padding = '8px 12px'; badge.style.borderRadius = '10px'; badge.style.boxShadow = '0 14px 40px rgba(0,0,0,0.4)';
                                    badge.style.fontSize = '13px'; badge.style.cursor = 'pointer'; badge.style.opacity = '0.98'; badge.style.backdropFilter = 'blur(5px)';
                                    document.body.appendChild(badge);
                                    badge.setAttribute('aria-live','polite'); badge.setAttribute('role','status');
                                    badge.addEventListener('click', function(){ window.location = '?page=einstellungen'; });
                                }
                                if(results.length===0){ badge.style.background = 'linear-gradient(180deg,#2ecc71,#27ae60)'; badge.style.color = '#041'; badge.innerText = 'Theme OK'; badge.title = 'No theme issues detected'; }
                                else{ badge.style.background = 'linear-gradient(180deg,#ffb400,#e09a00)'; badge.style.color = '#111'; badge.innerText = 'Fixed: ' + fixedCount + ' • Issues: ' + results.length + ' — Click to open Einstellungen'; badge.title = 'Fixed: ' + fixedCount + ' • Issues: ' + results.length; }
                            }catch(e){/* ignore */}

                        }catch(e){console.warn('scanAndFix failed', e);}                        
                    }
                    // Debounced observer to catch dynamic changes
                    var scanTimeout = null;
                    function scheduleScan(){ if(scanTimeout) clearTimeout(scanTimeout); scanTimeout = setTimeout(scanAndFix, 120); }
                    scanAndFix();
                    // expose helper for manual debugging in console
                    try{ window.__app_scan_and_fix = scanAndFix; window.__app_theme_summary = function(){ try{ return JSON.parse(localStorage.getItem('app_theme_debug')); }catch(e){return null;} }; }catch(e){}

                    try{
                        // Observe attribute/style changes and child additions
                        var bodyObserver = new MutationObserver(function(mutations){ scheduleScan(); });
                        bodyObserver.observe(document.body || document.documentElement, {childList:true, subtree:true, attributes:true, attributeFilter:['style','class']});
                        // Also observe head for new style tags that might be injected later
                        var headObserver = new MutationObserver(function(muts){ scheduleScan(); });
                        headObserver.observe(document.head || document.documentElement, {childList:true, subtree:true});
                    }catch(e){/* ignore if MutationObserver not supported */}
                } else {
                    if(existing) existing.parentNode.removeChild(existing);
                }
            }
            if (theme === 'black') {{
                ensureForceStyles(true);
                root.style.setProperty('--app-bg', '#121212');
                root.style.setProperty('--text-color', '#eaeaea');
                root.style.setProperty('--box-bg', '#1e1e1e');
                root.style.setProperty('--box-border', 'rgba(255,255,255,0.06)');
                root.style.setProperty('--box-shadow','0 8px 24px rgba(0,0,0,0.6)');
                root.style.setProperty('--button-bg', 'linear-gradient(180deg,#ffb400,#e09a00)');
                root.style.setProperty('--button-text', '#111');
                root.style.setProperty('--table-header-bg', '#1b1b1b');
                root.style.setProperty('--breakdown-bg', '#1e1e1e');
                root.style.setProperty('--breakdown-border', 'rgba(255,255,255,0.06)');
                document.body.style.background = 'var(--app-bg)';
                document.body.style.color = 'var(--text-color)';
            }} else {{
                ensureForceStyles(false);
                root.style.setProperty('--app-bg', '#ffffff');
                root.style.setProperty('--text-color', '#111111');
                root.style.setProperty('--box-bg', '#ffffff');
                root.style.setProperty('--box-border', 'rgba(0,0,0,0.08)');
                root.style.setProperty('--box-shadow', '0 6px 18px rgba(0,0,0,0.06)');
                root.style.setProperty('--button-bg', 'linear-gradient(180deg,#ffb400,#e09a00)');
                root.style.setProperty('--button-text', '#111');
                root.style.setProperty('--table-header-bg', '#eee');
                root.style.setProperty('--breakdown-bg', '#fff');
                root.style.setProperty('--breakdown-border', '#ddd');
                document.body.style.background = 'var(--app-bg)';
                document.body.style.color = 'var(--text-color)';
            }}
        }}catch(e){{}}
    }})();
    </script>
    """,
    unsafe_allow_html=True,
)

# Post-render DOM fixer: replace inline/light backgrounds with theme variables and observe dynamic DOM changes
st.markdown(
    """
    <script>
    (function(){
        function isVeryLight(rgbStr){
            if(!rgbStr) return false;
            var m = rgbStr.match(/\d+/g);
            if(!m) return false;
            var r = parseInt(m[0],10), g = parseInt(m[1],10), b = parseInt(m[2],10);
            return r >= 220 && g >= 220 && b >= 220;
        }
        function fixElement(el){
            try{
                if(!el || el.matches && el.matches('button, input[type="button"], input[type="submit"], .stButton *')) return;
                var cs = window.getComputedStyle(el);
                var bg = cs && cs.backgroundColor;
                // If computed background is very light (likely white/light) override to theme vars
                if(isVeryLight(bg) || /linear-gradient|gradient/i.test(cs.backgroundImage || '')){
                    el.style.setProperty('background', 'var(--box-bg)', 'important');
                    el.style.setProperty('color', 'var(--text-color)', 'important');
                }
                // If inline style contains a hard-coded light hex color, replace it
                var inline = el.getAttribute && el.getAttribute('style') || '';
                if(/background\s*:\s*#(?:f7f7ff|f7faff|f0f2f6|ffffff|fff|fffafa)\b/i.test(inline) || /background-color\s*:\s*#(?:f7f7ff|f7faff|f0f2f6|ffffff|fff)\b/i.test(inline)){
                    el.style.setProperty('background', 'var(--box-bg)', 'important');
                    el.style.setProperty('color', 'var(--text-color)', 'important');
                }
                // Table header fallback
                if(el.matches && (el.matches('th') || el.classList.contains('scroll-table'))) {
                    el.style.setProperty('background', 'var(--table-header-bg)', 'important');
                    el.style.setProperty('color', 'var(--text-color)', 'important');
                }
            }catch(e){}
        }
        function scanAndFix(root){
            try{
                var nodes = (root || document).querySelectorAll('*');
                for(var i=0;i<nodes.length;i++) fixElement(nodes[i]);
            }catch(e){}
        }
        // Initial quick pass
        setTimeout(function(){ scanAndFix(document); }, 50);
        // Re-run a few times in case elements appear a bit later
        var tries=0, maxTries=6;
        var interval = setInterval(function(){ scanAndFix(document); tries++; if(tries>maxTries) clearInterval(interval); }, 250);
        // Observe DOM mutations for dynamic additions/changes
        var mo = new MutationObserver(function(mutations){
            try{
                var needFullScan = false;
                mutations.forEach(function(m){
                    if(m.addedNodes && m.addedNodes.length){
                        m.addedNodes.forEach(function(n){
                            if(n.nodeType===1){
                                var tag = (n.tagName || '').toLowerCase();
                                // If a new <style> is added, it may affect many existing elements — trigger full scan
                                if(tag === 'style'){
                                    needFullScan = true;
                                } else {
                                    scanAndFix(n);
                                }
                            }
                        });
                    }
                    if(m.type === 'attributes' && m.target){
                        var t = (m.target && m.target.tagName || '').toLowerCase();
                        if(t === 'style'){
                            needFullScan = true;
                        } else {
                            fixElement(m.target);
                        }
                    }
                });
                if(needFullScan) scanAndFix(document);
            }catch(e){}
        });
        mo.observe(document.documentElement || document.body, { childList:true, subtree:true, attributes:true, attributeFilter:['style','class'] });
    })();
    </script>
    """,
    unsafe_allow_html=True,
)

# Theme debug page: renders canonical components and runs a JS scan to identify elements with very light backgrounds
def theme_debug_page():
    st.set_page_config(page_title="Theme Debug", layout="centered")
    st.title("🔧 Theme Debugger")
    st.info("Shows representative components and highlights elements with very light computed backgrounds so we can pinpoint remaining white areas.")
    st.write(f"Current page: `{st.session_state.get('page')}` — User: `{st.session_state.get('user', 'None')}` — Theme: `{st.session_state.get('theme','white')}`")
    st.write("(If you see a login redirect after clicking the Theme Debug button, this page should still load — if it doesn't, please tell me the exact sequence you used.)")

    st.header("Controls")
    col1, col2 = st.columns([1,3])
    with col1:
        if st.button("🔄 Rescan", key="theme_debug_rescan"):
            st.rerun()
    with col2:
        st.write("Use the rescan button after navigation to other pages to refresh scan results.")

    st.header("Components")
    st.write("Buttons:")
    st.button("Standard Button")
    st.download_button("Download", data="data", file_name="x.txt")

    st.write("Inputs:")
    st.text_input("Text input")
    st.number_input("Number input", value=3)
    st.text_area("Text area")

    st.write("Expander and Table:")
    with st.expander("Sample Expander"):
        st.write("Expander inner content")
    import pandas as _pd
    st.dataframe(_pd.DataFrame({"A": [1,2,3], "B": ["x","y","z"]}))

    st.write("Raw HTML table example (forces header bg):")
    st.markdown(
        """
        <div class="scroll-table-wrapper">
        <table class="scroll-table" id="debug-table">
        <thead>
        <tr><th>H1</th><th>H2</th></tr>
        </thead>
        <tbody>
        <tr><td>1</td><td>2</td></tr>
        <tr><td>3</td><td>4</td></tr>
        </tbody>
        </table>
        </div>
        <div id="theme-debug-results" style="margin-top:12px;padding:8px;border:1px dashed rgba(255,180,0,0.2);border-radius:6px;background:var(--box-bg);color:var(--text-color)"></div>
        """,
        unsafe_allow_html=True,
    )

    # JS scanner: find elements with very light computed background and list/select them
    st.markdown(
        """
        <script>
        (function(){
            function isVeryLight(rgbStr){
                if(!rgbStr) return false;
                var m = rgbStr.match(/\d+/g);
                if(!m) return false;
                var r = parseInt(m[0],10), g = parseInt(m[1],10), b = parseInt(m[2],10);
                return r >= 220 && g >= 220 && b >= 220;
            }
            function selectorFor(el){
                try{
                    if(el.id) return el.tagName.toLowerCase() + '#' + el.id;
                    if(el.classList && el.classList.length) return el.tagName.toLowerCase() + '.' + el.classList[0];
                    return el.tagName.toLowerCase();
                }catch(e){return el.tagName.toLowerCase();}
            }
            var nodes = document.querySelectorAll('*');
            var results = [];
            for(var i=0;i<nodes.length;i++){
                var el = nodes[i];
                try{
                    var cs = window.getComputedStyle(el);
                    var bg = cs && (cs.backgroundColor || cs.background);
                    if(isVeryLight(bg)){
                        results.push({sel: selectorFor(el), bg: bg});
                        el.style.outline = '3px solid rgba(255,0,0,0.6)';
                    }
                }catch(e){}
                if(results.length>60) break;
            }
            var container = document.getElementById('theme-debug-results');
            if(container){
                var rootTheme = document.documentElement.getAttribute('data-theme') || 'none';
                var rootAppBg = getComputedStyle(document.documentElement).getPropertyValue('--app-bg') || '';
                var infoHtml = '<div><strong>Client root data-theme:</strong> ' + rootTheme + ' — <strong>--app-bg:</strong> ' + rootAppBg + '</div>';
                if(results.length===0){ container.innerHTML = infoHtml + '<div style="margin-top:6px">✅ No very-light backgrounds detected</div>'; }
                else{
                    container.innerHTML = infoHtml + '<div style="margin-top:6px">⚠️ Detected elements with light backgrounds (highlighted)</div><ul>' + results.map(function(r){ return '<li><code>'+r.sel+'</code> — <small>'+r.bg+'</small></li>'; }).join('') + '</ul>';
                }
            }
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )


# Allow page navigation via URL query param (e.g., ?page=theme_debug)
try:
    # Use the modern st.query_params API (avoid mixing experimental API calls with st.query_params)
    params = st.query_params
    if 'page' in params and params['page']:
        st.session_state.page = params['page'][0]
except Exception:
    pass

# Set default page if not set
if 'page' not in st.session_state:
    st.session_state.page = "login"

# Routing basierend auf session state
# Theme debug should be reachable even if other checks might redirect to login — handle it first
if st.session_state.page == "theme_debug":
    theme_debug_page()
elif st.session_state.page == "login":
    login_page()
elif st.session_state.page == "mitarbeiter_projekt_auswahl":
    mitarbeiter_projekt_auswahl_page()
elif st.session_state.page == "mitarbeiter":
    mitarbeiter_page()
elif st.session_state.page == "app":
    bau_app_page()
elif st.session_state.page == "profil":
    profil_page()
elif st.session_state.page == "einstellungen":
    settings_page()
elif st.session_state.page == "projekt_auswahl":
    mitarbeiter_projekt_auswahl_page()
elif st.session_state.page == "dev_auth":
    dev_auth_page()
elif st.session_state.page == "dev":
    dev_page()
else:
    # Fallback: wenn page nicht erkannt, zum Login
    st.session_state.page = "login"
    st.rerun()