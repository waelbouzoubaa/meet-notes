"""KaptNotes — Streamlit Interface — Ramery Edition."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))

from processor import (
    list_templates,
    load_template,
    save_template,
    extract_speakers,
    apply_speaker_names,
    build_system_prompt,
    save_output,
)
from transcribe import transcribe_audio
from summarize import summarize_transcript
from pdf_export import generate_pdf
from docx_export import generate_docx
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="KaptNotes — Ramery",
    page_icon="assets/favicon_round.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Logo loader ────────────────────────────────────────────────────────────────
ASSETS_DIR = Path(__file__).parent / "assets"
LOGO_PATH  = next(
    (ASSETS_DIR / f for f in ["logo.png", "logo.jpg", "logo.jpeg", "logo.svg"]
     if (ASSETS_DIR / f).exists()),
    None,
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Base dark ── */
html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #E2E8F0;
}
.stApp { background: #0A1628 !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #193C6C !important;
    border-right: 1px solid rgba(255,255,255,0.06) !important;
}
[data-testid="stSidebar"] * { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.08) !important; margin: 0.7rem 0 !important; }
[data-testid="stSidebar"] .stCaption p { color: rgba(255,255,255,0.38) !important; font-size: 0.73rem !important; }
[data-testid="stSidebar"] label {
    font-size: 0.65rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1px !important;
    color: rgba(255,255,255,0.35) !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] > div > div,
[data-testid="stSidebar"] [data-testid="stTextInput"] input,
[data-testid="stSidebar"] textarea {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(255,255,255,0.12) !important;
    color: #E2E8F0 !important;
    border-radius: 7px !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.14) !important;
    color: #E2E8F0 !important;
    border-radius: 7px !important;
    font-size: 0.82rem !important;
    width: 100% !important;
    margin-top: 0.2rem !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: rgba(255,255,255,0.13) !important;
}

/* ── Logo zone ── */
.sidebar-logo {
    padding: 1.2rem 1.2rem 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.12);
    margin-bottom: 0.8rem;
    background: transparent;
}
.sidebar-logo-title {
    font-size: 1rem;
    font-weight: 700;
    color: #fff !important;
    letter-spacing: -0.2px;
    margin: 0.5rem 0 0;
}
.sidebar-logo-sub {
    font-size: 0.65rem;
    color: rgba(255,255,255,0.35) !important;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin: 2px 0 0;
}
.sidebar-logo-bar { width: 22px; height: 2px; background: #D32422; border-radius: 2px; margin-top: 6px; }

/* ── Hero ── */
.hero {
    background: #0F2035;
    border-radius: 10px;
    padding: 1rem 1.6rem;
    margin-bottom: 1.4rem;
    border-left: 4px solid #D32422;
    display: flex;
    align-items: center;
    gap: 1.4rem;
}
.hero-left { flex: 1; min-width: 0; }
.hero-eyebrow {
    font-size: 0.62rem;
    font-weight: 700;
    color: #D32422;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 2px;
}
.hero-title {
    font-size: 1.3rem;
    font-weight: 700;
    color: #F1F5F9;
    margin: 0;
    letter-spacing: -0.3px;
}
.hero-sub { font-size: 0.8rem; color: #64748B; margin: 2px 0 0; }
.hero-badge {
    background: rgba(211,36,34,0.12);
    border: 1px solid rgba(211,36,34,0.3);
    border-radius: 8px;
    padding: 0.5rem 1.1rem;
    text-align: center;
    flex-shrink: 0;
}
.hero-badge-val { font-size: 1rem; font-weight: 700; color: #F47A7A; display: block; }
.hero-badge-lbl { font-size: 0.6rem; color: #64748B; text-transform: uppercase; letter-spacing: 0.6px; }

/* ── Stepper ── */
.stepper-wrap {
    display: flex;
    align-items: flex-start;
    justify-content: center;
    margin: 0 auto 1.8rem;
    max-width: 700px;
    padding: 0 1rem;
}
.step-item {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 7px;
    min-width: 80px;
}
.step-icon {
    width: 40px; height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    font-weight: 700;
    flex-shrink: 0;
}
.step-icon-done    { background: #2563A8; color: #fff; }
.step-icon-active  { background: #D32422; color: #fff; box-shadow: 0 0 14px rgba(211,36,34,0.45); }
.step-icon-pending { background: #162540; color: #4A5568; border: 2px solid #162540; }

.step-label {
    font-size: 0.7rem;
    font-weight: 600;
    text-align: center;
    white-space: nowrap;
}
.step-label-done    { color: #6BAEF5; }
.step-label-active  { color: #F47A7A; }
.step-label-pending { color: #4A5568; }

.step-connector {
    flex: 1;
    height: 2px;
    margin-top: 19px;
    min-width: 30px;
}
.step-connector-done    { background: #2563A8; }
.step-connector-active  { background: linear-gradient(90deg, #2563A8 0%, #D32422 100%); }
.step-connector-pending { background: #162540; }

/* ── Cards ── */
.card {
    background: #0F2035;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.card-label {
    font-size: 0.68rem;
    font-weight: 700;
    color: #4A5568;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 0.6rem;
}

/* ── Info strip ── */
.info-strip {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(37,99,168,0.18);
    border: 1px solid rgba(37,99,168,0.35);
    border-radius: 8px;
    padding: 0.65rem 1rem;
    color: #7BB8F0;
    font-size: 0.85rem;
    margin-bottom: 1rem;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] > div {
    border: 2px dashed rgba(37,99,168,0.35) !important;
    border-radius: 10px !important;
    background: rgba(37,99,168,0.08) !important;
}
[data-testid="stFileUploader"] > div:hover {
    border-color: rgba(211,36,34,0.5) !important;
    background: rgba(211,36,34,0.04) !important;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: #D32422 !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    color: #fff !important;
    padding: 0.5rem 1.4rem !important;
    font-size: 0.9rem !important;
}
.stButton > button[kind="primary"]:hover { opacity: 0.85 !important; }

/* ── Metrics ── */
.metric-tile {
    background: #0F2035;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 10px;
    padding: 0.9rem 1rem;
    text-align: center;
}
.metric-value { font-size: 1.3rem; font-weight: 700; color: #7BB8F0; line-height: 1; margin-bottom: 4px; }
.metric-label { font-size: 0.65rem; color: #4A5568; text-transform: uppercase; letter-spacing: 0.5px; }

/* ── Download btn ── */
[data-testid="stDownloadButton"] > button {
    background: #2563A8 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ── Inputs / textareas ── */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
    background: #0A1628 !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    color: #E2E8F0 !important;
    border-radius: 8px !important;
}

/* ── Data editor ── */
[data-testid="stDataEditor"] {
    background: #0F2035 !important;
    border-radius: 8px !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0F2035 !important;
    border: 1px solid rgba(255,255,255,0.07) !important;
    border-radius: 8px !important;
}
[data-testid="stExpander"] summary { color: #94A3B8 !important; }

/* ── Hide Streamlit toolbar & menu ── */
[data-testid="stToolbar"] { display: none !important; }
#MainMenu { display: none !important; }
header[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
}

/* ── Sidebar collapse button ── */
[data-testid="stSidebarCollapseButton"] svg { fill: rgba(255,255,255,0.6) !important; }
#kapt-sidebar-toggle {
    position: fixed;
    left: 0;
    top: 8px;
    z-index: 999999;
    background: #193C6C;
    color: white;
    border: none;
    border-radius: 0 6px 6px 0;
    padding: 6px 10px;
    font-size: 18px;
    cursor: pointer;
    box-shadow: 3px 0 10px rgba(0,0,0,0.5);
    display: none;
}
body:has([data-testid="stSidebar"][aria-expanded="false"]) #kapt-sidebar-toggle {
    display: block !important;
}

/* ── Divider ── */
hr { border-color: rgba(255,255,255,0.07) !important; }

/* ── Success / info banners ── */
[data-testid="stAlert"] {
    background: rgba(37,99,168,0.15) !important;
    border: 1px solid rgba(37,99,168,0.3) !important;
    border-radius: 8px !important;
    color: #7BB8F0 !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button[data-baseweb="tab"] {
    color: #64748B !important;
    font-weight: 500 !important;
}
[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
    color: #F1F5F9 !important;
    border-bottom-color: #D32422 !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<button id="kapt-sidebar-toggle">☰</button>', unsafe_allow_html=True)

import streamlit.components.v1 as _components
_components.html("""
<script>
var doc = window.parent.document;
function _kaptAttach() {
    var btn = doc.getElementById('kapt-sidebar-toggle');
    if (!btn) { setTimeout(_kaptAttach, 300); return; }
    btn.addEventListener('click', function() {
        var d = doc.querySelector('[data-testid="stSidebarCollapseButton"]');
        var b = d && d.querySelector('button');
        if (b) b.click();
    });
}
_kaptAttach();
</script>
""", height=0)

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "phase": "upload",
    "transcript_raw": "",
    "transcript_named": "",
    "report": "",
    "audio_stem": "",
    "elapsed_transcription": 0.0,
    "selected_template": "socle_commun",
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
ss = st.session_state

# ── Toast persistant après rerun ───────────────────────────────────────────────
if "_toast" in ss:
    _icon, _msg = ss.pop("_toast")
    st.toast(_msg, icon=_icon)

# ── Template metadata ──────────────────────────────────────────────────────────
TEMPLATE_META = {
    "commercial":   ("💼", "Opportunités, engagements clients, prochaines étapes"),
    "chantier":     ("🏗️", "Avancement terrain, blocages, coordination lots"),
    "securite":     ("🦺", "Incidents HSE, actions correctives, responsabilités"),
    "direction":    ("🎯", "Décisions stratégiques, arbitrages, orientations"),
    "suivi_projet": ("📊", "Planning, budget, risques, dépendances"),
    "socle_commun": ("📋", "Socle générique BTP multi-acteurs"),
    "general":      ("📝", "Rapport complet polyvalent"),
    "brainstorm":   ("💡", "Focus créativité et idées"),
    "tech_review":  ("⚙️", "Sprint, architecture, dette technique"),
    "sales":        ("💼", "Signaux client, objections, pipeline"),
    "custom":       ("✏️", "Votre propre prompt système"),
}
def tmeta(t): return TEMPLATE_META.get(t, ("📄", ""))

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    # Logo
    if LOGO_PATH:
        import base64
        logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        ext = LOGO_PATH.suffix.lstrip(".")
        mime = "image/svg+xml" if ext == "svg" else f"image/{ext}"
        st.markdown(f"""
        <div class="sidebar-logo">
            <div style="display:flex;align-items:center;gap:10px;">
                <img src="data:{mime};base64,{logo_b64}"
                     style="width:36px;height:36px;border-radius:50%;object-fit:cover;flex-shrink:0;"/>
                <div>
                    <p class="sidebar-logo-title">Ramery</p>
                    <p class="sidebar-logo-sub">KaptNotes</p>
                </div>
            </div>
            <div class="sidebar-logo-bar"></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sidebar-logo">
            <p class="sidebar-logo-title">🎙 KaptNotes</p>
            <p class="sidebar-logo-sub">Ramery</p>
            <div class="sidebar-logo-bar"></div>
        </div>
        """, unsafe_allow_html=True)

    # Moteur de transcription — AssemblyAI par défaut (sélecteur masqué)
    engine = "assemblyai"
    # Pour réactiver le choix, décommente le bloc ci-dessous :
    # st.markdown('<p style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.35);margin-bottom:0.3rem">Moteur de transcription</p>', unsafe_allow_html=True)
    # engine = st.selectbox(
    #     "Moteur",
    #     options=["gemini", "assemblyai"],
    #     format_func=lambda x: "🤖  Gemini Flash" if x == "gemini" else "🎙  AssemblyAI",
    #     label_visibility="collapsed",
    #     key="engine_select",
    # )

    # Langue
    st.markdown('<p style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.35);margin-bottom:0.3rem">Langue</p>', unsafe_allow_html=True)
    language = st.selectbox("Langue", options=["fr", "en"],
        format_func=lambda x: "🇫🇷  Français" if x == "fr" else "🇬🇧  English",
        label_visibility="collapsed")

    st.divider()

    # Template
    st.markdown('<p style="font-size:0.65rem;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:rgba(255,255,255,0.35);margin-bottom:0.3rem">Template de rapport</p>', unsafe_allow_html=True)
    available_templates = list_templates()
    template_labels = {t: f"{tmeta(t)[0]}  {t.replace('_', ' ').title()}" for t in available_templates}

    selected_template = st.selectbox("Template", options=available_templates,
        format_func=lambda t: template_labels.get(t, t),
        label_visibility="collapsed",
        index=available_templates.index(ss.get("selected_template", "socle_commun"))
              if ss.get("selected_template", "socle_commun") in available_templates else 0,
        key="selected_template")

    st.caption(tmeta(selected_template)[1])

    _BUILTIN_TEMPLATES = {"socle_commun", "chantier", "securite", "direction", "suivi_projet", "commerciale"}

    if selected_template == "custom":
        # Pre-fill with socle_commun so the user can just tweak it
        try:
            _default_prompt = load_template("socle_commun")
        except FileNotFoundError:
            _default_prompt = "Tu es un assistant de réunion professionnel. Résume le transcript en Markdown."

        custom_prompt_text = st.text_area("Prompt système", height=200,
            value=_default_prompt,
            label_visibility="visible")

        st.caption("Modifiez le prompt ci-dessus puis enregistrez-le comme nouveau template.")
        _new_name = st.text_input("Nom du template", placeholder="ex: réunion_chantier_v2",
            label_visibility="visible")
        if st.button("💾  Enregistrer comme template", use_container_width=True):
            _clean = _new_name.strip().lower().replace(" ", "_")
            if not _clean:
                st.warning("Saisissez un nom avant d'enregistrer.")
            elif _clean in _BUILTIN_TEMPLATES:
                st.error("Ce nom est réservé à un template intégré.")
            else:
                save_template(_clean, custom_prompt_text)
                ss["_toast"] = ("✅", f"Template « {_clean} » enregistré !")
                st.rerun()
    else:
        custom_prompt_text = ""
        if selected_template in _BUILTIN_TEMPLATES:
            # Lecture seule pour les templates intégrés
            with st.expander("Voir le prompt", expanded=False):
                try:
                    st.code(load_template(selected_template), language="text")
                except FileNotFoundError:
                    st.warning("Template introuvable.")
        else:
            # Templates utilisateur : édition + suppression
            try:
                _current_content = load_template(selected_template)
            except FileNotFoundError:
                _current_content = ""
            _edited = st.text_area("Modifier le prompt", height=200,
                value=_current_content, label_visibility="visible")
            col_save, col_del = st.columns(2)
            with col_save:
                if st.button("💾  Enregistrer", use_container_width=True):
                    save_template(selected_template, _edited)
                    ss["_toast"] = ("✅", f"Template « {selected_template} » enregistré !")
                    st.rerun()
            with col_del:
                if st.button("🗑  Supprimer", use_container_width=True, type="secondary"):
                    _tpath = Path(__file__).parent / "templates" / f"{selected_template}.txt"
                    if _tpath.exists():
                        _tpath.unlink()
                    ss["_toast"] = ("🗑", f"Template « {selected_template} » supprimé.")
                    st.rerun()

    onedrive_path = ""

    st.divider()

    if ss.phase == "reported":
        st.button("🔄  Relancer avec un autre template",
            on_click=lambda: ss.update({"phase": "transcribed"}),
            use_container_width=True)
    if ss.phase != "upload":
        st.button("↩  Nouvelle analyse", on_click=lambda: ss.update(defaults),
            use_container_width=True)


# ── Hero ───────────────────────────────────────────────────────────────────────
phase_labels = {"upload": "Upload", "transcribing": "Transcription", "transcribed": "Participants", "reporting": "Rapport", "reported": "Rapport"}
st.markdown(f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-eyebrow">{"AssemblyAI" if engine == "assemblyai" else "Gemini Flash"} · Ramery</div>
    <h1 class="hero-title">KaptNotes</h1>
    <p class="hero-sub">Transcription · Diarisation · Compte rendu automatisé</p>
  </div>
  <div class="hero-badge">
    <span class="hero-badge-val">{phase_labels.get(ss.phase, "—")}</span>
    <span class="hero-badge-lbl">Étape en cours</span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Stepper ────────────────────────────────────────────────────────────────────
STEPS = [
    ("upload",        "📁", "Upload"),
    ("transcribing",  "🎙", "Transcription"),
    ("transcribed",   "👥", "Participants"),
    ("reporting",     "📄", "Rapport"),
]
order = ["upload", "transcribing", "transcribed", "reporting", "reported"]
cur   = order.index(ss.phase) if ss.phase in order else 0

html = '<div class="stepper-wrap">'
for i, (phase, icon, label) in enumerate(STEPS):
    req = order.index(phase)
    if req < cur:
        ic, lc, ico = "step-icon-done",    "step-label-done",    "✓"
    elif req == cur:
        ic, lc, ico = "step-icon-active",  "step-label-active",  icon
    else:
        ic, lc, ico = "step-icon-pending", "step-label-pending", icon

    html += f'<div class="step-item"><div class="step-icon {ic}">{ico}</div><span class="step-label {lc}">{label}</span></div>'

    if i < len(STEPS) - 1:
        if req < cur:     cc = "step-connector-done"
        elif req == cur:  cc = "step-connector-active"
        else:             cc = "step-connector-pending"
        html += f'<div class="step-connector {cc}"></div>'

html += "</div>"
st.markdown(html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1 — Upload
# ══════════════════════════════════════════════════════════════════════════════
if ss.phase == "upload":

    col_upload, col_opts = st.columns([3, 2], gap="large")

    with col_upload:
        st.markdown('<div class="card"><p class="card-label">Source audio</p>', unsafe_allow_html=True)
        tab_upload, tab_record = st.tabs(["📁  Importer un fichier", "🎙  Enregistrer"])

        with tab_upload:
            uploaded_file = st.file_uploader("audio",
                type=["mp3", "wav", "m4a", "mp4", "ogg", "flac", "aac", "webm"],
                label_visibility="collapsed",
                help="Formats acceptés : mp3 · wav · m4a · mp4 · ogg · flac · aac · webm")
            if uploaded_file:
                ss.pop("_rec_bytes", None)
                ss.pop("_rec_ext", None)
            recorded_audio     = None
            recorded_audio_ext = ".webm"

        with tab_record:
            try:
                from streamlit_mic_recorder import mic_recorder
                from datetime import datetime as _dt

                st.caption("Cliquez sur le bouton pour démarrer · Recliquez pour arrêter")

                audio_data = mic_recorder(
                    start_prompt="🎙  Démarrer l'enregistrement",
                    stop_prompt="⏹  Arrêter",
                    just_once=False,
                    use_container_width=True,
                    key="mic",
                )

                if audio_data and audio_data.get("bytes"):
                    recorded_bytes = audio_data["bytes"]
                    rec_id = audio_data.get("id", 0)
                    # Detect real format via magic bytes — don't trust browser's claimed format
                    if recorded_bytes[:4] == b'\x1a\x45\xdf\xa3':
                        _rec_ext, _fmt = ".webm", "audio/webm"
                    elif recorded_bytes[:4] == b'OggS':
                        _rec_ext, _fmt = ".ogg",  "audio/ogg"
                    elif recorded_bytes[:4] == b'RIFF':
                        _rec_ext, _fmt = ".wav",  "audio/wav"
                    elif recorded_bytes[4:8] == b'ftyp':
                        _rec_ext, _fmt = ".mp4",  "audio/mp4"
                    else:
                        _rec_ext, _fmt = ".webm", "audio/webm"
                    # Persist in session state so the value survives the button-click rerun
                    ss["_rec_bytes"] = recorded_bytes
                    ss["_rec_ext"]   = _rec_ext
                    st.audio(recorded_bytes, format=_fmt)

                    # Auto-download to browser on new recording (guard by rec_id to avoid re-trigger on rerun)
                    if rec_id != ss.get("_last_saved_rec_id"):
                        import base64 as _b64
                        rec_filename = f"enregistrement_{_dt.now().strftime('%Y%m%d_%H%M%S')}{_rec_ext}"
                        b64_audio = _b64.b64encode(recorded_bytes).decode()
                        import streamlit.components.v1 as _cv1
                        _cv1.html(f"""
<script>
(function() {{
    var doc = window.parent.document;
    var a = doc.createElement('a');
    a.href = 'data:{_fmt};base64,{b64_audio}';
    a.download = '{rec_filename}';
    a.style.display = 'none';
    doc.body.appendChild(a);
    a.click();
    setTimeout(function() {{ doc.body.removeChild(a); }}, 500);
}})();
</script>
""", height=0)
                        ss["_last_saved_rec_id"] = rec_id
                        ss["_rec_filename"] = rec_filename
                        ss["_rec_fmt"] = _fmt
                        st.success(f"Enregistrement sauvegardé automatiquement : `{rec_filename}`")
                    elif ss.get("_rec_filename"):
                        st.success(f"Enregistrement sauvegardé automatiquement : `{ss['_rec_filename']}`")

                    # Bouton de téléchargement explicite (fallback si auto-download bloqué)
                    _dl_fname = ss.get("_rec_filename", f"enregistrement{_rec_ext}")
                    _dl_fmt   = ss.get("_rec_fmt", _fmt)
                    st.download_button(
                        label=f"⬇  Télécharger l'enregistrement ({_rec_ext})",
                        data=recorded_bytes,
                        file_name=_dl_fname,
                        mime=_dl_fmt,
                        use_container_width=True,
                    )

                    uploaded_file = None

                # Always read from session state so value is correct after rerun
                recorded_audio     = ss.get("_rec_bytes")
                recorded_audio_ext = ss.get("_rec_ext", ".webm")
            except ImportError:
                st.warning("Module `streamlit-mic-recorder` non installé.")
                recorded_audio     = None
                recorded_audio_ext = ".webm"

        st.markdown('</div>', unsafe_allow_html=True)

    with col_opts:
        st.markdown('<div class="card"><p class="card-label">Options</p>', unsafe_allow_html=True)
        extra_context = st.text_area("Contexte additionnel",
            placeholder="Ex : chantier Bordeaux, focus retards lot gros œuvre…",
            height=88, label_visibility="visible")
        uploaded_docs = st.file_uploader(
            "Documents présentés en séance",
            type=["pdf", "pptx", "docx", "txt"],
            accept_multiple_files=True,
            help="PDF · PPTX · DOCX · TXT — texte et images analysés par Gemini",
            label_visibility="visible",
        )
        transcript_only = st.checkbox("Transcription uniquement (sans rapport)", value=False)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Source active : fichier uploadé ou enregistrement ──────────────────────
    audio_source   = uploaded_file or (recorded_audio is not None and recorded_audio)
    audio_is_rec   = recorded_audio is not None and not uploaded_file

    if audio_source:
        if audio_is_rec:
            display_name = f"enregistrement{recorded_audio_ext}"
            size_mb      = len(recorded_audio) / (1024 * 1024)
        else:
            display_name = uploaded_file.name
            size_mb      = uploaded_file.size / (1024 * 1024)

        icon, _ = tmeta(selected_template)
        st.markdown(
            f'<div class="info-strip">📎 <strong>{display_name}</strong>'
            f'&nbsp;·&nbsp;{size_mb:.1f} Mo'
            f'&nbsp;·&nbsp;Template : <strong>{icon} {selected_template.replace("_"," ").title()}</strong></div>',
            unsafe_allow_html=True)

        _required_key = "ASSEMBLYAI_API_KEY" if engine == "assemblyai" else "GEMINI_API_KEY"
        if not os.getenv(_required_key):
            st.error(f"{_required_key} manquante dans le fichier .env")
            st.stop()

        if st.button("▶  Lancer l'analyse", type="primary"):
            if audio_is_rec:
                ss._pending_suffix   = recorded_audio_ext
                ss._pending_bytes    = bytes(recorded_audio)
                ss._pending_stem     = "enregistrement"
            else:
                ss._pending_suffix   = Path(uploaded_file.name).suffix
                ss._pending_bytes    = bytes(uploaded_file.getbuffer())
                ss._pending_stem     = Path(uploaded_file.name).stem
            ss._pending_display  = display_name
            ss._extra_context    = extra_context
            ss._transcript_only  = transcript_only
            ss._pending_engine   = engine
            ss._pending_docs     = [(d.name, bytes(d.getbuffer())) for d in (uploaded_docs or [])]
            ss.phase             = "transcribing"
            st.rerun()
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 1b — Transcription en cours
# ══════════════════════════════════════════════════════════════════════════════
elif ss.phase == "transcribing":
    with tempfile.NamedTemporaryFile(delete=False, suffix=ss._pending_suffix) as tmp:
        tmp.write(ss._pending_bytes)
        tmp_path = Path(tmp.name)
    try:
        _engine = getattr(ss, "_pending_engine", "gemini")
        _engine_label = "AssemblyAI" if _engine == "assemblyai" else "Gemini Files API"
        with st.status("Transcription en cours…", expanded=True) as status:
            st.write(f"Envoi de **{ss._pending_display}** vers {_engine_label}…")
            transcript, elapsed = transcribe_audio(tmp_path, language, engine=_engine)
            status.update(label=f"Transcription terminée en {elapsed:.1f} s",
                state="complete", expanded=False)
    except Exception as e:
        st.error(f"Erreur transcription : {e}")
        tmp_path.unlink(missing_ok=True)
        ss.phase = "upload"
        st.stop()
    finally:
        tmp_path.unlink(missing_ok=True)

    ss.transcript_raw        = transcript
    ss.transcript_named      = transcript
    ss.audio_stem            = ss._pending_stem
    ss.elapsed_transcription = elapsed
    ss.phase                 = "transcribed"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Identification & Rapport
# ══════════════════════════════════════════════════════════════════════════════
elif ss.phase == "transcribed":

    extra_context   = getattr(ss, "_extra_context", "")
    transcript_only = getattr(ss, "_transcript_only", False)

    # Auto-download transcript .txt on first render of this phase
    if ss.get("_transcript_dl_stem") != ss.audio_stem:
        import base64 as _b64
        import streamlit.components.v1 as _cv1
        _txt_b64 = _b64.b64encode(ss.transcript_raw.encode("utf-8")).decode()
        _txt_filename = f"{ss.audio_stem}_transcript.txt"
        _cv1.html(f"""
<script>
(function() {{
    var doc = window.parent.document;
    var a = doc.createElement('a');
    a.href = 'data:text/plain;charset=utf-8;base64,{_txt_b64}';
    a.download = '{_txt_filename}';
    a.style.display = 'none';
    doc.body.appendChild(a);
    a.click();
    setTimeout(function() {{ doc.body.removeChild(a); }}, 500);
}})();
</script>
""", height=0)
        ss["_transcript_dl_stem"] = ss.audio_stem

    speakers   = extract_speakers(ss.transcript_raw)
    word_count = len(ss.transcript_raw.split())
    icon, _    = tmeta(selected_template)

    # Métriques
    c1, c2, c3, c4 = st.columns(4)
    for col, (val, label) in zip([c1, c2, c3, c4], [
        (str(len(speakers)),                                              "Locuteurs"),
        (f"{word_count:,}",                                               "Mots transcrits"),
        (f"{ss.elapsed_transcription:.0f} s",                            "Durée analyse"),
        (f"{icon} {selected_template.replace('_',' ').title()}",         "Template"),
    ]):
        col.markdown(
            f'<div class="metric-tile"><div class="metric-value">{val}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_left, col_right = st.columns([3, 2], gap="large")

    with col_left:
        st.markdown("**Identification des participants**")
        st.caption("Renseignez les vrais noms pour personnaliser le rapport — optionnel.")
        if speakers:
            import pandas as pd
            _id_col = "Identifiant"
            edited_df = st.data_editor(
                pd.DataFrame({_id_col: speakers, "Vrai nom": [""] * len(speakers)}),
                column_config={
                    _id_col: st.column_config.TextColumn(disabled=True),
                    "Vrai nom": st.column_config.TextColumn(max_chars=50),
                },
                hide_index=True, use_container_width=True)
            speaker_map = {
                row[_id_col]: row["Vrai nom"]
                for _, row in edited_df.iterrows()
                if row["Vrai nom"].strip()
            }
        else:
            st.info("Aucun locuteur détecté automatiquement.")
            speaker_map = {}

    with col_right:
        with st.expander("📄  Voir le transcript brut", expanded=False):
            st.text_area("t", value=ss.transcript_raw, height=260,
                disabled=True, label_visibility="collapsed")

    st.markdown("---")

    btn_label = "💾  Enregistrer le transcript" if transcript_only else "▶  Générer le rapport"
    if st.button(btn_label, type="primary"):
        ss.transcript_named = (
            apply_speaker_names(ss.transcript_raw, speaker_map) if speaker_map
            else ss.transcript_raw
        )
        extra_dir = Path(onedrive_path) if onedrive_path.strip() else None
        save_output(ss.transcript_named, ss.audio_stem, "transcript", "MANUAL", extra_dir)

        if transcript_only:
            ss.report = ""
            ss.phase  = "reported"
            st.rerun()
        else:
            ss._pending_template      = selected_template
            ss._pending_extra_context = extra_context
            ss._pending_custom_prompt = custom_prompt_text
            ss.phase                  = "reporting"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2b — Génération du rapport
# ══════════════════════════════════════════════════════════════════════════════
elif ss.phase == "reporting":
    system_prompt = build_system_prompt(
        ss._pending_template,
        ss._pending_extra_context,
        ss._pending_custom_prompt,
    )
    try:
        with st.status("Génération du rapport…", expanded=True) as status:
            st.write(f"Analyse avec le template **{ss._pending_template.replace('_',' ').title()}**…")

            # Build document parts if any docs were uploaded
            doc_parts = []
            pending_docs = getattr(ss, "_pending_docs", [])
            if pending_docs:
                from doc_extract import build_doc_parts
                for doc_name, doc_bytes in pending_docs:
                    st.write(f"Analyse du document **{doc_name}**…")
                    doc_parts.extend(build_doc_parts(doc_bytes, doc_name))

            report = summarize_transcript(ss.transcript_named, system_prompt=system_prompt, doc_parts=doc_parts or None)
            status.update(label="Rapport généré avec succès !", state="complete", expanded=False)
    except Exception as e:
        st.error(f"Erreur génération : {e}")
        ss.phase = "transcribed"
        st.stop()
    ss.report = report
    save_output(report, ss.audio_stem, "report", "MANUAL", None)
    ss.phase = "reported"
    st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Résultats
# ══════════════════════════════════════════════════════════════════════════════
elif ss.phase == "reported":

    dest = f"copié dans `{onedrive_path}`" if onedrive_path.strip() else "sauvegardé localement"
    st.success(f"Analyse terminée pour **{ss.audio_stem}** — {dest}")

    if st.button("🔄  Relancer avec un autre template", key="rerun_template_btn"):
        ss.phase = "transcribed"
        st.rerun()

    if ss.report:
        tab_report, tab_transcript = st.tabs(["📄  Rapport", "📝  Transcript"])

        with tab_report:
            st.markdown(ss.report)
            st.divider()
            col_md, col_docx, col_pdf = st.columns(3)
            with col_md:
                st.download_button(
                    label="⬇  Télécharger (.md)",
                    data=ss.report,
                    file_name=f"{ss.audio_stem}_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with col_docx:
                try:
                    docx_bytes = generate_docx(ss.report, ss.audio_stem)
                    st.download_button(
                        label="⬇  Télécharger (.docx)",
                        data=docx_bytes,
                        file_name=f"{ss.audio_stem}_report.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Erreur export Word : {e}")
            with col_pdf:
                try:
                    pdf_bytes = generate_pdf(ss.report, ss.audio_stem)
                    st.download_button(
                        label="⬇  Télécharger (.pdf)",
                        data=pdf_bytes,
                        file_name=f"{ss.audio_stem}_report.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
                except Exception as e:
                    st.error(f"Erreur export PDF : {e}")

        with tab_transcript:
            st.text_area("t", value=ss.transcript_named, height=480,
                label_visibility="collapsed", disabled=True)
            st.download_button(
                label="⬇  Télécharger le transcript (.txt)",
                data=ss.transcript_named,
                file_name=f"{ss.audio_stem}.txt",
                mime="text/plain",
            )
    else:
        st.text_area("Transcript", value=ss.transcript_named, height=480,
            disabled=True, label_visibility="visible")
        st.download_button(
            label="⬇  Télécharger le transcript (.txt)",
            data=ss.transcript_named,
            file_name=f"{ss.audio_stem}.txt",
            mime="text/plain",
            type="primary",
        )
