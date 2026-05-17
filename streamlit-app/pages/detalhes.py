import re
import time
import uuid

import httpx
import streamlit as st

st.set_page_config(layout="wide", page_title="Detalhes do Prompt")

st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    section[data-testid="stSidebar"] { display: none !important; }
    hr { border-color: rgba(255,255,255,0.08) !important; }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        padding: 10px 14px !important;
        caret-color: #a78bfa !important;
    }
    .stTextInput label, .stTextArea label {
        color: #94a3b8 !important; font-size: 11px !important;
        letter-spacing: 0.12em !important; text-transform: uppercase !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
        border: none !important; border-radius: 8px !important; color: white !important;
        font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important;
        font-size: 12px !important;
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


# ── API ───────────────────────────────────────────────────
def _headers():
    return {"x-api-key": st.secrets["API_KEY"], "Content-Type": "application/json"}


def _base():
    return st.secrets["API_GATEWAY_URL"]


def fetch_versions(prompt_id: str) -> list:
    try:
        resp = httpx.get(
            f"{_base()}/prompts/{prompt_id}", headers=_headers(), timeout=10.0
        )
        resp.raise_for_status()
        return resp.json().get("versions", [])
    except Exception as e:
        st.error(f"Erro ao carregar versões: {e}")
        return []


def run_prompt_api(payload: dict) -> dict:
    resp = httpx.post(f"{_base()}/run", headers=_headers(), json=payload, timeout=310.0)
    resp.raise_for_status()
    return resp.json()


def get_execution_api(execution_id: str) -> dict:
    resp = httpx.get(
        f"{_base()}/executions/{execution_id}", headers=_headers(), timeout=10.0
    )
    resp.raise_for_status()
    return resp.json()


def fetch_history(prompt_name: str, run_type: str) -> list:
    try:
        resp = httpx.get(
            f"{_base()}/executions",
            headers=_headers(),
            params={"prompt_name": prompt_name, "run_type": run_type},
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json().get("executions", [])
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return []


def toggle_status(prompt_id: str, version: str, is_active: bool) -> bool:
    try:
        resp = httpx.patch(
            f"{_base()}/prompts/{prompt_id}/versions/{version}",
            headers=_headers(),
            json={"is_active": is_active},
            timeout=10.0,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status: {e}")
        return False


# ── helpers ───────────────────────────────────────────────
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


def extract_variables(prompt: str) -> list:
    return list(dict.fromkeys(re.findall(r"\{\{(\w+)\}\}", prompt)))


# ── render history (definido antes de ser usado) ──────────
def render_history(executions: list, current_version: str):
    if not executions:
        st.info("Nenhuma execução encontrada.")
        return

    st.caption(f"{len(executions)} execução(ões)")

    for idx, ex in enumerate(executions):
        num = len(executions) - idx
        version = ex.get("prompt_version", "—")
        status = ex.get("status", "—")
        model = model_short(ex.get("model_id", "—"))
        in_tok = ex.get("input_tokens", 0)
        out_tok = ex.get("output_tokens", 0)
        latency = ex.get("latency_ms", 0)
        date = to_brasilia(ex.get("created_at", ""))

        s_color = "#22c55e" if status == "done" else "#ef4444"
        s_bg = "rgba(34,197,94,0.15)" if status == "done" else "rgba(239,68,68,0.15)"
        s_border = "rgba(34,197,94,0.4)" if status == "done" else "rgba(239,68,68,0.4)"
        v_color = "#a78bfa" if version == current_version else "#475569"

        st.markdown(
            f"""<div style="display:grid; grid-template-columns:28px 60px 160px 1fr 110px 70px;
            align-items:center; gap:10px; padding:6px 0 2px;
            font-family:'Space Grotesk',sans-serif; font-size:12px; color:#94a3b8;">
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:#2a3142;">#{num}</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px; color:{v_color};">{version}</span>
            <span>{model}</span>
            <span>{date}</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px;">
                {in_tok}↑ {out_tok}↓ · {latency}ms</span>
            <span style="background:{s_bg}; color:{s_color}; border:1px solid {s_border};
                border-radius:4px; padding:2px 8px; font-size:10px;
                font-family:'JetBrains Mono',monospace; text-align:center;">{status}</span>
            </div>""",
            unsafe_allow_html=True,
        )

        with st.expander("ver detalhes", expanded=False):
            sp = ex.get("system_prompt", "")
            if sp:
                st.markdown(
                    '<p style="font-size:9px; color:#475569; text-transform:uppercase; '
                    "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 4px;\">"
                    "System prompt</p>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:11px; "
                    f'color:#94a3b8; line-height:1.6; white-space:pre-wrap; margin:0 0 14px;">'
                    f"{sp[:400]}{'...' if len(sp) > 400 else ''}</p>",
                    unsafe_allow_html=True,
                )

            # variáveis — extraídas do system prompt original
            vars_used = ex.get("variables_used", {})
            if vars_used:
                st.markdown(
                    '<p style="font-size:9px; color:#475569; text-transform:uppercase; '
                    "letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 6px;\">"
                    "Variáveis</p>",
                    unsafe_allow_html=True,
                )
                for k, val in vars_used.items():
                    st.markdown(
                        f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:11px; "
                        f'color:#94a3b8; margin:0 0 4px;">'
                        f'<span style="color:#475569;">{k}:</span> {val}</p>',
                        unsafe_allow_html=True,
                    )
                st.markdown("<div style='height:10px'/>", unsafe_allow_html=True)
            else:
                st.markdown(
                    "<p style=\"font-size:9px; color:#2a3142; font-family:'Space Grotesk',sans-serif; "
                    'margin:0 0 14px;">Sem variáveis registradas nesta execução.</p>',
                    unsafe_allow_html=True,
                )

            output = ex.get("output", "")
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

        st.markdown(
            "<div style='border-bottom:1px solid rgba(255,255,255,0.05); margin:2px 0 6px;'/>",
            unsafe_allow_html=True,
        )


# ── execute run com polling ───────────────────────────────
def execute_run(
    system_prompt,
    prompt_name,
    prompt_version,
    model_id,
    model_name,
    temperature,
    max_tokens,
    session_id,
    variables_used=None,
):
    payload = {
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "system_prompt": system_prompt,
        "model_id": model_id,
        "temperature": temperature,
        "max_tokens": int(max_tokens),
        "session_id": session_id,
        "variables_used": variables_used or {},
    }
    with st.spinner("Executando..."):
        result = run_prompt_api(payload)

    if result.get("status") == "done":
        st.session_state.detail_output = result.get("output", "")
        st.session_state.detail_output_meta = (
            f"{model_name}  ·  temp {temperature:.2f}  ·  "
            f"{result.get('input_tokens', 0)} in / {result.get('output_tokens', 0)} out  ·  "
            f"{result.get('latency_ms', 0)}ms"
        )
        st.rerun()
        return

    execution_id = result.get("execution_id")
    if not execution_id:
        st.error("execution_id não retornado.")
        return

    progress = st.progress(0, text="Aguardando resposta...")
    for i in range(60):
        time.sleep(2)
        progress.progress(min(i * 2, 95), text=f"Processando... {(i + 1) * 2}s")
        try:
            data = get_execution_api(execution_id)
            if data.get("status") == "done":
                progress.empty()
                st.session_state.detail_output = data.get("output", "")
                st.session_state.detail_output_meta = (
                    f"{model_name}  ·  temp {temperature:.2f}  ·  "
                    f"{data.get('input_tokens', 0)} in / {data.get('output_tokens', 0)} out  ·  "
                    f"{data.get('latency_ms', 0)}ms"
                )
                st.rerun()
                return
            if data.get("status") == "error":
                progress.empty()
                st.error(f"Erro: {data.get('output', '')}")
                return
        except Exception:
            pass
    progress.empty()
    st.error("Timeout: execução excedeu 120s.")


# ── session state ──────────────────────────────────────────
if "detail_session_id" not in st.session_state:
    st.session_state.detail_session_id = str(uuid.uuid4())
if "detail_output" not in st.session_state:
    st.session_state.detail_output = None
if "detail_output_meta" not in st.session_state:
    st.session_state.detail_output_meta = None

# ── PROMPT ID ─────────────────────────────────────────────
prompt_id = st.session_state.get("detail_prompt_id", "")

if not prompt_id:
    st.markdown(
        """<div style="display:flex; align-items:center; justify-content:center; height:60vh; text-align:center;">
        <div>
            <p style="font-size:15px; color:#2a3142; font-family:'Space Grotesk',sans-serif;">
                Nenhum prompt selecionado.</p>
            <p style="font-size:12px; color:#1e2430; font-family:'Space Grotesk',sans-serif;">
                Acesse esta página pelo Catálogo.</p>
        </div></div>""",
        unsafe_allow_html=True,
    )
    st.stop()

# ── CARREGA VERSÕES ───────────────────────────────────────
cache_key = f"versions_{prompt_id}"
if cache_key not in st.session_state:
    with st.spinner("Carregando versões..."):
        st.session_state[cache_key] = fetch_versions(prompt_id)

versions = st.session_state[cache_key]

if not versions:
    st.error("Nenhuma versão encontrada.")
    st.stop()

version_labels = [v.get("version", "—") for v in versions]
sel_key = f"sel_ver_{prompt_id}"
if sel_key not in st.session_state:
    st.session_state[sel_key] = version_labels[0]

# ── HEADER ────────────────────────────────────────────────
st.markdown(
    f"""<div style="border-bottom:1px solid rgba(255,255,255,0.07);
    margin:-4rem -4rem 2rem -4rem; padding:14px 3rem; display:flex; align-items:center; gap:10px;
    background:rgba(255,255,255,0.02);">
    <a href="/catalog" style="font-family:'Space Grotesk',sans-serif; font-size:12px;
        color:#475569; text-decoration:none;">← Catálogo</a>
    <span style="color:#1e2430;">/</span>
    <span style="font-family:'Space Grotesk',sans-serif; font-size:16px;
        font-weight:600; color:#f1f5f9;">{prompt_id}</span>
    </div>""",
    unsafe_allow_html=True,
)

# ── LAYOUT ────────────────────────────────────────────────
col_ver, col_main = st.columns([1, 4], gap="large")

# ── VERSÕES ───────────────────────────────────────────────
with col_ver:
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#7c3aed;
        letter-spacing:0.15em; text-transform:uppercase; margin:0 0 10px; font-weight:600;">
        Versões</p>""",
        unsafe_allow_html=True,
    )

    for v in versions:
        vlabel = v.get("version", "—")
        is_active = v.get("is_active", False)
        is_sel = st.session_state[sel_key] == vlabel

        if is_sel:
            st.markdown(
                f"""<div style="background:rgba(124,58,237,0.12); border-left:3px solid #7c3aed;
                border-radius:8px; padding:8px 12px; margin-bottom:6px;">
                <p style="font-family:'JetBrains Mono',monospace; font-size:13px;
                    font-weight:600; color:#a78bfa; margin:0 0 2px;">{vlabel}</p>
                <p style="font-size:10px; color:#475569; margin:0; font-family:'Space Grotesk',sans-serif;">
                    {"🟢 ativo" if is_active else "⚪ inativo"}</p>
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            badge = "🟢" if is_active else "⚪"
            if st.button(
                f"{badge}  {vlabel}",
                key=f"ver_{vlabel}",
                type="secondary",
                use_container_width=True,
            ):
                st.session_state[sel_key] = vlabel
                st.session_state.detail_output = None
                st.session_state.detail_output_meta = None
                st.rerun()

# ── CONTEÚDO ──────────────────────────────────────────────
with col_main:
    sel_label = st.session_state[sel_key]
    v = next((x for x in versions if x.get("version") == sel_label), versions[0])

    model_id = v.get("model_id", "")
    model_name = model_short(model_id)
    temperature = v.get("temperature", 0.7)
    max_tokens = v.get("max_tokens", 1024)
    sys_prompt = v.get("system_prompt", "")
    description = v.get("description", "") or "Sem descrição."
    tags = v.get("tags", [])
    created_at = to_brasilia(v.get("created_at", ""))
    is_active = v.get("is_active", False)

    tab_info, tab_test, tab_hist = st.tabs(["Informações", "Testar", "Histórico"])

    # ── INFORMAÇÕES ───────────────────────────────────────
    with tab_info:
        h1, h2, h3 = st.columns([4, 1, 1])
        with h1:
            st.markdown(
                f"<p style=\"font-family:'Space Grotesk',sans-serif; font-size:15px; "
                f'font-weight:600; color:#f1f5f9; margin:8px 0 4px;">{prompt_id} '
                f"<span style=\"font-family:'JetBrains Mono',monospace; font-size:12px; "
                f'color:#7c3aed;">{sel_label}</span></p>',
                unsafe_allow_html=True,
            )
        with h2:
            new_active = st.toggle(
                "Ativo",
                value=is_active,
                key=f"toggle_{prompt_id}_{sel_label}",
                help="Ativa ou desativa esta versão em produção.",
            )
            if new_active != is_active:
                if toggle_status(prompt_id, sel_label, new_active):
                    for ver in st.session_state[cache_key]:
                        if ver.get("version") == sel_label:
                            ver["is_active"] = new_active
                    st.rerun()
        with h3:
            if st.button(
                "Editar no Playground", type="secondary", use_container_width=True
            ):
                st.info("Em breve.")

        # métricas compactas
        m1, m2, m3, m4, m5 = st.columns(5)
        for col, label, val in [
            (m1, "Modelo", model_name),
            (m2, "Temperatura", f"{temperature:.2f}"),
            (m3, "Max tokens", str(max_tokens)),
            (m4, "Status", "ativo" if is_active else "inativo"),
            (m5, "Deploy", created_at),
        ]:
            col.markdown(
                f'<div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.07); '
                f'border-radius:8px; padding:10px 12px;">'
                f'<p style="font-size:9px; color:#475569; text-transform:uppercase; letter-spacing:0.1em; '
                f"font-family:'Space Grotesk',sans-serif; margin:0 0 4px;\">{label}</p>"
                f"<p style=\"font-family:'JetBrains Mono',monospace; font-size:12px; color:#94a3b8; margin:0;\">"
                f"{val}</p></div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)
        st.divider()

        st.markdown(
            """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#7c3aed;
            letter-spacing:0.15em; text-transform:uppercase; margin:0 0 6px; font-weight:600;">
            Descrição</p>""",
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<p style=\"font-family:'Space Grotesk',sans-serif; font-size:13px; "
            f'color:#64748b; line-height:1.7; margin:0;">{description}</p>',
            unsafe_allow_html=True,
        )

        st.divider()

        st.markdown(
            """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#7c3aed;
            letter-spacing:0.15em; text-transform:uppercase; margin:0 0 6px; font-weight:600;">
            System prompt</p>""",
            unsafe_allow_html=True,
        )
        st.text_area(
            "system_prompt_view",
            value=sys_prompt,
            height=300,
            disabled=True,
            label_visibility="collapsed",
        )

        st.divider()

        st.markdown(
            """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#7c3aed;
            letter-spacing:0.15em; text-transform:uppercase; margin:0 0 8px; font-weight:600;">
            Tags</p>""",
            unsafe_allow_html=True,
        )
        if tags:
            chips = " ".join(
                f'<span style="background:rgba(124,58,237,0.15); color:#a78bfa; '
                f"border:1px solid rgba(124,58,237,0.35); border-radius:999px; "
                f"padding:3px 10px; font-size:11px; font-family:'Space Grotesk',sans-serif;\">{t}</span>"
                for t in tags
            )
            st.markdown(chips, unsafe_allow_html=True)
        else:
            st.markdown(
                '<p style="font-size:12px; color:#2a3142;">Sem tags.</p>',
                unsafe_allow_html=True,
            )

    # ── TESTAR ────────────────────────────────────────────
    with tab_test:
        st.markdown(
            f"""<div style="background:rgba(124,58,237,0.06); border:1px solid rgba(124,58,237,0.2);
            border-radius:10px; padding:10px 16px; margin-bottom:16px;
            font-family:'JetBrains Mono',monospace; font-size:12px; color:#a78bfa;
            display:flex; gap:16px;">
            <span>{prompt_id} {sel_label}</span>
            <span style="color:#2a3142;">·</span>
            <span>{model_name}</span>
            <span style="color:#2a3142;">·</span>
            <span>temp {temperature:.2f}</span>
            <span style="color:#2a3142;">·</span>
            <span>{max_tokens} tokens</span>
            </div>""",
            unsafe_allow_html=True,
        )

        # system prompt visível — somente leitura
        st.markdown(
            """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#475569;
            letter-spacing:0.15em; text-transform:uppercase; margin:0 0 6px; font-weight:600;">
            System prompt</p>""",
            unsafe_allow_html=True,
        )
        st.text_area(
            "test_sys_prompt",
            value=sys_prompt,
            height=160,
            disabled=True,
            label_visibility="collapsed",
        )

        st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)

        variables = extract_variables(sys_prompt)
        var_values = {}

        if variables:
            st.markdown(
                """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#f59e0b;
                letter-spacing:0.15em; text-transform:uppercase; margin:0 0 8px; font-weight:600;">
                Variáveis</p>""",
                unsafe_allow_html=True,
            )
            vcols = st.columns(min(len(variables), 3))
            for i, var in enumerate(variables):
                with vcols[i % 3]:
                    var_values[var] = st.text_area(
                        var.replace("_", " ").capitalize(),
                        placeholder=f"valor para {var}",
                        key=f"dvar_{var}_{sel_label}",
                        height=80,
                    )

        run_clicked = st.button("Run", type="primary")

        st.divider()

        st.markdown(
            """<p style="font-family:'Space Grotesk',sans-serif; font-size:10px; color:#7c3aed;
            letter-spacing:0.15em; text-transform:uppercase; margin:0 0 10px; font-weight:600;">
            Output</p>""",
            unsafe_allow_html=True,
        )

        if st.session_state.detail_output:
            clean = "\n\n".join(
                p.strip()
                for p in st.session_state.detail_output.split("\n\n")
                if p.strip()
            )
            st.markdown(
                f'<div style="font-size:10px; color:#22c55e; letter-spacing:0.1em; '
                f"text-transform:uppercase; font-family:'Space Grotesk',sans-serif; "
                f'margin-bottom:6px;">200 OK · {st.session_state.detail_output_meta}</div>',
                unsafe_allow_html=True,
            )
            with st.container(border=True):
                st.markdown(clean)
        else:
            st.markdown(
                """<div style="border:1px dashed rgba(255,255,255,0.08); border-radius:10px;
                padding:24px; font-family:'JetBrains Mono',monospace;
                font-size:13px; color:#2a3142;">
                Nenhuma execução ainda. Clique em Run para testar.</div>""",
                unsafe_allow_html=True,
            )

        if run_clicked:
            if variables and any(
                var_values.get(v2, "").strip() == "" for v2 in variables
            ):
                st.warning("Preencha todas as variáveis antes de executar.")
            else:
                # passa prompt original + variáveis separados — Lambda faz a substituição
                execute_run(
                    sys_prompt,
                    prompt_id,
                    sel_label,
                    model_id,
                    model_name,
                    temperature,
                    max_tokens,
                    st.session_state.detail_session_id,
                    variables_used=var_values if variables else {},
                )

    # ── HISTÓRICO ─────────────────────────────────────────
    with tab_hist:
        run_type_filter = st.radio(
            "Tipo de execução",
            options=["playground", "production"],
            format_func=lambda x: (
                "Playground (testes)" if x == "playground" else "Produção (API)"
            ),
            horizontal=True,
            label_visibility="collapsed",
        )

        executions = fetch_history(prompt_id, run_type_filter)
        render_history(executions, sel_label)
