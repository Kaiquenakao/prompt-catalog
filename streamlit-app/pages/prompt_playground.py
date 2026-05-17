import re
import time
import uuid

import httpx
import streamlit as st

st.set_page_config(layout="wide", page_title="Prompt Playground")

st.markdown(
    """
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 13px !important;
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        padding: 10px 14px !important;
        caret-color: #a78bfa !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: rgba(139,92,246,0.65) !important;
        box-shadow: 0 0 0 3px rgba(139,92,246,0.14) !important;
    }
    .stTextInput label, .stTextArea label, .stSelectbox label {
        color: #94a3b8 !important; font-size: 11px !important;
        letter-spacing: 0.12em !important; text-transform: uppercase !important;
        font-family: 'Space Grotesk', sans-serif !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #7c3aed, #4f46e5) !important;
        border: none !important; border-radius: 8px !important; color: white !important;
        font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important;
        font-size: 12px !important; letter-spacing: 0.08em !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(124,58,237,0.5) !important;
    }
    .stButton > button[kind="secondary"] {
        background: rgba(255,255,255,0.05) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px !important; color: #94a3b8 !important;
        font-family: 'Space Grotesk', sans-serif !important; font-size: 12px !important;
    }
    .stButton > button[kind="secondary"]:hover {
        background: rgba(255,255,255,0.08) !important; color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,0.07) !important; }
    hr { border-color: rgba(255,255,255,0.08) !important; }
    .stSelectbox [data-baseweb="select"] > div {
        border-radius: 10px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
    }
    div[data-testid="stTooltipContent"] > div,
    div[role="tooltip"],
    [data-baseweb="tooltip"] [data-testid="stMarkdownContainer"] p,
    div[class*="tooltip"] {
        font-size: 11px !important;
        line-height: 1.6 !important;
        font-family: 'Space Grotesk', sans-serif !important;
        white-space: pre-line !important;
    }
    #MainMenu, footer, header { visibility: hidden; }
    ::-webkit-scrollbar { width: 4px; }
    ::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.4); border-radius: 2px; }
</style>
""",
    unsafe_allow_html=True,
)


# ── API client ────────────────────────────────────────────
def _headers() -> dict:
    return {
        "x-api-key": st.secrets["API_KEY"],
        "Content-Type": "application/json",
    }


def _base() -> str:
    return st.secrets["API_GATEWAY_URL"]


def fetch_models() -> dict:
    try:
        resp = httpx.get(f"{_base()}/models", headers=_headers(), timeout=10.0)
        resp.raise_for_status()
        return {m["name"]: m["id"] for m in resp.json().get("models", [])}
    except Exception:
        return {
            "Claude Haiku 4.5": "anthropic.claude-haiku-4-5-20251001-v1:0",
            "Claude Sonnet 4.5": "anthropic.claude-sonnet-4-5-20250929-v1:0",
            "Claude Sonnet 4.6": "anthropic.claude-sonnet-4-6",
        }


def run_prompt(payload: dict) -> dict:
    resp = httpx.post(
        f"{_base()}/run",
        headers=_headers(),
        json=payload,
        timeout=310.0,
    )
    resp.raise_for_status()
    return resp.json()


def get_execution(execution_id: str) -> dict:
    resp = httpx.get(
        f"{_base()}/executions/{execution_id}",
        headers=_headers(),
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()


def get_history(session_id: str) -> list:
    resp = httpx.get(
        f"{_base()}/executions",
        headers=_headers(),
        params={"session_id": session_id},
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json().get("executions", [])


def check_prompt_versions(prompt_name: str) -> dict:
    try:
        resp = httpx.get(
            f"{_base()}/prompts/{prompt_name}",
            headers=_headers(),
            timeout=10.0,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"versions": [], "count": 0}


def deploy_prompt(payload: dict) -> dict:
    resp = httpx.post(
        f"{_base()}/prompts",
        headers=_headers(),
        json=payload,
        timeout=15.0,
    )
    resp.raise_for_status()
    return resp.json()


# ── helpers ───────────────────────────────────────────────
def temp_bar_html(value: float) -> str:
    pct = value * 100
    if value < 0.33:
        color, label = "#38bdf8", "preciso"
    elif value < 0.66:
        color, label = "#a78bfa", "equilibrado"
    else:
        color, label = "#f97316", "criativo"
    return f"""
    <div style="margin-bottom:4px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <span style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#94a3b8;
                letter-spacing:0.12em; text-transform:uppercase;">Temperatura</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:13px; color:{color}; font-weight:500;">
                {value:.2f} <span style="font-size:10px; color:#6b7280;">— {label}</span>
            </span>
        </div>
        <div style="height:8px; background:rgba(255,255,255,0.07); border-radius:999px; overflow:hidden;">
            <div style="height:100%; width:{pct}%;
                background: linear-gradient(90deg, #38bdf8, #a78bfa, #f97316);
                border-radius:999px;"></div>
        </div>
        <div style="display:flex; justify-content:space-between; margin-top:4px;">
            <span style="font-family:'JetBrains Mono',monospace; font-size:9px; color:#4b5563;">0.0</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:9px; color:#4b5563;">0.5</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:9px; color:#4b5563;">1.0</span>
        </div>
    </div>
    """


def extract_variables(prompt: str) -> list:
    return list(dict.fromkeys(re.findall(r"\{\{(\w+)\}\}", prompt)))


def execute_run(
    final_prompt: str,
    prompt_name: str,
    model_id: str,
    model_name: str,
    temperature: float,
    max_tokens: int,
):
    """Chama POST /run e faz polling até status=done."""
    payload = {
        "prompt_name": prompt_name,
        "system_prompt": final_prompt,
        "model_id": model_id,
        "temperature": temperature,
        "max_tokens": int(max_tokens),
        "session_id": st.session_state.session_id,
    }

    with st.spinner("Enviando para o modelo..."):
        result = run_prompt(payload)

    # se já veio done na resposta direta (< 29s), usa direto
    if result.get("status") == "done":
        st.session_state.output = result.get("output", "")
        st.session_state.output_meta = (
            f"{model_name}  ·  temp {temperature:.2f}  ·  "
            f"{result.get('input_tokens', 0)} in / {result.get('output_tokens', 0)} out  ·  "
            f"{result.get('latency_ms', 0)}ms"
        )
        st.session_state["_scroll_to_output"] = True
        st.rerun()
        return

    # polling para chamadas longas
    execution_id = result.get("execution_id")
    if not execution_id:
        st.error("Erro: execution_id não retornado.")
        return

    progress = st.progress(0, text="Aguardando resposta do modelo...")
    for i in range(60):  # até 120s (60 x 2s)
        time.sleep(2)
        progress.progress(min(i * 2, 95), text=f"Processando... {(i + 1) * 2}s")
        try:
            data = get_execution(execution_id)
            if data.get("status") == "done":
                progress.empty()
                st.session_state.output = data.get("output", "")
                st.session_state.output_meta = (
                    f"{model_name}  ·  temp {temperature:.2f}  ·  "
                    f"{data.get('input_tokens', 0)} in / {data.get('output_tokens', 0)} out  ·  "
                    f"{data.get('latency_ms', 0)}ms"
                )
                st.session_state["_scroll_to_output"] = True
                st.rerun()
                return
            if data.get("status") == "error":
                progress.empty()
                st.error(f"Erro na execução: {data.get('output', 'desconhecido')}")
                return
        except Exception:
            pass

    progress.empty()
    st.error("Timeout: a execução excedeu 120s.")


# ── session state ──────────────────────────────────────────
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "tags" not in st.session_state:
    st.session_state.tags = []
if "output" not in st.session_state:
    st.session_state.output = None
if "output_meta" not in st.session_state:
    st.session_state.output_meta = None
if "model_options" not in st.session_state:
    with st.spinner("Carregando modelos..."):
        st.session_state.model_options = fetch_models()
if "deploy_success" not in st.session_state:
    st.session_state.deploy_success = None

# ── pré-preenche campos se vier dos detalhes ──────────────
edit = st.session_state.pop("playground_edit", None)
if edit:
    # só seta se ainda não foi inicializado — evita sobrescrever o que o usuário digitou
    if "pf_name" not in st.session_state:
        st.session_state["pf_name"] = edit.get("prompt_name", "")
    if "pf_prompt" not in st.session_state:
        st.session_state["pf_prompt"] = edit.get("system_prompt", "")
    if "pf_description" not in st.session_state:
        st.session_state["pf_description"] = edit.get("description", "")
    if "pf_temperature" not in st.session_state:
        st.session_state["pf_temperature"] = float(edit.get("temperature", 0.7))
    if "pf_max_tokens" not in st.session_state:
        st.session_state["pf_max_tokens"] = int(edit.get("max_tokens", 1024))
    if "_editing_from" not in st.session_state:
        st.session_state["_editing_from"] = edit.get("from_version", "")
        st.session_state["_prefill_name"] = edit.get("prompt_name", "")
    st.session_state.tags = edit.get("tags", [])


# ── MODAL: campos obrigatórios ────────────────────────────
@st.dialog("Campos obrigatórios não preenchidos")
def validation_modal(missing: list):
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#94a3b8; margin:0 0 16px;">
        Preencha os campos abaixo antes de executar o prompt.</p>""",
        unsafe_allow_html=True,
    )
    for field in missing:
        st.markdown(
            f"""<div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3);
            border-radius:8px; padding:10px 14px; margin-bottom:8px;
            font-family:'Space Grotesk',sans-serif; font-size:13px; color:#fca5a5;">
            {field}</div>""",
            unsafe_allow_html=True,
        )
    st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)
    if st.button("Fechar", type="secondary", use_container_width=True):
        st.rerun()


# ── MODAL: variáveis ──────────────────────────────────────
@st.dialog("Variáveis do prompt")
def variables_modal(
    variables, system_prompt, model_id, model_name, temperature, max_tokens
):
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#94a3b8; margin:0 0 20px;">
        Preencha os valores que serão substituídos no prompt antes da execução.</p>""",
        unsafe_allow_html=True,
    )
    filled = {}
    for var in variables:
        filled[var] = st.text_area(
            var.replace("_", " ").capitalize(),
            placeholder=f"ex: valor real para {var}",
            key=f"modal_{var}",
            height=80,
            help=(
                f"Este valor substituirá {{{{{var}}}}} no prompt antes de enviar ao modelo.\n"
                "Em produção, este campo virá preenchido automaticamente pela requisição da API."
            ),
        )

    st.markdown("<div style='height:4px'/>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1], gap="small")
    with c1:
        confirm = st.button("Executar", type="primary", use_container_width=True)
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True):
            st.rerun()

    if confirm:
        if any(v.strip() == "" for v in filled.values()):
            st.warning("Preencha todos os campos antes de executar.")
        else:
            final_prompt = system_prompt
            for var, val in filled.items():
                final_prompt = final_prompt.replace(f"{{{{{var}}}}}", val)
            execute_run(
                final_prompt,
                system_prompt,
                model_id,
                model_name,
                temperature,
                max_tokens,
            )


# ── MODAL: deploy ─────────────────────────────────────────
@st.dialog("Deploy para produção")
def deploy_modal(
    prompt_name,
    system_prompt,
    description,
    tags,
    model_id,
    model_name,
    temperature,
    max_tokens,
):
    # verifica versões existentes
    with st.spinner("Verificando versões existentes..."):
        data = check_prompt_versions(prompt_name)
        count = data.get("count", 0)
        next_v = f"v{count + 1}"
        is_new = count == 0

    if is_new:
        st.markdown(
            f"""<div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3);
            border-radius:10px; padding:14px 18px; margin-bottom:16px;">
            <span style="font-size:11px; color:#22c55e; font-family:'Space Grotesk',sans-serif;
                font-weight:600;">Novo prompt — será criado como {next_v}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"""<div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3);
            border-radius:10px; padding:14px 18px; margin-bottom:16px;">
            <span style="font-size:11px; color:#f59e0b; font-family:'Space Grotesk',sans-serif;
                font-weight:600;">Já existe {count} versão(ões) deste prompt.</span><br>
            <span style="font-size:12px; color:#94a3b8; font-family:'Space Grotesk',sans-serif;">
                Será criada a versão <strong style="color:#f1f5f9;">{next_v}</strong> em produção.
            </span>
            </div>""",
            unsafe_allow_html=True,
        )

    # resumo do que será salvo
    st.markdown(
        f"""
    <div style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px;">
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#475569; font-family:'Space Grotesk',sans-serif;">Nome</span>
            <span style="font-size:12px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;">{prompt_name}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#475569; font-family:'Space Grotesk',sans-serif;">Versão</span>
            <span style="font-size:12px; color:#a78bfa; font-family:'JetBrains Mono',monospace;">{next_v}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#475569; font-family:'Space Grotesk',sans-serif;">Modelo</span>
            <span style="font-size:12px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;">{model_name}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#475569; font-family:'Space Grotesk',sans-serif;">Temperatura</span>
            <span style="font-size:12px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;">{temperature:.2f}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#475569; font-family:'Space Grotesk',sans-serif;">Max tokens</span>
            <span style="font-size:12px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;">{max_tokens}</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#475569; font-family:'Space Grotesk',sans-serif;">Status</span>
            <span style="background:rgba(34,197,94,0.15); color:#22c55e; border:1px solid rgba(34,197,94,0.4);
                border-radius:4px; padding:2px 8px; font-size:10px; font-family:'JetBrains Mono',monospace;">
                prod · ativo</span>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.divider()

    is_active = st.toggle(
        "Desativar versões anteriores ao ativar esta",
        value=False,
        help=(
            "Desativado (padrão): todas as versões ativas continuam rodando em paralelo — "
            "ideal para testes A/B.\n\n"
            "Ativado: as versões anteriores são desativadas e apenas esta entra em uso."
        ),
    )

    st.markdown("<div style='height:4px'/>", unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1], gap="small")
    with c1:
        confirm = st.button(
            "Confirmar deploy", type="primary", use_container_width=True
        )
    with c2:
        if st.button("Cancelar", type="secondary", use_container_width=True):
            st.rerun()

    if confirm:
        with st.spinner("Publicando..."):
            try:
                result = deploy_prompt(
                    {
                        "prompt_name": prompt_name,
                        "system_prompt": system_prompt,
                        "description": description,
                        "tags": tags,
                        "model_id": model_id,
                        "temperature": temperature,
                        "max_tokens": int(max_tokens),
                        "session_id": st.session_state.session_id,
                        "is_active": not is_active,
                    }
                )
                version = result.get("version", next_v)
                st.session_state.deploy_success = f"{prompt_name} {version}"
                # limpa estado de edição
                for k in [
                    "_editing_from",
                    "_prefill_name",
                    "pf_name",
                    "pf_prompt",
                    "pf_description",
                ]:
                    st.session_state.pop(k, None)
                st.rerun()
            except Exception as e:
                st.error(f"Erro no deploy: {e}")


@st.dialog("Histórico da sessão", width="large")
def history_modal():
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#94a3b8; margin:0 0 16px;">
        Execuções desta sessão — visíveis apenas para você.</p>""",
        unsafe_allow_html=True,
    )
    try:
        executions = get_history(st.session_state.session_id)
    except Exception as e:
        st.error(f"Erro ao carregar histórico: {e}")
        return

    if not executions:
        st.info("Nenhuma execução nesta sessão ainda.")
        return

    def to_brasilia(utc_str: str) -> str:
        try:
            from datetime import datetime, timezone, timedelta

            dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            brt = dt.astimezone(timezone(timedelta(hours=-3)))
            return brt.strftime("%d/%m/%Y %H:%M:%S")
        except Exception:
            return utc_str[:19].replace("T", " ")

    total = len(executions)

    for idx, ex in enumerate(executions):
        num = total - idx  # mais recente = número maior
        status = ex.get("status", "-")
        model_short = ex.get("model_id", "-").split(".")[-1][:22]
        date_str = to_brasilia(ex.get("created_at", ""))
        in_tok = ex.get("input_tokens", 0)
        out_tok = ex.get("output_tokens", 0)
        latency = ex.get("latency_ms", 0)
        pname = ex.get("prompt_name") or ex.get("system_prompt", "")[:40]

        status_badge = (
            f'<span style="background:rgba(34,197,94,0.15); color:#22c55e; '
            f"border:1px solid rgba(34,197,94,0.4); border-radius:4px; "
            f"padding:2px 8px; font-size:10px; font-family:'JetBrains Mono',monospace;\">done</span>"
            if status == "done"
            else f'<span style="background:rgba(239,68,68,0.15); color:#ef4444; '
            f"border:1px solid rgba(239,68,68,0.4); border-radius:4px; "
            f"padding:2px 8px; font-size:10px; font-family:'JetBrains Mono',monospace;\">{status}</span>"
        )

        st.markdown(
            f"""
        <div style="display:grid; grid-template-columns:28px 2fr 2fr 1.5fr 1fr 1fr;
            align-items:center; gap:8px; padding:6px 0 2px;
            font-family:'Space Grotesk',sans-serif; font-size:12px; color:#94a3b8;">
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px;
                color:#4b5563; text-align:right;">#{num}</span>
            <span style="color:#e2e8f0; font-weight:500; white-space:nowrap;
                overflow:hidden; text-overflow:ellipsis;" title="{pname}">{pname}</span>
            <span style="color:#a78bfa; font-family:'JetBrains Mono',monospace;
                font-size:11px;">{model_short}</span>
            <span>{date_str}</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:11px;">
                {in_tok}↑ {out_tok}↓</span>
            {status_badge}
        </div>
        """,
            unsafe_allow_html=True,
        )

        with st.expander("ver detalhes", expanded=False):
            st.markdown(
                f"""
            <div style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:14px;">
                <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
                    border-radius:8px; padding:8px 14px; min-width:90px;">
                    <div style="font-size:9px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif;">Status</div>
                    <div style="margin-top:4px;">{status_badge}</div>
                </div>
                <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
                    border-radius:8px; padding:8px 14px; min-width:90px;">
                    <div style="font-size:9px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif;">Modelo</div>
                    <div style="font-size:11px; color:#a78bfa; font-family:'JetBrains Mono',monospace;
                        margin-top:4px;">{model_short}</div>
                </div>
                <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
                    border-radius:8px; padding:8px 14px; min-width:90px;">
                    <div style="font-size:9px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif;">Tokens</div>
                    <div style="font-size:11px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;
                        margin-top:4px;">{in_tok}↑ &nbsp;{out_tok}↓</div>
                </div>
                <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
                    border-radius:8px; padding:8px 14px; min-width:90px;">
                    <div style="font-size:9px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif;">Latência</div>
                    <div style="font-size:11px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;
                        margin-top:4px;">{latency}ms</div>
                </div>
                <div style="background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08);
                    border-radius:8px; padding:8px 14px; min-width:120px;">
                    <div style="font-size:9px; color:#475569; text-transform:uppercase;
                        letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif;">Horário (BRT)</div>
                    <div style="font-size:11px; color:#e2e8f0; font-family:'JetBrains Mono',monospace;
                        margin-top:4px;">{date_str}</div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """<p style="font-size:10px; color:#475569; text-transform:uppercase;
                letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:0 0 6px;">
                System prompt</p>""",
                unsafe_allow_html=True,
            )
            st.code(ex.get("system_prompt", ""), language=None)

            if ex.get("output"):
                st.markdown(
                    """<p style="font-size:10px; color:#475569; text-transform:uppercase;
                    letter-spacing:0.1em; font-family:'Space Grotesk',sans-serif; margin:8px 0 6px;">
                    Output</p>""",
                    unsafe_allow_html=True,
                )
                clean = "\n\n".join(
                    p.strip() for p in ex.get("output", "").split("\n\n") if p.strip()
                )
                with st.container(border=True):
                    st.markdown(clean)

        st.markdown(
            "<div style='border-bottom:1px solid rgba(255,255,255,0.06); margin:4px 0 8px;'/>",
            unsafe_allow_html=True,
        )


# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#7c3aed;
        letter-spacing:0.15em; text-transform:uppercase; margin:8px 0 16px; font-weight:600;">
        Parâmetros</p>""",
        unsafe_allow_html=True,
    )
    model_names = list(st.session_state.model_options.keys())
    st.divider()
    st.markdown(
        f"""<div style="background:rgba(124,58,237,0.08); border:1px solid rgba(124,58,237,0.2);
        border-radius:10px; padding:12px 14px;">
        <p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#7c3aed;
            letter-spacing:0.12em; text-transform:uppercase; margin:0 0 10px; font-weight:600;">
            Sessão</p>
        <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
            <span style="font-size:12px; color:#94a3b8;">Status</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#22c55e;">draft</span>
        </div>
        <div style="display:flex; justify-content:space-between;">
            <span style="font-size:12px; color:#94a3b8;">Session ID</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#475569;">
            {st.session_state.session_id[:8]}...</span>
        </div></div>""",
        unsafe_allow_html=True,
    )

# ── HEADER ────────────────────────────────────────────────
st.markdown(
    """<div style="border-bottom:1px solid rgba(255,255,255,0.07);
    margin:-4rem -4rem 2rem -4rem; padding:16px 3rem;
    display:flex; align-items:center; justify-content:space-between;
    background:rgba(255,255,255,0.02);">
    <div style="display:flex; align-items:center; gap:12px;">
        <span style="font-family:'Space Grotesk',sans-serif; font-size:20px; font-weight:600; color:#f1f5f9;">
            Prompt Playground</span>
        <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#7c3aed;
            background:rgba(124,58,237,0.12); padding:3px 10px; border-radius:20px;
            border:1px solid rgba(124,58,237,0.3);">beta</span>
        <span style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#4b5563;">
            Escreva, teste e faça deploy dos seus prompts</span>
    </div>
    <div style="display:flex; gap:6px;">
        <a href="/" target="_self" style="font-family:'Space Grotesk',sans-serif; font-size:12px;
            color:#64748b; padding:6px 14px; border-radius:8px; text-decoration:none;
            border:1px solid transparent;">Catálogo</a>
        <a href="/prompt_playground" target="_self" style="font-family:'Space Grotesk',sans-serif; font-size:12px; font-weight:600;
            color:#a78bfa; background:rgba(124,58,237,0.15); border:1px solid rgba(124,58,237,0.3);
            padding:6px 14px; border-radius:8px; text-decoration:none;">Playground</a>
        <a href="/historico" target="_self" style="font-family:'Space Grotesk',sans-serif; font-size:12px;
            color:#64748b; padding:6px 14px; border-radius:8px; text-decoration:none;
            border:1px solid transparent;">Histórico</a>
    </div>
    </div>""",
    unsafe_allow_html=True,
)

# ── BANNER DE SUCESSO ─────────────────────────────────────
if st.session_state.deploy_success:
    msg = st.session_state.deploy_success
    # scroll para o topo automaticamente
    st.markdown(
        "<script>window.parent.document.querySelector('section.main').scrollTo(0,0);</script>",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns([10, 1])
    with c1:
        st.markdown(
            f"""<div style="background:rgba(34,197,94,0.08); border:1px solid rgba(34,197,94,0.3);
            border-radius:10px; padding:12px 18px; display:flex; align-items:center; gap:12px;">
            <span style="font-size:13px; color:#22c55e; font-family:'Space Grotesk',sans-serif; font-weight:600;">
                Deploy realizado com sucesso
            </span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:12px;
                color:#a78bfa; background:rgba(124,58,237,0.12); padding:2px 10px;
                border-radius:999px; border:1px solid rgba(124,58,237,0.3);">{msg}</span>
            <a href="/" target="_self" style="font-size:12px; color:#a78bfa;
                font-family:'Space Grotesk',sans-serif; text-decoration:none;
                border-bottom:1px solid rgba(167,139,250,0.3);">ver no catálogo →</a>
            </div>""",
            unsafe_allow_html=True,
        )
    with c2:
        if st.button("✕", type="secondary", use_container_width=True):
            st.session_state.deploy_success = None
            st.rerun()

# ── BANNER DE EDIÇÃO ──────────────────────────────────────
if st.session_state.get("_editing_from"):
    pid = st.session_state.get("_prefill_name", "")
    fromv = st.session_state["_editing_from"]
    st.markdown(
        f"""<div style="background:rgba(245,158,11,0.08); border:1px solid rgba(245,158,11,0.3);
        border-radius:10px; padding:14px 20px; margin-bottom:16px;">
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:8px;">
            <span style="font-size:15px;">✏️</span>
            <span style="font-size:13px; color:#f59e0b; font-family:'Space Grotesk',sans-serif; font-weight:600;">
                Editando prompt existente</span>
        </div>
        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
            <span style="font-size:12px; color:#94a3b8; font-family:'Space Grotesk',sans-serif;">
                Ao fazer Deploy, será criada</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#f59e0b;
                background:rgba(245,158,11,0.12); padding:2px 10px; border-radius:4px;
                border:1px solid rgba(245,158,11,0.3);">{pid}</span>
            <span style="font-size:12px; color:#94a3b8; font-family:'Space Grotesk',sans-serif;">
                com o mesmo nome —</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#a78bfa;">
                versão anterior: {fromv}</span>
        </div>
        </div>""",
        unsafe_allow_html=True,
    )

# ── COLUNAS ───────────────────────────────────────────────
col_left, col_right = st.columns([2, 2], gap="large")

# ── ESQUERDA ──────────────────────────────────────────────
with col_left:
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#7c3aed;
        letter-spacing:0.15em; text-transform:uppercase; margin:0 0 12px; font-weight:600;">
        Definição</p>""",
        unsafe_allow_html=True,
    )

    prompt_name = st.text_input(
        "Nome",
        key="pf_name",
        placeholder="ex: suporte_reclamacao",
        help=(
            "Identificador único deste prompt no catálogo.\n\n"
            "• Use snake_case: palavras separadas por underline, sem espaços\n"
            "• Inclua o domínio: suporte_reclamacao, cobranca_segunda_via\n"
            "• Não inclua versão no nome — se já existir um prompt com este identificador, "
            "o sistema criará uma nova versão automaticamente\n\n"
            "Antes de criar, verifique na página do catálogo se já existe um prompt "
            "com nome similar que atenda à sua necessidade."
        ),
    )
    system_prompt = st.text_area(
        "System prompt",
        key="pf_prompt",
        placeholder=(
            "Você é um especialista em atendimento ao cliente da empresa Acme.\n"
            "Seu tom é empático, direto e sempre orientado à resolução.\n\n"
            "Use {{variavel}} para campos preenchidos em tempo de execução.\n"
            "Exemplo:\n"
            "  Cliente: {{customer_name}}\n"
            "  Problema relatado: {{issue_description}}\n"
            "  Última compra: {{last_order_id}}"
        ),
        height=240,
        help=(
            "Instrução principal enviada ao modelo antes de qualquer mensagem do usuário.\n\n"
            "• Defina papel e tom na primeira linha: 'Você é um especialista em X'\n"
            "• Seja específico sobre o que o modelo deve e não deve fazer\n"
            "• Use {{variavel}} para qualquer valor dinâmico\n"
            "• Inclua exemplos de input/output quando o formato importa"
        ),
    )
    description = st.text_area(
        "Quando usar este prompt",
        key="pf_description",
        placeholder=(
            "Descreva o caso de uso específico, o público-alvo e o que se espera como saída.\n"
            "Ex: Usado pelo time de suporte para responder reclamações de entrega. "
            "Espera-se uma resposta empática com proposta de resolução em até 2 parágrafos."
        ),
        height=150,
        help=(
            "Documentação interna para quem for usar ou manter este prompt.\n\n"
            "• Quando acionar este prompt (gatilho ou evento)\n"
            "• Quem é o usuário final da resposta gerada\n"
            "• O que se espera como saída (tom, tamanho, formato)\n"
            "• O que este prompt não cobre — limites de escopo"
        ),
    )

    # ── TAGS ──────────────────────────────────────────────
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#94a3b8;
        letter-spacing:0.12em; text-transform:uppercase; margin:12px 0 6px;">Tags</p>""",
        unsafe_allow_html=True,
    )
    tag_col, btn_col = st.columns([5, 1], gap="small")
    with tag_col:
        new_tag = st.text_input(
            "nova_tag",
            placeholder="ex: suporte, reclamacao, producao  —  clique em + para adicionar",
            label_visibility="collapsed",
            key="new_tag_input",
            help=(
                "Tags para categorizar e filtrar prompts no catálogo.\n\n"
                "• Domínio: suporte, cobranca, vendas, onboarding\n"
                "• Ambiente: producao, homologacao, experimental\n"
                "• Versão: v1, v2, latest\n"
                "• Tipo de saída: email, sms, chat, relatorio"
            ),
        )
    with btn_col:
        if st.button("+", type="secondary", use_container_width=True):
            clean = new_tag.strip().lower()
            if clean and clean not in st.session_state.tags:
                st.session_state.tags.append(clean)
            st.rerun()

    if st.session_state.tags:
        cols = st.columns(min(len(st.session_state.tags), 4))
        for i, tag in enumerate(st.session_state.tags):
            with cols[i % 4]:
                st.markdown(
                    f"""<div style="background:rgba(124,58,237,0.15);
                    border:1px solid rgba(124,58,237,0.4); border-radius:999px;
                    padding:4px 10px; text-align:center; font-family:'Space Grotesk',sans-serif;
                    font-size:12px; color:#a78bfa; margin-bottom:3px;
                    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{tag}</div>""",
                    unsafe_allow_html=True,
                )
                if st.button("x", key=f"rm_{tag}", use_container_width=True):
                    st.session_state.tags.remove(tag)
                    st.rerun()

# ── DIREITA ───────────────────────────────────────────────
with col_right:
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#7c3aed;
        letter-spacing:0.15em; text-transform:uppercase; margin:0 0 12px; font-weight:600;">
        Configuração</p>""",
        unsafe_allow_html=True,
    )

    model_name = st.selectbox(
        "Modelo",
        options=model_names,
        key="selected_model",
        help=(
            "Modelos carregados via API do Bedrock.\n\n"
            "• Haiku — mais rápido e barato, ideal para respostas curtas\n"
            "• Sonnet — melhor custo-benefício para a maioria dos casos\n"
            "• Opus — máxima capacidade de raciocínio, ideal para tarefas complexas"
        ),
    )
    model_id = st.session_state.model_options[model_name]

    st.markdown(
        f"""<div style="font-family:'JetBrains Mono',monospace; font-size:10px;
        color:#475569; margin-top:-8px; margin-bottom:12px; padding-left:2px;">
        {model_id}</div>""",
        unsafe_allow_html=True,
    )

    temperature = st.slider(
        "Temperatura",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.01,
        label_visibility="visible",
        help=(
            "Controla o grau de aleatoriedade na resposta do modelo.\n\n"
            "• 0.0 – 0.3 (preciso): extração de dados, classificação, consistência crítica\n"
            "• 0.4 – 0.6 (equilibrado): e-mails, resumos, uso geral\n"
            "• 0.7 – 1.0 (criativo): geração de conteúdo, brainstorming, copy"
        ),
    )
    st.markdown(temp_bar_html(temperature), unsafe_allow_html=True)

    max_tokens = st.number_input(
        "Max tokens",
        min_value=100,
        max_value=8096,
        value=1024,
        step=100,
        help=(
            "Limite máximo de tokens na resposta do modelo.\n"
            "100 tokens ≈ 75 palavras.\n\n"
            "• Respostas curtas (classificação, extração): 256–512\n"
            "• Respostas médias (e-mails, resumos): 512–1024\n"
            "• Respostas longas (relatórios, análises): 2048–4096"
        ),
    )

    st.markdown("<div style='height:8px'/>", unsafe_allow_html=True)
    btn1, btn2 = st.columns([1, 1], gap="small")
    with btn1:
        run_clicked = st.button("Run", type="primary", use_container_width=True)
    with btn2:
        history_clicked = st.button(
            "Historico", type="secondary", use_container_width=True
        )

    st.divider()

    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#7c3aed;
        letter-spacing:0.15em; text-transform:uppercase; margin:0 0 12px; font-weight:600;"
        id="output-section">
        Output</p>""",
        unsafe_allow_html=True,
    )

    if st.session_state.output:
        # scroll automático para o output após run
        if st.session_state.pop("_scroll_to_output", False):
            st.markdown(
                """<script>
                setTimeout(function(){
                    var main = window.parent.document.querySelector('.main .block-container');
                    if(main){ main.scrollTop = main.scrollHeight; }
                    else { window.parent.scrollTo(0, window.parent.document.body.scrollHeight); }
                }, 400);
                </script>""",
                unsafe_allow_html=True,
            )
        clean_output = "\n\n".join(
            p.strip() for p in st.session_state.output.split("\n\n") if p.strip()
        )
        st.markdown(
            f"""<div style="font-size:10px; color:#22c55e; letter-spacing:0.1em;
            text-transform:uppercase; font-family:'Space Grotesk',sans-serif;
            margin-bottom:6px;">200 OK &nbsp;·&nbsp; {st.session_state.output_meta}</div>
            <style>
            div[data-testid="stVerticalBlockBorderWrapper"] > div {{
                background: rgba(10, 22, 10, 0.85) !important;
            }}
            </style>""",
            unsafe_allow_html=True,
        )
        with st.container(border=True):
            st.markdown(clean_output)
    else:
        st.markdown(
            """<div style="border:1px dashed rgba(255,255,255,0.08); border-radius:12px;
            padding:32px 24px; min-height:200px; font-family:'JetBrains Mono',monospace;
            font-size:13px; color:#4b5563; line-height:1.8;">
            Nenhuma execução ainda. Preencha o system prompt e clique em Run.</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:10px'/>", unsafe_allow_html=True)
    deploy_clicked = st.button("Deploy", type="secondary", use_container_width=True)

# ── LÓGICA ────────────────────────────────────────────────
# lê valores dos campos com key
prompt_name = st.session_state.get("pf_name", "")
system_prompt = st.session_state.get("pf_prompt", "")
description = st.session_state.get("pf_description", "")
variables = extract_variables(system_prompt)

if history_clicked:
    history_modal()

if deploy_clicked:
    missing = []
    if not prompt_name.strip():
        missing.append("Nome")
    if not system_prompt.strip():
        missing.append("System prompt")
    if missing:
        validation_modal(missing)
    else:
        deploy_modal(
            prompt_name,
            system_prompt,
            description,
            st.session_state.tags,
            model_id,
            model_name,
            temperature,
            max_tokens,
        )

if run_clicked:
    missing = []
    if not prompt_name.strip():
        missing.append("Nome")
    if not system_prompt.strip():
        missing.append("System prompt")
    if not description.strip():
        missing.append("Quando usar este prompt")

    if missing:
        validation_modal(missing)
    elif variables:
        variables_modal(
            variables, system_prompt, model_id, model_name, temperature, max_tokens
        )
    else:
        execute_run(
            system_prompt, prompt_name, model_id, model_name, temperature, max_tokens
        )
