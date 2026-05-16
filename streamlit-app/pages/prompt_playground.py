import streamlit as st
import re
import time

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
    /* tooltip menor com quebras de linha */
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


# ── session state ──────────────────────────────────────────
if "tags" not in st.session_state:
    st.session_state.tags = []
if "output" not in st.session_state:
    st.session_state.output = None
if "output_meta" not in st.session_state:
    st.session_state.output_meta = None


# ── MODAL DE VARIÁVEIS ────────────────────────────────────
@st.dialog("Variáveis do prompt")
def variables_modal(variables, system_prompt, model, temperature, max_tokens):
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#94a3b8; margin:0 0 20px;">
        Preencha os valores que serão substituídos no prompt antes da execução.</p>""",
        unsafe_allow_html=True,
    )
    filled = {}
    for var in variables:
        filled[var] = st.text_input(
            var.replace("_", " ").capitalize(),
            placeholder=f"ex: valor real para {var}",
            key=f"modal_{var}",
            help=(
                f"Este valor substituirá {{{{{var}}}}} no prompt antes de enviar ao modelo. "
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

            with st.spinner("Executando..."):
                # TODO: api_client.render_prompt(prompt_name, final_prompt, model, temperature, max_tokens)
                time.sleep(1.5)

            st.session_state.output = (
                "Resultado aparecerá aqui após integração com a Lambda render-prompt."
            )
            st.session_state.output_meta = (
                f"{model}  ·  temp {temperature:.2f}  ·  {max_tokens} tokens"
            )
            st.rerun()


# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """<p style="font-family:'Space Grotesk',sans-serif; font-size:11px; color:#7c3aed;
        letter-spacing:0.15em; text-transform:uppercase; margin:8px 0 16px; font-weight:600;">
        Parâmetros</p>""",
        unsafe_allow_html=True,
    )
    model = st.selectbox(
        "Modelo",
        options=["claude-sonnet-4-5", "claude-opus-4-5", "claude-haiku-4-5"],
        help=(
            "Escolha o modelo conforme a complexidade da tarefa.\n\n"
            "• Sonnet — melhor custo-benefício para a maioria dos casos\n"
            "• Opus — máxima capacidade de raciocínio, ideal para tarefas complexas\n"
            "• Haiku — mais rápido e barato, ideal para respostas curtas e alto volume"
        ),
    )
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
            <span style="font-size:12px; color:#94a3b8;">Max tokens</span>
            <span style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#a78bfa;">{max_tokens}</span>
        </div></div>""",
        unsafe_allow_html=True,
    )

# ── HEADER ────────────────────────────────────────────────
st.markdown(
    """<div style="border-bottom:1px solid rgba(255,255,255,0.07);
    margin:-4rem -4rem 2rem -4rem; padding:16px 3rem; display:flex; align-items:center; gap:12px;
    background:rgba(255,255,255,0.02);">
    <span style="font-family:'Space Grotesk',sans-serif; font-size:20px; font-weight:600; color:#f1f5f9;">
        Prompt Playground</span>
    <span style="font-family:'JetBrains Mono',monospace; font-size:10px; color:#7c3aed;
        background:rgba(124,58,237,0.12); padding:3px 10px; border-radius:20px;
    <span style="font-family:'Space Grotesk',sans-serif; font-size:13px; color:#4b5563;">
        Escreva, teste e faça deploy dos seus prompts</span></div>""",
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
            placeholder="ex: suporte, reclamacao, producao, v2  —  clique em + para adicionar",
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
    st.markdown(
        f"""<div style="background:rgba(124,58,237,0.08); border:1px solid rgba(124,58,237,0.2);
        border-radius:10px; padding:10px 16px; margin-bottom:16px;
        font-family:'JetBrains Mono',monospace; font-size:13px; color:#a78bfa;">{model}</div>""",
        unsafe_allow_html=True,
    )
    temperature = st.slider(
        "temperatura_slider",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.01,
        label_visibility="collapsed",
        help=(
            "Controla o grau de aleatoriedade na resposta do modelo.\n\n"
            "• 0.0 – 0.3 (preciso): extração de dados, classificação, consistência crítica\n"
            "• 0.4 – 0.6 (equilibrado): e-mails, resumos, uso geral\n"
            "• 0.7 – 1.0 (criativo): geração de conteúdo, brainstorming, copy"
        ),
    )
    st.markdown(temp_bar_html(temperature), unsafe_allow_html=True)
    st.markdown("<div style='height:12px'/>", unsafe_allow_html=True)

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
        letter-spacing:0.15em; text-transform:uppercase; margin:0 0 12px; font-weight:600;">
        Output</p>""",
        unsafe_allow_html=True,
    )

    if st.session_state.output:
        st.markdown(
            f"""<div style="background:rgba(34,197,94,0.05); border:1px solid rgba(34,197,94,0.2);
            border-radius:12px; padding:20px 22px; font-family:'JetBrains Mono',monospace;
            font-size:13px; color:#e2e8f0; line-height:1.8;">
            <span style="font-size:10px; color:#22c55e; letter-spacing:0.1em;
                text-transform:uppercase; font-family:'Space Grotesk',sans-serif;">
                200 OK  ·  {st.session_state.output_meta}
            </span><br><br>{st.session_state.output}</div>""",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            """<div style="border:1px dashed rgba(255,255,255,0.08); border-radius:12px;
            padding:32px 24px; min-height:200px; font-family:'JetBrains Mono',monospace;
            font-size:13px; color:#4b5563; line-height:1.8;">
            Nenhuma execução ainda. Preencha o system prompt e clique em Run.</div>""",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:10px'/>", unsafe_allow_html=True)
    st.button("Deploy", type="secondary", use_container_width=True, disabled=True)

    if history_clicked:
        st.info("Modal de historico — em breve")

# ── LÓGICA DE RUN ─────────────────────────────────────────
variables = extract_variables(system_prompt)

if run_clicked:
    if not system_prompt.strip():
        st.warning("Preencha o system prompt antes de executar.")
    elif variables:
        variables_modal(variables, system_prompt, model, temperature, max_tokens)
    else:
        with st.spinner("Executando..."):
            # TODO: api_client.render_prompt(prompt_name, system_prompt, model, temperature, max_tokens)
            time.sleep(1.5)
        st.session_state.output = (
            "Resultado aparecerá aqui após integração com a Lambda render-prompt."
        )
        st.session_state.output_meta = (
            f"{model}  ·  temp {temperature:.2f}  ·  {max_tokens} tokens"
        )
        st.rerun()
