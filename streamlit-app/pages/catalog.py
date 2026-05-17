import httpx
import streamlit as st

st.set_page_config(layout="wide", page_title="Prompt Catalog")

st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    section[data-testid="stSidebar"] { display: none !important; }
    hr { border-color: rgba(255,255,255,0.08) !important; }
    .stTextInput > div > div > input {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        padding: 10px 14px !important;
    }
    .stTextInput label {
        color: #94a3b8 !important; font-size: 11px !important;
        letter-spacing: 0.12em !important; text-transform: uppercase !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px !important; color: #94a3b8 !important;
        font-family: 'Space Grotesk', sans-serif !important; font-size: 12px !important;
    }
    #MainMenu, footer, header { visibility: hidden; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.4); border-radius: 2px; }
</style>
""",
    unsafe_allow_html=True,
)


def _headers():
    return {"x-api-key": st.secrets["API_KEY"], "Content-Type": "application/json"}


def fetch_prompts() -> list:
    try:
        resp = httpx.get(
            f"{st.secrets['API_GATEWAY_URL']}/prompts",
            headers=_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("prompts", [])
    except Exception as e:
        st.error(f"Erro ao carregar prompts: {e}")
        return []


def to_brasilia(utc_str: str) -> str:
    try:
        from datetime import datetime, timezone, timedelta

        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        brt = dt.astimezone(timezone(timedelta(hours=-3)))
        return brt.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return utc_str[:16].replace("T", " ")


def model_short(model_id: str) -> str:
    for old, new in [
        ("claude-haiku-4-5", "Claude Haiku 4.5"),
        ("claude-sonnet-4-5", "Claude Sonnet 4.5"),
        ("claude-sonnet-4-6", "Claude Sonnet 4.6"),
        ("claude-opus-4-5", "Claude Opus 4.5"),
        ("claude-opus-4-6", "Claude Opus 4.6"),
        ("claude-opus-4-7", "Claude Opus 4.7"),
        ("claude-opus-4-1", "Claude Opus 4.1"),
    ]:
        if old in model_id:
            return new
    return model_id.split(".")[-1][:30]


if "catalog_prompts" not in st.session_state:
    with st.spinner("Carregando catálogo..."):
        st.session_state.catalog_prompts = fetch_prompts()

# ── HEADER ────────────────────────────────────────────────
st.markdown(
    """<div style="border-bottom:1px solid rgba(255,255,255,0.07);
    margin:-4rem -4rem 2rem -4rem; padding:16px 3rem; display:flex; align-items:center; gap:12px;
    background:rgba(255,255,255,0.02);">
    <span style="font-family:'Space Grotesk',sans-serif; font-size:20px; font-weight:600; color:#f1f5f9;">
        Prompt Catalog</span>
    <span style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#4b5563;">
        — Prompts em produção</span></div>""",
    unsafe_allow_html=True,
)

# ── BUSCA ─────────────────────────────────────────────────
sc1, sc2 = st.columns([5, 1], gap="small")
with sc1:
    search = st.text_input(
        "buscar",
        placeholder="buscar por nome ou descrição...",
        label_visibility="collapsed",
    )
with sc2:
    if st.button("Atualizar", type="secondary", use_container_width=True):
        st.session_state.catalog_prompts = fetch_prompts()
        st.rerun()

st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

# ── FILTRA ────────────────────────────────────────────────
prompts = st.session_state.catalog_prompts
if search:
    term = search.lower()
    prompts = [
        p
        for p in prompts
        if term in p.get("prompt_id", "").lower()
        or term in p.get("description", "").lower()
    ]

# ── CARDS ─────────────────────────────────────────────────
if not prompts:
    st.markdown("<div style='height:40px'/>", unsafe_allow_html=True)
    st.markdown(
        "<p style=\"text-align:center; color:#374151; font-size:14px; font-family:'Space Grotesk',sans-serif;\">"
        "Nenhum prompt em produção ainda. Crie um no Playground e clique em Deploy.</p>",
        unsafe_allow_html=True,
    )
else:
    st.caption(f"{len(prompts)} prompt(s) encontrado(s)")

    for p in prompts:
        pid = p.get("prompt_id", "—")
        version = p.get("version", "—")
        description = p.get("description", "") or "Sem descrição."
        is_active = p.get("is_active", False)
        created_at = to_brasilia(p.get("created_at", ""))
        model = model_short(p.get("model_id", "—"))
        temperature = p.get("temperature", 0)
        max_tokens = p.get("max_tokens", "—")

        with st.container(border=True):
            # linha 1: nome + versão + status + data
            r1c1, r1c2 = st.columns([4, 1])
            with r1c1:
                st.markdown(
                    f"<span style=\"font-family:'Space Grotesk',sans-serif; font-size:17px; "
                    f'font-weight:600; color:#f1f5f9;">{pid}</span>'
                    f"&nbsp;&nbsp;"
                    f"<span style=\"font-family:'JetBrains Mono',monospace; font-size:11px; "
                    f"color:#7c3aed; background:rgba(124,58,237,0.12); padding:2px 10px; "
                    f'border-radius:999px; border:1px solid rgba(124,58,237,0.3);">{version}</span>'
                    f"&nbsp;&nbsp;"
                    + (
                        '<span style="background:rgba(34,197,94,0.15); color:#22c55e; '
                        "border:1px solid rgba(34,197,94,0.4); border-radius:4px; "
                        "padding:2px 8px; font-size:10px; font-family:'JetBrains Mono',monospace;\">ativo</span>"
                        if is_active
                        else '<span style="background:rgba(255,255,255,0.06); color:#475569; '
                        "border:1px solid rgba(255,255,255,0.1); border-radius:4px; "
                        "padding:2px 8px; font-size:10px; font-family:'JetBrains Mono',monospace;\">inativo</span>"
                    ),
                    unsafe_allow_html=True,
                )
            with r1c2:
                st.markdown(
                    f'<p style="text-align:right; font-size:11px; color:#2a3142; '
                    f"font-family:'Space Grotesk',sans-serif; margin:4px 0 0;\">{created_at}</p>",
                    unsafe_allow_html=True,
                )

            # linha 2: descrição
            st.markdown(
                f"<p style=\"font-family:'Space Grotesk',sans-serif; font-size:13px; "
                f'color:#64748b; line-height:1.6; margin:6px 0 0;">{description}</p>',
                unsafe_allow_html=True,
            )

            st.divider()

            # linha 3: modelo · temperatura · max tokens
            f1, f2, f3, _ = st.columns([2, 2, 2, 3])
            with f1:
                st.markdown(
                    '<p style="font-size:10px; color:#374151; text-transform:uppercase; '
                    "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 2px;\">Modelo</p>"
                    f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:12px; "
                    f'color:#94a3b8; margin:0;">{model}</p>',
                    unsafe_allow_html=True,
                )
            with f2:
                st.markdown(
                    '<p style="font-size:10px; color:#374151; text-transform:uppercase; '
                    "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 2px;\">Temperatura</p>"
                    f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:12px; "
                    f'color:#94a3b8; margin:0;">{temperature:.2f}</p>',
                    unsafe_allow_html=True,
                )
            with f3:
                st.markdown(
                    '<p style="font-size:10px; color:#374151; text-transform:uppercase; '
                    "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 2px;\">Max tokens</p>"
                    f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:12px; "
                    f'color:#94a3b8; margin:0;">{max_tokens}</p>',
                    unsafe_allow_html=True,
                )
            with _:
                st.markdown("<div style='height:4px'/>", unsafe_allow_html=True)
                if st.button(
                    "Ver detalhes",
                    key=f"det_{pid}",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state["detail_prompt_id"] = pid
                    st.switch_page("pages/detalhes.py")
