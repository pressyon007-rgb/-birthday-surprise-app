import hmac
import os
import json
import html
import base64
import random
from datetime import datetime, timezone, timedelta
from io import BytesIO
from urllib.parse import quote

import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw, ImageFilter

# ============================================================
# MONALISA BIRTHDAY APP — COMPLETE SINGLE-FILE VERSION
# ============================================================
st.set_page_config(page_title="Monalisa | Emerald Memories", page_icon="💚", layout="wide", initial_sidebar_state="expanded")

APP_DIR = os.path.dirname(os.path.abspath(__file__))
# Support running app.py from the project root OR from a dashboard/ subfolder.
BASE_DIR = os.path.dirname(APP_DIR) if os.path.basename(APP_DIR).lower() == "dashboard" and os.path.isdir(os.path.join(os.path.dirname(APP_DIR), "assets")) else APP_DIR
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
PHOTO_DIR = os.path.join(ASSETS_DIR, "photos")
AUDIO_DIR = os.path.join(ASSETS_DIR, "audio")
BACKGROUND_DIR = os.path.join(ASSETS_DIR, "backgrounds")
SETTINGS_PATH = os.path.join(BASE_DIR, "monalisa_settings.json")
for folder in (PHOTO_DIR, AUDIO_DIR, BACKGROUND_DIR):
    os.makedirs(folder, exist_ok=True)

IST = timezone(timedelta(hours=5, minutes=30))
BIRTHDAY_OPENS_AT = datetime(2026, 11, 3, 0, 0, 0, tzinfo=IST)
TEST_MODE = os.environ.get("MONALISA_TEST_MODE", "").strip().lower() in {"1", "true", "yes", "on"}
def get_secret_or_env(name, default=""):
    try:
        value = st.secrets.get(name, default)
    except Exception:
        value = default
    return os.environ.get(name, value) or default

APP_PASSWORD = str(get_secret_or_env("MONALISA_APP_PASSWORD", "")).strip()
OWNER_PASSWORD = str(get_secret_or_env("MONALISA_OWNER_PASSWORD", "")).strip()
PUBLIC_URL_DEFAULT = str(get_secret_or_env("MONALISA_PUBLIC_URL", "")).strip()

DEFAULTS = {
    "photo_display_mode": "Photo gallery", "slideshow_seconds": 4,
    "theme": "Emerald & Gold", "page_bg": "#08291f", "accent": "#d8b653", "text_color": "#fff3d2",
    "card_opacity": 92, "background_darkness": 22, "font_scale": 100, "compact_layout": True, "animations": True,
    "gallery_title": "Our Beautiful Memories ✦", "gallery_subtitle": "Every picture holds a little piece of love ✨",
    "letter_title": "A Letter From My Heart 💚",
    "letter_text": "Dear Monalisa,\n\nSome memories become the most beautiful parts of our lives. Thank you for your laughter, your kindness, and all the little moments that mean more than words can explain. I hope this year brings you peace, courage, beautiful surprises, and all the happiness you deserve.\n\nNo matter how busy life becomes, you will always have a special place in my heart.\n\nWith lots of love 💚",
    "music_title": "Monalisa's Birthday Song", "music_volume": 70,
    "frame_color": "#f7f0d8", "frame_style": "Classic", "frame_thickness": 8, "frame_gap": 10,
    "gallery_columns": 4, "gallery_photo_height": 210, "show_captions": True,
    "caption_font_size": 17, "caption_color": "#f5d889", "caption_emphasis": "Italic",
    "custom_background": "", "custom_music": "", "photo_settings": {}, "photo_order": [], "scrapbook_notes": {},
}
EXCLUDE_FROM_PERSIST = {"logged_in", "page", "quiz_index", "quiz_answers", "gallery_index", "quiz_done", "automatic_slide", "scrapbook_index", "_last_theme"}


def load_settings():
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if isinstance(saved, dict):
            for key in DEFAULTS:
                if key in saved:
                    DEFAULTS[key] = saved[key]
    except (OSError, json.JSONDecodeError, TypeError):
        pass


def save_settings():
    payload = {}
    for key in DEFAULTS:
        if key in EXCLUDE_FROM_PERSIST:
            continue
        value = st.session_state.get(key, DEFAULTS[key])
        try:
            json.dumps(value)
            payload[key] = value
        except (TypeError, ValueError):
            pass
    try:
        temp = SETTINGS_PATH + ".tmp"
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        os.replace(temp, SETTINGS_PATH)
    except OSError:
        pass


load_settings()
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value
for key, value in {"logged_in": False, "page": "login", "quiz_index": 0, "quiz_answers": [], "gallery_index": 0, "quiz_done": False, "automatic_slide": 0, "scrapbook_index": 0, "memories_seen": False, "owner_authenticated": False}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def list_files(folder, extensions):
    try:
        return sorted(os.path.join(folder, name) for name in os.listdir(folder) if name.lower().endswith(extensions))
    except OSError:
        return []


def list_photos():
    return list_files(PHOTO_DIR, (".jpg", ".jpeg", ".png", ".webp", ".bmp"))


def list_backgrounds():
    return list_files(BACKGROUND_DIR, (".jpg", ".jpeg", ".png", ".webp"))


def safe_filename(name):
    base = os.path.basename(name or "upload")
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base) or "upload"


def save_uploaded_file(uploaded, folder, prefix=""):
    if uploaded is None:
        return ""
    filename = prefix + safe_filename(uploaded.name)
    path = os.path.join(folder, filename)
    root, ext = os.path.splitext(path)
    counter = 1
    while os.path.exists(path):
        path = f"{root}_{counter}{ext}"
        counter += 1
    try:
        raw = uploaded.getvalue()
        if len(raw) > 25 * 1024 * 1024:
            st.error(f"{uploaded.name} is larger than 25 MB. Please choose a smaller file.")
            return ""
        ext = os.path.splitext(filename)[1].lower()
        if folder in (PHOTO_DIR, BACKGROUND_DIR):
            try:
                with Image.open(BytesIO(raw)) as check_image:
                    check_image.verify()
            except Exception:
                st.error(f"{uploaded.name} is not a valid supported image.")
                return ""
        elif folder == AUDIO_DIR and ext not in {".mp3", ".wav", ".ogg", ".m4a"}:
            st.error("Unsupported audio type. Use MP3, WAV, OGG, or M4A.")
            return ""
        with open(path, "xb") as f:
            f.write(raw)
        return path
    except OSError:
        st.error(f"Could not save {uploaded.name}. Check folder permissions.")
        return ""


EMOTIONAL_CAPTIONS = [
    "You are one of my favourite memories. 💚",
    "Some moments stay in the heart forever. ✨",
    "A little picture, a lifetime of love. 🌷",
    "No matter how much time passes, this memory stays. 🤍",
    "Your smile makes ordinary moments beautiful. 😊",
    "Family by relation, forever close at heart. 💚",
    "If I could keep one moment, it would be this one. 🥹",
    "The best memories are the ones we share. ✨",
    "A beautiful day made brighter by you. 🌻",
    "This photo holds more love than words can say. 💌",
]


def default_emotional_caption(filename):
    """Return a warm starter caption based on the photo filename."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    clean = stem.replace("_", " ").replace("-", " ").strip()
    return f"A beautiful memory with {clean}. 💚" if clean else EMOTIONAL_CAPTIONS[0]


def get_photo_config(path):
    name = os.path.basename(path)
    cfg = st.session_state.photo_settings.get(name, {})
    return {
        "width": int(cfg.get("width", 100)), "height": int(cfg.get("height", st.session_state.gallery_photo_height)),
        "frame": cfg.get("frame", st.session_state.frame_style), "frame_color": cfg.get("frame_color", st.session_state.frame_color),
        "thickness": int(cfg.get("thickness", st.session_state.frame_thickness)), "radius": int(cfg.get("radius", 8)),
        "rotation": int(cfg.get("rotation", 0)), "caption": cfg.get("caption", default_emotional_caption(name)),
        "shadow": bool(cfg.get("shadow", True)), "mat": int(cfg.get("mat", st.session_state.frame_gap)),
    }


def update_photo_config(path, **kwargs):
    settings = dict(st.session_state.photo_settings)
    name = os.path.basename(path)
    cfg = dict(settings.get(name, {}))
    cfg.update(kwargs)
    settings[name] = cfg
    st.session_state.photo_settings = settings
    save_settings()


def make_frame_image(path, cfg=None):
    cfg = cfg or get_photo_config(path)
    try:
        source = Image.open(path).convert("RGB")
        source.thumbnail((1000, 1200), Image.Resampling.LANCZOS)
    except (OSError, ValueError):
        return None
    pad = max(0, int(cfg["mat"]))
    border = max(1, int(cfg["thickness"]))
    color = cfg["frame_color"]
    canvas = Image.new("RGB", (source.width + 2 * (pad + border), source.height + 2 * (pad + border)), color)
    canvas.paste(source, (pad + border, pad + border))
    draw = ImageDraw.Draw(canvas)
    if cfg["frame"] == "Double Gold":
        draw.rectangle((border // 2, border // 2, canvas.width - border // 2 - 1, canvas.height - border // 2 - 1), outline="#c6a34c", width=max(1, border // 2))
        draw.rectangle((border + pad // 2, border + pad // 2, canvas.width - border - pad // 2 - 1, canvas.height - border - pad // 2 - 1), outline="#fff0bd", width=1)
    elif cfg["frame"] == "Polaroid":
        extra = max(24, border * 3)
        bigger = Image.new("RGB", (canvas.width, canvas.height + extra), color)
        bigger.paste(canvas, (0, 0))
        canvas = bigger
    elif cfg["frame"] == "Minimal":
        draw.rectangle((0, 0, canvas.width - 1, canvas.height - 1), outline=color, width=border)
    return canvas


def style_photo_image(image, cfg):
    """Apply optional rounded corners and a soft shadow without cropping the photo."""
    image = image.convert("RGBA")
    radius = max(0, min(30, int(cfg.get("radius", 8))))
    if radius:
        mask = Image.new("L", image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=radius, fill=255)
        image.putalpha(mask)
    if cfg.get("shadow", True):
        pad = 18
        shadow_layer = Image.new("RGBA", (image.width + pad * 2, image.height + pad * 2), (0, 0, 0, 0))
        alpha = image.getchannel("A")
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 100))
        shadow.putalpha(alpha.point(lambda value: value * 100 // 255))
        shadow_layer.alpha_composite(shadow, (pad, pad))
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(7))
        shadow_layer.alpha_composite(image, (pad, pad))
        return shadow_layer
    return image


def image_data_url(path):
    try:
        with open(path, "rb") as f:
            raw = f.read()
        ext = os.path.splitext(path)[1].lower()
        mime = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
    except OSError:
        return ""


def apply_global_css():
    compact = st.session_state.compact_layout
    top_pad = "0.25rem" if compact else "1rem"
    gap = "0.3rem" if compact else "0.8rem"
    bg, accent, text_color = st.session_state.page_bg, st.session_state.accent, st.session_state.text_color
    opacity = max(0.1, min(1.0, st.session_state.card_opacity / 100))
    font_scale = max(75, min(140, int(st.session_state.font_scale))) / 100
    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');
    :root{{--emerald:{bg};--gold:{accent};--cream:{text_color};}}
    html,body,[class*="css"]{{font-family:Poppins,sans-serif;font-size:{font_scale}rem;}}
    [data-testid="stAppViewContainer"]{{background:linear-gradient(135deg,#041a14 0%,{bg} 55%,#03120e 100%);color:var(--cream);}}
    [data-testid="stHeader"]{{background:rgba(3,20,15,.92);}}
    [data-testid="stSidebar"]{{background:rgba(4,29,22,.98);border-right:1px solid var(--gold);min-width:300px;}}
    [data-testid="stSidebar"] *{{color:var(--cream);}}
    .block-container{{max-width:1600px;padding:{top_pad} .7rem .45rem!important;}}
    [data-testid="stVerticalBlock"]{{gap:{gap}!important;}}
    [data-testid="stElementContainer"]{{margin-bottom:0!important;}}
    [data-testid="stHorizontalBlock"]{{gap:.6rem!important;}}
    h1,h2,h3,p,label{{color:var(--cream);}} h1,h2,h3{{line-height:1.12;}}
    .hero{{text-align:center;padding:.45rem .5rem .55rem;margin:0 0 .4rem;border:1px solid rgba(216,182,83,.55);border-radius:18px;background:rgba(4,25,19,.55);}}
    .hero h1{{margin:.15rem 0;font-size:clamp(1.6rem,3vw,2.6rem);color:#f5d889;}} .hero p{{margin:.15rem 0;opacity:.92;}}
    div.stButton>button{{border-radius:999px;border:1px solid var(--gold);background:linear-gradient(110deg,#25b48a,#d1b342);color:#fff7df;font-weight:600;min-height:40px;padding:.45rem .85rem;}}
    div.stButton>button:hover{{border-color:#fff0bd;filter:brightness(1.06);}}
    [data-testid="stExpander"]{{border:1px solid rgba(216,182,83,.55)!important;border-radius:12px!important;background:rgba(5,39,29,.65);}}
    [data-testid="stImage"] img{{object-fit:contain!important;}}
    .memory-card{{border:1px solid var(--gold);border-radius:15px;padding:10px;background:rgba(255,250,231,{opacity});color:#3c321d;box-shadow:0 6px 18px rgba(0,0,0,.20);text-align:center;height:100%;}}
    .memory-card h2,.memory-card p{{color:#473a27;}} .caption{{color:{st.session_state.caption_color};font-size:{int(st.session_state.caption_font_size)}px;font-style:{'italic' if st.session_state.caption_emphasis == 'Italic' else 'normal'};font-weight:{700 if st.session_state.caption_emphasis == 'Bold' else 400};margin:.35rem 0 .5rem;text-align:center;line-height:1.4;overflow-wrap:anywhere;}}
    @media(max-width:700px){{[data-testid="stSidebar"]{{min-width:0;}}.block-container{{padding:.15rem .4rem .3rem!important;}}[data-testid="stHorizontalBlock"]{{gap:.25rem!important;}}.hero{{padding:.25rem;}}.hero h1{{font-size:1.55rem;}}div.stButton>button{{min-height:38px;padding:.35rem .55rem;}}}}
    </style>"""
    st.markdown(css, unsafe_allow_html=True)


def apply_custom_background():
    path = st.session_state.get("custom_background", "")
    if path and os.path.isfile(path):
        url = image_data_url(path)
        if url:
            overlay = max(0, min(85, int(st.session_state.background_darkness))) / 100
            st.markdown(f'<style>[data-testid="stAppViewContainer"]{{background-image:linear-gradient(rgba(2,15,11,{overlay}),rgba(2,15,11,{overlay})),url("{url}");background-size:cover;background-position:center;background-attachment:fixed;}}</style>', unsafe_allow_html=True)


def owner_settings_gate():
    """Require a separate owner password before exposing customization controls."""
    with st.sidebar:
        st.markdown("## 🔐 Owner access")
        if st.session_state.get("owner_authenticated", False):
            st.success("Owner access enabled")
            if st.button("🔒 Lock owner settings", key="lock_owner_settings", use_container_width=True):
                st.session_state.owner_authenticated = False
                st.rerun()
            return True

        with st.form("owner_settings_login"):
            owner_password = st.text_input("Owner password", type="password", key="owner_password_input")
            submitted = st.form_submit_button("Unlock owner settings", use_container_width=True)

        if submitted:
            if OWNER_PASSWORD and hmac.compare_digest(owner_password, OWNER_PASSWORD):
                st.session_state.owner_authenticated = True
                st.session_state.page = "studio"
                st.rerun()
            elif not OWNER_PASSWORD:
                st.error("Owner password is not configured. Add MONALISA_OWNER_PASSWORD in Streamlit Cloud Secrets.")
            else:
                st.error("Incorrect owner password.")

    return bool(st.session_state.get("owner_authenticated", False))


def sidebar_customizer():
    with st.sidebar:
        st.markdown("## 🎨 Customize Everything")
        st.caption("Changes save automatically in this project.")
        with st.expander("🌈 Colours & layout", expanded=True):
            st.selectbox("Preset colour theme", ["Emerald & Gold", "Burgundy & Champagne", "Midnight Blue & Gold"], key="theme")
            presets = {"Emerald & Gold": ("#08291f", "#d8b653", "#fff3d2"), "Burgundy & Champagne": ("#35121e", "#e3c18b", "#fff0df"), "Midnight Blue & Gold": ("#101c35", "#d7b65b", "#f3f2ff")}
            if st.session_state.get("_last_theme") != st.session_state.theme:
                st.session_state.page_bg, st.session_state.accent, st.session_state.text_color = presets[st.session_state.theme]
                st.session_state._last_theme = st.session_state.theme
            st.color_picker("Background colour", key="page_bg")
            st.color_picker("Accent / frame colour", key="accent")
            st.color_picker("Text colour", key="text_color")
            st.toggle("Reduce blank spaces", key="compact_layout")
            st.slider("Photo background darkness", 0, 80, key="background_darkness")
            st.slider("Content card opacity", 40, 100, key="card_opacity")
            st.slider("Text size (%)", 75, 140, key="font_scale")
            st.toggle("Animated effects", key="animations")
        with st.expander("🖼️ Gallery & frames", expanded=True):
            st.selectbox("Photo display mode", ["Automatic slideshow", "Photo gallery", "Photo collage", "Floating Memory Wall", "Interactive Scrapbook", "Heart-Shaped Photo Gallery", "Memory Timeline", "Hanging Polaroid Gallery"], key="photo_display_mode")
            st.slider("Slideshow interval (seconds)", min_value=2, max_value=12, key="slideshow_seconds")
            st.text_input("Gallery section title", key="gallery_title")
            st.text_input("Gallery subtitle", key="gallery_subtitle")
            st.slider("Gallery columns", 1, 6, key="gallery_columns")
            st.slider("Photo display height", 120, 420, key="gallery_photo_height")
            st.selectbox("Default frame style", ["Classic", "Double Gold", "Polaroid", "Minimal"], key="frame_style")
            st.color_picker("Default frame colour", key="frame_color")
            st.slider("Frame thickness", 1, 24, key="frame_thickness")
            st.slider("Space inside frame", 0, 36, key="frame_gap")
            st.toggle("Show photo captions", key="show_captions")
            st.slider("Caption text size", 11, 28, key="caption_font_size")
            st.color_picker("Caption text colour", key="caption_color")
            st.selectbox("Caption emphasis", ["Normal", "Italic", "Bold"], key="caption_emphasis")
        with st.expander("🎵 Music", expanded=False):
            st.caption("Autoplay + looping are enabled. Some browsers block sound until you tap Start music once.")
            st.text_input("Song title", key="music_title")
            st.slider("Music volume", 0, 100, key="music_volume")
            uploaded_song = st.file_uploader("Upload music file", type=["mp3", "wav", "ogg", "m4a"], key="song_upload")
            if uploaded_song is not None and st.button("Save uploaded music", key="save_song"):
                saved = save_uploaded_file(uploaded_song, AUDIO_DIR, "custom_birthday_song_")
                if saved:
                    st.session_state.custom_music = saved
                    save_settings()
                    st.success("Music saved in assets/audio.")
                    st.rerun()
        with st.expander("🌌 Background", expanded=False):
            backgrounds = list_backgrounds()
            options = [""] + backgrounds
            current = st.session_state.get("custom_background", "")
            chosen_index = options.index(current) if current in options else 0
            chosen = st.selectbox("Saved background image", options, index=chosen_index, format_func=lambda p: "Use theme background" if not p else os.path.basename(p))
            st.session_state.custom_background = chosen
            uploaded_bg = st.file_uploader("Upload background image", type=["jpg", "jpeg", "png", "webp"], key="background_upload")
            if uploaded_bg is not None and st.button("Save background image", key="save_bg"):
                saved = save_uploaded_file(uploaded_bg, BACKGROUND_DIR, "custom_bg_")
                if saved:
                    st.session_state.custom_background = saved
                    save_settings()
                    st.success("Background saved in assets/backgrounds.")
                    st.rerun()
        with st.expander("💌 Letter", expanded=False):
            st.text_input("Letter heading", key="letter_title")
            st.text_area("Letter text", key="letter_text", height=240)
        with st.expander("🌐 Publish & share", expanded=False):
            st.caption("This panel prepares sharing details; it cannot publish automatically. Deploy through Streamlit Community Cloud after pushing the project to GitHub.")
            st.text_input("Public app URL (after deployment)", value=st.session_state.get("public_app_url", PUBLIC_URL_DEFAULT), key="public_app_url", placeholder="Paste the real Streamlit Cloud URL here")
            public_url = str(st.session_state.get("public_app_url", "")).strip()
            if public_url.startswith(("https://", "http://")):
                st.code(public_url, language=None)
                wa_link = "https://wa.me/?text=" + quote("Monalisa's birthday memories 💚 " + public_url)
                st.markdown(f"[Share this app through WhatsApp]({wa_link})")
                st.caption("Test this exact URL in a private browser and on a phone before sharing.")
            else:
                st.info("No public URL configured yet. This is expected before deployment; no link has been created.")
            st.markdown("**Before publishing**")
            st.markdown("1. Save customizations. 2. Include `assets/` and `monalisa_settings.json` in the repository. 3. Add `MONALISA_APP_PASSWORD` under Streamlit Cloud → Settings → Secrets. 4. Keep `MONALISA_TEST_MODE` unset in production.")
        if st.button("💾 Save all customization settings", use_container_width=True):
            save_settings()
            st.success("Settings saved.")
    save_settings()


def hero(title, subtitle=""):
    sub = f"<p>{html.escape(subtitle)}</p>" if subtitle else ""
    st.markdown(f'<div class="hero"><h1>{html.escape(title)}</h1>{sub}</div>', unsafe_allow_html=True)


def nav_bar():
    # The recipient's journey is intentionally ordered: Quiz -> Memories -> Letter.
    pages = [("❔ Quiz", "quiz")]
    if st.session_state.get("quiz_done", False):
        pages.append(("📸 Memories", "photos"))
    if st.session_state.get("memories_seen", False):
        pages.append(("💌 Letter", "letter"))
    # Photo Studio is visible only in the authenticated owner's session.
    if st.session_state.get("owner_authenticated", False):
        pages.append(("🖼️ Photo Studio", "studio"))
    cols = st.columns(len(pages))
    for col, (label, page_name) in zip(cols, pages):
        with col:
            if st.button(label, key=f"nav_{page_name}", use_container_width=True):
                st.session_state.page = page_name
                st.rerun()


def play_music():
    """Render a looping audio player and attempt autoplay.

    Audible autoplay can be blocked by browser policy. The player and its
    Start Music button are placed before the script so the button exists when
    JavaScript runs. Works whether app.py is in the project root or dashboard/.
    """
    path = st.session_state.get("custom_music", "")
    if not path or not os.path.isfile(path):
        candidates = [
            os.path.join(AUDIO_DIR, "tamil-birthday-song.mp3"),
            os.path.join(AUDIO_DIR, "birthday_song.mp3"),
            os.path.join(ASSETS_DIR, "music", "birthday_song.mp3"),
        ]
        candidates.extend(list_files(AUDIO_DIR, (".mp3", ".wav", ".ogg", ".m4a")))
        path = next((candidate for candidate in candidates if os.path.isfile(candidate)), "")

    if not path:
        st.info("🎵 Add your song at assets/audio/tamil-birthday-song.mp3, or upload it in the sidebar under Music.")
        return

    try:
        with open(path, "rb") as audio_file:
            raw_audio = audio_file.read()
        if not raw_audio:
            st.error(f"The music file is empty: {os.path.basename(path)}")
            return
        encoded = base64.b64encode(raw_audio).decode("ascii")
        ext = os.path.splitext(path)[1].lower()
        mime = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".m4a": "audio/mp4"}.get(ext, "audio/mpeg")
        volume = max(0, min(100, int(st.session_state.get("music_volume", 70)))) / 100
        title = html.escape(str(st.session_state.get("music_title", "Birthday song")))
        audio_html = f'''<!doctype html>
<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head>
<body style="margin:0;background:transparent;font-family:Arial,sans-serif;color:#f5d889">
  <audio id="monalisaBirthdayMusic" controls loop preload="auto" playsinline style="width:100%;height:42px">
    <source src="data:{mime};base64,{encoded}" type="{mime}">
    Your browser does not support audio playback.
  </audio>
  <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:5px 0">
    <button id="startMusic" type="button" style="border:1px solid #d8b653;border-radius:20px;padding:8px 16px;background:#0b4635;color:#fff3d2;font-weight:600;cursor:pointer">▶ Start music</button>
    <span id="autoplayNotice" style="font-size:12px">Trying to start: {title}</span>
  </div>
  <script>
    window.addEventListener('DOMContentLoaded', function() {{
      const player = document.getElementById('monalisaBirthdayMusic');
      const button = document.getElementById('startMusic');
      const notice = document.getElementById('autoplayNotice');
      if (!player || !button || !notice) return;
      player.volume = {volume};
      player.loop = true;
      const attemptPlay = function() {{
        const promise = player.play();
        if (promise && promise.then) promise.then(function() {{
          notice.textContent = '♪ Playing: {title}';
        }}).catch(function() {{
          notice.textContent = 'Autoplay blocked by browser — tap Start music.';
        }});
      }};
      button.addEventListener('click', function() {{
        player.play().then(function() {{ notice.textContent = '♪ Music is playing'; }}).catch(function() {{
          notice.textContent = 'Could not start. Press Play on the audio player.';
        }});
      }});
      player.addEventListener('error', function() {{ notice.textContent = 'Audio file could not be decoded. Try another MP3/WAV file.'; }});
      player.addEventListener('canplay', function() {{ notice.textContent = 'Ready: {title}'; }}, {{once:true}});
      attemptPlay();
    }});
  </script>
</body></html>'''
        components.html(audio_html, height=92, scrolling=False)
    except OSError as error:
        st.error(f"Unable to load the song: {error}")


QUIZ = [("What makes a memory special?", ["The people in it", "The price of things", "The place only"], 0), ("Choose the best gift for someone you love.", ["A kind memory", "An empty box", "A forgotten note"], 0), ("What should a birthday year bring?", ["Joy and growth", "Only busy days", "No new memories"], 0)]


def show_login():
    _, center, _ = st.columns([1, 1.15, 1])
    with center:
        hero("A Little World of Memories 💚", "A collection of moments made with love")
        st.markdown('<div class="memory-card"><h2>Welcome</h2><p>Enter the password to open your memories.</p></div>', unsafe_allow_html=True)
        photos = list_photos()
        if photos:
            cols = st.columns(min(4, len(photos[:4])))
            for col, path in zip(cols, photos[:4]):
                with col:
                    st.image(path, use_container_width=True)
        with st.form("login_form"):
            password = st.text_input("Enter the password", type="password")
            submitted = st.form_submit_button("Open memories 💚", use_container_width=True)
            if submitted:
                if APP_PASSWORD and hmac.compare_digest(password, APP_PASSWORD):
                    st.session_state.logged_in = True
                    st.session_state.page = "quiz"
                    st.session_state.quiz_index = 0
                    st.session_state.quiz_answers = []
                    st.session_state.quiz_done = False
                    st.session_state.memories_seen = False
                    st.rerun()
                elif not APP_PASSWORD:
                    st.error("The app password is not configured. Please configure MONALISA_APP_PASSWORD in Streamlit Cloud Secrets.")
                else:
                    st.error("That password doesn't match. Try again.")


def show_home():
    hero("Happy Birthday Monalisa ✨", "A lifetime of memories, a heart full of love")
    photos = list_photos()
    left, right = st.columns([1.2, 1])
    with left:
        st.markdown('<div class="memory-card"><h2>Made of memories ✦</h2><p>Every photograph holds a moment, every moment holds a story.</p></div>', unsafe_allow_html=True)
        if photos:
            st.image(photos[0], use_container_width=True)
    with right:
        st.markdown('<div class="memory-card"><h2>For you, Monalisa 💚</h2><p>May the days ahead bring you laughter, warmth, courage and beautiful surprises.</p></div>', unsafe_allow_html=True)
        if st.button("✨ Open the memory gallery", use_container_width=True):
            st.session_state.page = "photos"; st.rerun()
        if st.button("💌 Read the letter", use_container_width=True):
            st.session_state.page = "letter"; st.rerun()
        if st.button("🎁 Birthday reveal", use_container_width=True):
            st.session_state.page = "reveal"; st.rerun()


def show_quiz():
    hero("A Little Memory Quiz ✨", "Answer these just for fun")
    if st.session_state.quiz_done:
        st.success("Quiz complete! Every memory is more special when shared. 💚")
        left, right = st.columns(2)
        with left:
            if st.button("🔁 Try the quiz again", use_container_width=True):
                st.session_state.quiz_index = 0
                st.session_state.quiz_answers = []
                st.session_state.quiz_done = False
                st.rerun()
        with right:
            if st.button("Continue to our memories →", use_container_width=True):
                st.session_state.page = "photos"
                st.rerun()
        return
    idx = st.session_state.quiz_index
    question, choices, answer = QUIZ[idx]
    st.progress((idx + 1) / len(QUIZ))
    st.subheader(f"Question {idx + 1} of {len(QUIZ)}")
    choice = st.radio(question, choices, key=f"quiz_choice_{idx}")
    if st.button("Submit answer", use_container_width=True):
        st.session_state.quiz_answers.append(choice)
        if choice == choices[answer]: st.success("Correct! 💚")
        else: st.info(f"Best answer: {choices[answer]}")
        if idx + 1 >= len(QUIZ): st.session_state.quiz_done = True
        else: st.session_state.quiz_index += 1
        st.rerun()


def show_photo_card(path, custom_height=None):
    cfg = get_photo_config(path)
    image = make_frame_image(path, cfg)
    if image is None:
        st.warning(f"Could not load photo: {os.path.basename(path)}")
        return
    image = style_photo_image(image, cfg)
    if cfg["rotation"]:
        image = image.rotate(cfg["rotation"], expand=True, fillcolor=cfg["frame_color"])
    target_height = max(120, min(520, int(custom_height or cfg["height"])))
    if image.height > target_height:
        new_width = max(1, round(image.width * target_height / image.height))
        image = image.resize((new_width, target_height), Image.Resampling.LANCZOS)
    display_width = max(35, min(100, int(cfg["width"])))
    # Center each photo and let the per-photo width control affect the visible size.
    left_space = max(1, 100 - display_width)
    left, center, right = st.columns([left_space, display_width, left_space], gap="small")
    with center:
        st.image(image, use_container_width=True)
    if st.session_state.show_captions:
        st.markdown(f'<div class="caption">{html.escape(str(cfg["caption"]))}</div>', unsafe_allow_html=True)


def render_photo_mode(photos):
    import math
    mode = st.session_state.photo_display_mode
    gap = int(st.session_state.frame_gap)
    captions = st.session_state.show_captions
    if not photos:
        st.info("No photos available yet."); return
    if mode == "Automatic slideshow":
        index = st.session_state.automatic_slide % len(photos)
        show_photo_card(photos[index])
        st.caption(f"Photo {index + 1} of {len(photos)} · Use the arrows to change photos. The selected interval is {st.session_state.slideshow_seconds} seconds.")
        prev, _, nxt = st.columns([1, 3, 1])
        with prev:
            if st.button("← Previous", key="slide_previous"):
                st.session_state.automatic_slide = (index - 1) % len(photos); st.rerun()
        with nxt:
            if st.button("Next →", key="slide_next"):
                st.session_state.automatic_slide = (index + 1) % len(photos); st.rerun()
        st.caption("Note: this slideshow uses manual next/previous controls to avoid refreshing the entire app unexpectedly.")
        return
    if mode == "Photo gallery":
        count = max(1, min(6, int(st.session_state.gallery_columns)))
        for start in range(0, len(photos), count):
            cols = st.columns(count, gap="small")
            for col, path in zip(cols, photos[start:start + count]):
                with col: show_photo_card(path)
        return
    if mode in ("Photo collage", "Floating Memory Wall", "Hanging Polaroid Gallery"):
        floating = mode == "Floating Memory Wall"
        hanging = mode == "Hanging Polaroid Gallery"
        cards = []
        for path in photos:
            data = image_data_url(path)
            if not data: continue
            cfg = get_photo_config(path)
            caption = html.escape(str(cfg["caption"]))
            rotation = random.randint(-5, 5) if floating or hanging else random.randint(-2, 2)
            cards.append(f'<article class="memory {"floating" if floating else "hanging" if hanging else ""}" style="--tilt:{rotation}deg;--frame:{html.escape(cfg["frame_color"])}"><img src="{data}" alt="{caption}"><p>{caption if captions else ""}</p></article>')
        animation = "@keyframes floatMemory{0%,100%{transform:translateY(0) rotate(var(--tilt))}50%{transform:translateY(-10px) rotate(var(--tilt))}}.floating{animation:floatMemory 4s ease-in-out infinite}" if floating and st.session_state.animations else ""
        components.html(f'''<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{margin:0;background:transparent;font-family:Georgia,serif}}.wall{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:{gap + 10}px;padding:10px;align-items:start}}.memory{{background:#fff9e9;padding:9px;border:3px solid var(--frame);box-shadow:0 8px 20px #0005;transform:rotate(var(--tilt))}}.memory img{{width:100%;height:auto;display:block;object-fit:contain}}.memory p{{color:#473a27;text-align:center;margin:7px 0 1px;font-size:14px}}.hanging{{margin-top:18px;position:relative}}.hanging:before{{content:"";position:absolute;top:-18px;left:50%;height:20px;border-left:2px solid #d8b653}}{animation}</style></head><body><div class="wall">{''.join(cards)}</div></body></html>''', height=max(420, min(2400, len(cards) * 190)), scrolling=True)
        return
    if mode == "Interactive Scrapbook":
        index = st.session_state.scrapbook_index % len(photos); path = photos[index]; name = os.path.basename(path)
        st.markdown("### 📔 A Page From Our Story\nEvery picture holds a memory worth keeping.")
        left, right = st.columns([1.2, 1])
        with left: show_photo_card(path)
        with right:
            st.markdown(f"#### Memory {index + 1}")
            note = st.text_area("Write a memory note", value=st.session_state.scrapbook_notes.get(name, ""), key=f"note_{name}", placeholder="Write a favourite moment here...")
            if st.button("Save memory note", key=f"save_note_{name}"):
                notes = dict(st.session_state.scrapbook_notes); notes[name] = note; st.session_state.scrapbook_notes = notes; save_settings(); st.success("Memory note saved.")
        prev, _, nxt = st.columns([1, 3, 1])
        with prev:
            if st.button("← Previous page", key="scrap_prev"):
                st.session_state.scrapbook_index = (index - 1) % len(photos); st.rerun()
        with nxt:
            if st.button("Next page →", key="scrap_next"):
                st.session_state.scrapbook_index = (index + 1) % len(photos); st.rerun()
        return
    if mode == "Heart-Shaped Photo Gallery":
        cards = []
        for i, path in enumerate(photos):
            data = image_data_url(path)
            if not data: continue
            angle = 2 * math.pi * i / max(1, len(photos))
            x = 16 * math.sin(angle) ** 3
            y = 13 * math.cos(angle) - 5 * math.cos(2 * angle) - 2 * math.cos(3 * angle) - math.cos(4 * angle)
            left, top = 50 + x * 2.5, 48 - y * 2.5
            caption = html.escape(str(get_photo_config(path)["caption"]))
            cards.append(f'<div class="heart-photo" style="left:{left}%;top:{top}%"><img src="{data}" alt="{caption}"><p>{caption if captions else ""}</p></div>')
        components.html(f'''<html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{margin:0;background:transparent}}.heart{{position:relative;width:100%;max-width:950px;height:760px;margin:auto}}.heart-photo{{position:absolute;width:16%;transform:translate(-50%,-50%);background:#fff8e8;padding:5px;border:2px solid #d8b653;box-shadow:0 4px 12px #0005}}.heart-photo img{{display:block;width:100%;height:auto}}.heart-photo p{{color:#473a27;text-align:center;font-size:11px;margin:4px 0 0}}@media(max-width:650px){{.heart{{height:520px}}.heart-photo{{width:23%}}}}</style></head><body><div class="heart">{''.join(cards)}</div></body></html>''', height=780, scrolling=True)
        return
    if mode == "Memory Timeline":
        st.markdown("### 🕰️ Our Memory Timeline")
        for index, path in enumerate(photos):
            left, right = st.columns([1, 5])
            with left: st.markdown(f"### {index + 1:02d} ♡")
            with right:
                st.markdown("---"); show_photo_card(path); st.caption("A moment to remember forever.")
        return


def show_photos():
    st.session_state.memories_seen = True
    hero(st.session_state.gallery_title, st.session_state.gallery_subtitle)
    photos = list_photos()
    if not photos:
        st.warning("No photos found. Add images to assets/photos or upload them in Photo Studio.")
        if st.button("Open Photo Studio"):
            st.session_state.page = "studio"; st.rerun()
        return
    by_name = {os.path.basename(path): path for path in photos}
    saved_order = st.session_state.photo_order
    ordered = [by_name[name] for name in saved_order if name in by_name]
    ordered += [path for path in photos if os.path.basename(path) not in saved_order]
    render_photo_mode(ordered)
    st.divider()
    left, right = st.columns(2)
    with left:
        if st.button("🖼️ Edit photos and display settings", use_container_width=True):
            st.session_state.page = "studio"
            st.rerun()
    with right:
        if st.button("Continue to the letter 💌", use_container_width=True):
            st.session_state.page = "letter"
            st.rerun()


def show_studio():
    hero("Photo Gallery & Editor", "Customize each memory and save your choices")
    upload = st.file_uploader("Add photos to your gallery", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key="photo_uploads")
    if upload and st.button("Save uploaded photos", key="save_photos"):
        saved_names = []
        for file in upload:
            path = save_uploaded_file(file, PHOTO_DIR)
            if path: saved_names.append(os.path.basename(path))
        if saved_names:
            st.session_state.photo_order = list(st.session_state.photo_order) + saved_names
            save_settings(); st.success(f"Saved {len(saved_names)} photo(s)."); st.rerun()
    photos = list_photos()
    if not photos:
        st.info("Add images to assets/photos or use the uploader above."); return
    names = [os.path.basename(path) for path in photos]
    initial_name = st.session_state.get("edit_photo_name", names[0])
    selected_name = st.selectbox("Choose a photo to customize", names, index=names.index(initial_name) if initial_name in names else 0, key="studio_selected_photo")
    path = os.path.join(PHOTO_DIR, selected_name)
    cfg = get_photo_config(path)
    left, right = st.columns([1.05, 1.25], gap="medium")
    with left:
        st.markdown("#### Live preview")
        framed = make_frame_image(path, cfg)
        if framed is not None:
            framed = style_photo_image(framed, cfg)
            if cfg["rotation"]: framed = framed.rotate(cfg["rotation"], expand=True, fillcolor=cfg["frame_color"])
            st.image(framed, use_container_width=True)
            if st.session_state.show_captions:
                st.markdown(f'<div class="caption">{html.escape(str(cfg["caption"]))}</div>', unsafe_allow_html=True)
        st.caption("The full original photo is preserved; it is fitted inside the frame.")
    with right:
        st.markdown("#### Photo settings")
        width = st.slider("Display width (%)", 35, 100, cfg["width"], key=f"width_{selected_name}")
        height = st.slider("Display height setting", 120, 520, cfg["height"], key=f"height_{selected_name}")
        frame_options = ["Classic", "Double Gold", "Polaroid", "Minimal"]
        frame = st.selectbox("Frame design", frame_options, index=frame_options.index(cfg["frame"]) if cfg["frame"] in frame_options else 0, key=f"frame_{selected_name}")
        frame_color = st.color_picker("Frame colour", cfg["frame_color"], key=f"color_{selected_name}")
        thickness = st.slider("Frame thickness", 1, 24, cfg["thickness"], key=f"thickness_{selected_name}")
        mat = st.slider("Inner spacing", 0, 36, cfg["mat"], key=f"mat_{selected_name}")
        radius = st.slider("Corner roundness (preview card)", 0, 30, cfg["radius"], key=f"radius_{selected_name}")
        rotation = st.slider("Rotation", -15, 15, cfg["rotation"], key=f"rotation_{selected_name}")
        idea = st.selectbox("Emotional caption ideas", ["Choose an idea…"] + EMOTIONAL_CAPTIONS, key=f"caption_idea_{selected_name}")
        if st.button("Use selected caption idea", key=f"use_caption_idea_{selected_name}"):
            if idea != "Choose an idea…":
                update_photo_config(path, caption=idea)
                st.rerun()
        caption = st.text_area("Customize this photo's emotional caption", value=cfg["caption"], key=f"caption_{selected_name}", height=100, placeholder="Example: Your smile makes every memory brighter. 💚")
        shadow = st.toggle("Soft shadow", cfg["shadow"], key=f"shadow_{selected_name}")
        if st.button("💾 Save this photo's settings", use_container_width=True):
            update_photo_config(path, width=width, height=height, frame=frame, frame_color=frame_color, thickness=thickness, mat=mat, radius=radius, rotation=rotation, caption=caption, shadow=shadow)
            st.success("Photo settings saved permanently."); st.rerun()
    st.divider()
    st.markdown("#### Arrange photo order")
    current_order = st.session_state.photo_order
    ordered_names = [name for name in current_order if name in names]
    ordered_names += [name for name in names if name not in ordered_names]
    chosen_order = st.multiselect("Select the order (top to bottom)", names, default=ordered_names, key="order_editor")
    if st.button("Save photo order"):
        st.session_state.photo_order = chosen_order; save_settings(); st.success("Gallery order saved."); st.rerun()


def show_letter():
    hero(st.session_state.letter_title, "Words from the heart")
    st.markdown(f'<div class="memory-card" style="padding:clamp(18px,4vw,42px);max-width:950px;margin:auto"><div style="font-size:1.05rem;line-height:1.9;white-space:pre-wrap;color:#4c3b24">{html.escape(st.session_state.letter_text)}</div></div>', unsafe_allow_html=True)


def show_reveal():
    hero("A Day Made for You 🎁", "Wishing you love, laughter and a year full of beautiful moments")
    st.markdown('<div class="memory-card" style="padding:clamp(22px,5vw,60px);max-width:1000px;margin:auto"><div style="font-size:clamp(2rem,6vw,4rem);color:#b18b2f">Happy Birthday, Monalisa! 💚</div><p style="font-size:1.2rem;line-height:1.8;color:#473a27">May every new chapter bring you reasons to smile, people who value you, and memories you will treasure for years.</p><div style="font-size:2rem">✨ 💚 🎂 💚 ✨</div></div>', unsafe_allow_html=True)
    photos = list_photos()
    if photos:
        cols = st.columns(min(3, len(photos[:3])))
        for col, path in zip(cols, photos[:3]):
            with col: st.image(path, use_container_width=True)


def show_countdown():
    now = datetime.now(IST)
    remaining = BIRTHDAY_OPENS_AT - now
    hero("A Special Day Is Getting Closer ✨", "A few more moments until the memories unlock")
    if remaining.total_seconds() <= 0:
        st.success("The birthday date has arrived. You can open the memories now."); return
    total = int(remaining.total_seconds())
    days, rem = divmod(total, 86400); hours, rem = divmod(rem, 3600); minutes, seconds = divmod(rem, 60)
    cols = st.columns(4)
    for col, value, label in zip(cols, [days, hours, minutes, seconds], ["Days", "Hours", "Minutes", "Seconds"]):
        with col: st.markdown(f'<div class="memory-card"><div style="font-size:clamp(1.5rem,4vw,3rem);color:#b18b2f;font-weight:700">{value}</div><div>{label}</div></div>', unsafe_allow_html=True)
    st.caption("The real unlock is 3 November 2026 at 12:00 AM IST.")


def main():
    apply_global_css()
    apply_custom_background()
    owner_mode = owner_settings_gate()
    if owner_mode:
        sidebar_customizer()

    # Keep one shared music player in the same place across the app's pages.
    play_music()
    now = datetime.now(IST)
    locked = now < BIRTHDAY_OPENS_AT and not TEST_MODE
    if TEST_MODE:
        st.warning("LOCAL PREVIEW MODE IS ON. You can test the pages before the birthday. The real date lock remains 3 November 2026 at 12:00 AM IST.")
    # Before the birthday, only the authenticated owner can enter the app/editor.
    if locked and not owner_mode:
        show_countdown()
        return
    # Never allow a recipient to open the owner-only photo editor by typing/selecting its page.
    if st.session_state.page == "studio" and not owner_mode:
        st.session_state.page = "quiz" if st.session_state.get("logged_in", False) else "login"
        st.rerun()
    # Enforce the intended recipient flow even if a page is selected directly.
    if st.session_state.page == "photos" and not st.session_state.get("quiz_done", False):
        st.session_state.page = "quiz"
    if st.session_state.page == "letter" and not st.session_state.get("memories_seen", False):
        st.session_state.page = "photos" if st.session_state.get("quiz_done", False) else "quiz"

    if not st.session_state.logged_in and st.session_state.page != "login" and not owner_mode:
        st.session_state.page = "login"
    if st.session_state.page == "login":
        show_login(); return
    nav_bar()
    page = st.session_state.page
    if page == "home":
        st.session_state.page = "quiz"
        st.rerun()
    elif page == "quiz": show_quiz()
    elif page == "photos": show_photos()
    elif page == "studio": show_studio()
    elif page == "letter": show_letter()
    elif page == "reveal": show_reveal()
    else:
        st.session_state.page = "quiz"
        st.rerun()
    if st.session_state.logged_in:
        with st.sidebar:
            if st.button("🔒 Lock app / return to login", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.owner_authenticated = False
                st.session_state.page = "login"
                st.rerun()


if __name__ == "__main__":
    main()
