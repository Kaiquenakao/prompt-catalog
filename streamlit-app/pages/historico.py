import httpx
import streamlit as st

st.set_page_config(layout="wide", page_title="Histórico")

st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    section[data-testid="stSidebar"] { display: none !important; }
    hr { border-color: rgba(255,255,255,0.08) !important; }
    .stTextInput > div > div > input {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important; border-radius: 10px !important;
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


def _base():
    return st.secrets["API_GATEWAY_URL"]


def fetch_all_executions(prompt_name: str = "", run_type: str = "") -> list:
    try:
        params = {}
        if prompt_name:
            params["prompt_name"] = prompt_name
        if run_type:
            params["run_type"] = run_type
        resp = httpx.get(
            f"{_base()}/executions",
            headers=_headers(),
            params=params,
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json().get("executions", [])
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return []


def to_brasilia(utc_str: str) -> str:
    try:
        from datetime import datetime, timezone, timedelta

        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
        brt = dt.astimezone(timezone(timedelta(hours=-3)))
        return brt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        return utc_str[:19].replace("T", " ")


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


# ── HEADER + NAV ──────────────────────────────────────────
st.markdown(
    """<div style="border-bottom:1px solid rgba(255,255,255,0.07);
    margin:-4rem -4rem 2rem -4rem; padding:14px 3rem;
    display:flex; align-items:center; justify-content:space-between;
    background:rgba(255,255,255,0.02);">
    <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-family:'Space Grotesk',sans-serif; font-size:20px; font-weight:600; color:#f1f5f9;">
            Histórico</span>
        <span style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#4b5563;">
            — Todas as execuções</span>
    </div>
    <div style="display:flex; gap:6px;">
        <a href="/" target="_self" style="font-family:'Space Grotesk',sans-serif; font-size:12px;
            color:#64748b; padding:6px 14px; border-radius:8px; text-decoration:none;
            border:1px solid transparent;">Catálogo</a>
        <a href="/prompt_playground" target="_self" style="font-family:'Space Grotesk',sans-serif; font-size:12px;
            color:#64748b; padding:6px 14px; border-radius:8px; text-decoration:none;
            border:1px solid transparent;">Playground</a>
        <a href="/historico" target="_self" style="font-family:'Space Grotesk',sans-serif; font-size:12px; font-weight:600;
            color:#a78bfa; background:rgba(124,58,237,0.15); border:1px solid rgba(124,58,237,0.3);
            padding:6px 14px; border-radius:8px; text-decoration:none;">Histórico</a>
    </div>
    </div>""",
    unsafe_allow_html=True,
)

# ── FILTROS ───────────────────────────────────────────────
from datetime import date, timedelta

f1, f2, f3, f4, f5 = st.columns([3, 2, 1.5, 1.5, 1], gap="small")
with f1:
    st.markdown(
        "<p style=\"font-size:10px; color:#475569; margin:0 0 4px; font-family:'Space Grotesk',sans-serif; text-transform:uppercase; letter-spacing:0.1em;\">Nome do prompt</p>",
        unsafe_allow_html=True,
    )
    search_name = st.text_input(
        "buscar",
        placeholder="buscar por nome...",
        label_visibility="collapsed",
        help="Filtra execuções pelo nome do prompt. A busca é parcial — 'suporte' retorna 'suporte_reclamacao'.",
    )
with f2:
    st.markdown(
        "<p style=\"font-size:10px; color:#475569; margin:0 0 4px; font-family:'Space Grotesk',sans-serif; text-transform:uppercase; letter-spacing:0.1em;\">Tipo</p>",
        unsafe_allow_html=True,
    )
    run_type_filter = st.selectbox(
        "tipo",
        options=["todos", "playground", "production"],
        format_func=lambda x: {
            "todos": "Todos",
            "playground": "Playground",
            "production": "Produção",
        }[x],
        label_visibility="collapsed",
        help=(
            "Playground — execuções feitas manualmente no Playground ou na aba Testar dos Detalhes.\n\n"
            "Produção — execuções feitas por sistemas externos via API (sem session_id)."
        ),
    )
with f3:
    st.markdown(
        "<p style=\"font-size:10px; color:#475569; margin:0 0 4px; font-family:'Space Grotesk',sans-serif; text-transform:uppercase; letter-spacing:0.1em;\">De</p>",
        unsafe_allow_html=True,
    )
    date_from = st.date_input(
        "De",
        value=date.today() - timedelta(days=7),
        label_visibility="collapsed",
        help="Data inicial do período. Padrão: últimos 7 dias.",
    )
with f4:
    st.markdown(
        "<p style=\"font-size:10px; color:#475569; margin:0 0 4px; font-family:'Space Grotesk',sans-serif; text-transform:uppercase; letter-spacing:0.1em;\">Até</p>",
        unsafe_allow_html=True,
    )
    date_to = st.date_input(
        "Até",
        value=date.today(),
        label_visibility="collapsed",
        help="Data final do período. Padrão: hoje.",
    )
with f5:
    st.markdown(
        '<p style="font-size:10px; color:#475569; margin:0 0 4px;">&nbsp;</p>',
        unsafe_allow_html=True,
    )
    buscar = st.button("Buscar", type="secondary", use_container_width=True)

st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

# ── CARREGA ───────────────────────────────────────────────
cache_key = f"hist_{search_name}_{run_type_filter}"
if buscar or cache_key not in st.session_state:
    with st.spinner("Carregando execuções..."):
        rt = "" if run_type_filter == "todos" else run_type_filter
        st.session_state[cache_key] = fetch_all_executions(search_name, rt)

executions = st.session_state.get(cache_key, [])

# filtra execuções sem nome válido de prompt
executions = [
    e
    for e in executions
    if e.get("prompt_name", "")
    and " " not in (e.get("prompt_name") or "")
    and len(e.get("prompt_name") or "") <= 60
]

# ordena por data mais recente
executions = sorted(executions, key=lambda x: x.get("created_at", ""), reverse=True)

# filtra por período
from datetime import datetime, timezone


def in_range(utc_str: str) -> bool:
    try:
        dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00")).date()
        return date_from <= dt <= date_to
    except Exception:
        return True


executions = [e for e in executions if in_range(e.get("created_at", ""))]

if not executions:
    st.markdown(
        """<div style="border:1px dashed rgba(255,255,255,0.08); border-radius:12px;
        padding:48px 24px; text-align:center; margin-top:16px;">
        <p style="font-family:'Space Grotesk',sans-serif; font-size:14px; color:#374151; margin:0;">
        Nenhuma execução encontrada.</p></div>""",
        unsafe_allow_html=True,
    )
else:
    st.caption(f"{len(executions)} execução(ões) encontrada(s)")
    st.markdown("<div style='height:4px'/>", unsafe_allow_html=True)

    h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 1, 2, 2, 1.5, 1.2, 1])
    for col, label in zip(
        [h1, h2, h3, h4, h5, h6, h7],
        ["Prompt", "Versão", "Modelo", "Data (BRT)", "Tokens", "Tipo", "Status"],
    ):
        col.markdown(
            f'<p style="font-size:9px; color:#374151; text-transform:uppercase; '
            f"letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 4px;\">{label}</p>",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:2px'/>", unsafe_allow_html=True)

    for ex in executions:
        raw_name = ex.get("prompt_name", "") or ""
        version = ex.get("prompt_version", "—") or "—"
        status = ex.get("status", "—")
        model = model_short(ex.get("model_id", "—"))
        in_tok = ex.get("input_tokens", 0)
        out_tok = ex.get("output_tokens", 0)
        latency = ex.get("latency_ms", 0)
        date_str = to_brasilia(ex.get("created_at", ""))
        run_type = ex.get("run_type", "—")

        # filtra nomes inválidos: sem espaço e curtos = nome real de prompt
        is_valid_name = raw_name and " " not in raw_name and len(raw_name) <= 60
        prompt_name = raw_name if is_valid_name else "—"

        s_color = "#22c55e" if status == "done" else "#ef4444"
        s_bg = "rgba(34,197,94,0.15)" if status == "done" else "rgba(239,68,68,0.15)"
        s_border = "rgba(34,197,94,0.4)" if status == "done" else "rgba(239,68,68,0.4)"
        t_color = "#a78bfa" if run_type == "playground" else "#38bdf8"
        t_bg = (
            "rgba(124,58,237,0.12)"
            if run_type == "playground"
            else "rgba(56,189,248,0.12)"
        )
        t_border = (
            "rgba(124,58,237,0.3)"
            if run_type == "playground"
            else "rgba(56,189,248,0.3)"
        )

        if is_valid_name:
            name_cell = (
                f'<a href="/detalhes?prompt_id={prompt_name}" target="_self" '
                f'style="font-weight:500; color:#a78bfa; text-decoration:none; '
                f'border-bottom:1px solid rgba(167,139,250,0.3);">{prompt_name}</a>'
            )
        else:
            name_cell = '<span style="color:#374151; font-size:11px;">sem nome</span>'

        st.markdown(
            f"""<div style="display:grid; grid-template-columns:2fr 0.8fr 1.5fr 1.8fr 1.2fr 1fr 0.8fr;
            align-items:center; gap:10px; padding:10px 14px;
            background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06);
            border-radius:8px; margin-bottom:6px;
            font-family:'Space Grotesk',sans-serif; font-size:12px; color:#94a3b8;">
            {name_cell}
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#7c3aed;">{version}</span>
            <span>{model}</span>
            <span style="font-size:11px;">{date_str}</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px;">{in_tok}↑ {out_tok}↓</span>
            <span style="background:{t_bg}; color:{t_color}; border:1px solid {t_border};
                border-radius:4px; padding:2px 8px; font-size:10px;
                font-family:'JetBrains Mono',monospace;">{run_type}</span>
            <span style="background:{s_bg}; color:{s_color}; border:1px solid {s_border};
                border-radius:4px; padding:2px 8px; font-size:10px;
                font-family:'JetBrains Mono',monospace;">{status}</span>
            </div>""",
            unsafe_allow_html=True,
        )

        with st.expander("ver output", expanded=False):
            output = ex.get("output", "")
            vars_used = ex.get("variables_used", {})

            if vars_used:
                st.markdown(
                    '<p style="font-size:9px; color:#475569; text-transform:uppercase; '
                    "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 4px;\">"
                    "Variáveis</p>",
                    unsafe_allow_html=True,
                )
                for k, v in vars_used.items():
                    st.markdown(
                        f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:11px; "
                        f'color:#94a3b8; margin:0 0 3px;">'
                        f'<span style="color:#475569;">{k}:</span> {v}</p>',
                        unsafe_allow_html=True,
                    )
                st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)

            st.markdown(
                '<p style="font-size:10px; color:#7c3aed; text-transform:uppercase; '
                "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; "
                'margin:0 0 8px; font-weight:600;">Output</p>',
                unsafe_allow_html=True,
            )
            if output:
                clean = "\n\n".join(
                    p.strip() for p in output.split("\n\n") if p.strip()
                )
                with st.container(border=True):
                    st.markdown(clean)
            else:
                st.caption("Sem output.")
