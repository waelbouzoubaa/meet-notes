"""Meet Notes — Streamlit Interface — Ramery Edition."""

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
    extract_speakers,
    apply_speaker_names,
    build_system_prompt,
    save_output,
)
from transcribe import transcribe_audio
from summarize import summarize_transcript
from pdf_export import generate_pdf
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Meet Notes — Ramery",
    page_icon="🎙",
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

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "phase": "upload",
    "transcript_raw": "",
    "transcript_named": "",
    "report": "",
    "audio_stem": "",
    "elapsed_transcription": 0.0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v
ss = st.session_state

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
                    <p class="sidebar-logo-sub">Meet Notes</p>
                </div>
            </div>
            <div class="sidebar-logo-bar"></div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="sidebar-logo">
            <p class="sidebar-logo-title">🎙 Meet Notes</p>
            <p class="sidebar-logo-sub">Ramery</p>
            <div class="sidebar-logo-bar"></div>
        </div>
        """, unsafe_allow_html=True)

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
        label_visibility="collapsed")

    st.caption(tmeta(selected_template)[1])

    if selected_template == "custom":
        custom_prompt_text = st.text_area("Prompt système", height=140,
            value="Tu es un assistant de réunion. Résume le transcript en Markdown.",
            label_visibility="visible")
    else:
        custom_prompt_text = ""
        with st.expander("Voir le prompt", expanded=False):
            try:
                st.code(load_template(selected_template), language="text")
            except FileNotFoundError:
                st.warning("Template introuvable.")

    onedrive_path = ""

    st.divider()

    if ss.phase != "upload":
        st.button("↩  Nouvelle analyse", on_click=lambda: ss.update(defaults))


# ── Hero ───────────────────────────────────────────────────────────────────────
phase_labels = {"upload": "Upload", "transcribed": "Transcription", "reported": "Rapport"}
st.markdown(f"""
<div class="hero">
  <div class="hero-left">
    <div class="hero-eyebrow">Gemini 2.5 Flash · Ramery</div>
    <h1 class="hero-title">Meet Notes</h1>
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
    ("upload",      "📁", "Upload"),
    ("transcribed", "🎙", "Transcription"),
    ("transcribed", "👥", "Participants"),
    ("reported",    "📄", "Rapport"),
]
order = ["upload", "transcribed", "reported"]
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
        st.markdown('<div class="card"><p class="card-label">Fichier audio</p>', unsafe_allow_html=True)
        uploaded_file = st.file_uploader("audio",
            type=["mp3", "wav", "m4a", "ogg", "flac", "aac", "webm"],
            label_visibility="collapsed",
            help="Formats acceptés : mp3 · wav · m4a · ogg · flac · aac · webm")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_opts:
        st.markdown('<div class="card"><p class="card-label">Options</p>', unsafe_allow_html=True)
        extra_context = st.text_area("Contexte additionnel",
            placeholder="Ex : chantier Bordeaux, focus retards lot gros œuvre…",
            height=88, label_visibility="visible")
        transcript_only = st.checkbox("Transcription uniquement (sans rapport)", value=False)
        st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file:
        size_mb = uploaded_file.size / (1024 * 1024)
        icon, _ = tmeta(selected_template)
        st.markdown(
            f'<div class="info-strip">📎 <strong>{uploaded_file.name}</strong>'
            f'&nbsp;·&nbsp;{size_mb:.1f} Mo'
            f'&nbsp;·&nbsp;Template : <strong>{icon} {selected_template.replace("_"," ").title()}</strong></div>',
            unsafe_allow_html=True)

        if not os.getenv("GEMINI_API_KEY"):
            st.error("GEMINI_API_KEY manquante dans le fichier .env")
            st.stop()

        if st.button("▶  Lancer l'analyse", type="primary"):
            suffix = Path(uploaded_file.name).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getbuffer())
                tmp_path = Path(tmp.name)
            try:
                with st.status("Transcription en cours…", expanded=True) as status:
                    st.write(f"Envoi de **{uploaded_file.name}** vers Gemini Files API…")
                    transcript, elapsed = transcribe_audio(tmp_path, language)
                    status.update(label=f"Transcription terminée en {elapsed:.1f} s",
                        state="complete", expanded=False)
            except Exception as e:
                st.error(f"Erreur transcription : {e}")
                tmp_path.unlink(missing_ok=True)
                st.stop()
            finally:
                tmp_path.unlink(missing_ok=True)

            ss.transcript_raw        = transcript
            ss.transcript_named      = transcript
            ss.audio_stem            = Path(uploaded_file.name).stem
            ss.elapsed_transcription = elapsed
            ss._extra_context        = extra_context
            ss._transcript_only      = transcript_only
            ss.phase                 = "transcribed"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 2 — Identification & Rapport
# ══════════════════════════════════════════════════════════════════════════════
elif ss.phase == "transcribed":

    extra_context   = getattr(ss, "_extra_context", "")
    transcript_only = getattr(ss, "_transcript_only", False)

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
            edited_df = st.data_editor(
                pd.DataFrame({"Identifiant Gemini": speakers, "Vrai nom": [""] * len(speakers)}),
                column_config={
                    "Identifiant Gemini": st.column_config.TextColumn(disabled=True),
                    "Vrai nom": st.column_config.TextColumn(max_chars=50),
                },
                hide_index=True, use_container_width=True)
            speaker_map = {
                row["Identifiant Gemini"]: row["Vrai nom"]
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
            system_prompt = build_system_prompt(selected_template, extra_context, custom_prompt_text)
            with st.status("Génération du rapport…", expanded=True) as status:
                st.write(f"Analyse avec le template **{selected_template.replace('_',' ').title()}**…")
                report = summarize_transcript(ss.transcript_named, system_prompt=system_prompt)
                status.update(label="Rapport généré avec succès !", state="complete", expanded=False)
            ss.report = report
            save_output(report, ss.audio_stem, "report", "MANUAL", extra_dir)
            ss.phase = "reported"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PHASE 3 — Résultats
# ══════════════════════════════════════════════════════════════════════════════
elif ss.phase == "reported":

    dest = f"copié dans `{onedrive_path}`" if onedrive_path.strip() else "sauvegardé localement"
    st.success(f"Analyse terminée pour **{ss.audio_stem}** — {dest}")

    if ss.report:
        tab_report, tab_transcript = st.tabs(["📄  Rapport", "📝  Transcript"])

        with tab_report:
            st.markdown(ss.report)
            st.divider()
            col_md, col_pdf = st.columns(2)
            with col_md:
                st.download_button(
                    label="⬇  Télécharger (.md)",
                    data=ss.report,
                    file_name=f"{ss.audio_stem}_report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
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
