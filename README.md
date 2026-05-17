# Prompt Catalog

> Plataforma interna para gerenciamento, versionamento e monitoramento de prompts LLM em produção.

---

## Visão de Negócio

Times que usam LLMs em produtos enfrentam um problema recorrente: **prompts vivem no código, em planilhas, ou na cabeça das pessoas**. Quando algo dá errado em produção — uma resposta estranha, uma mudança de comportamento — não há rastreabilidade, não há histórico, não há rollback.

O **Prompt Catalog** resolve isso tratando prompts como artefatos de software:

- **Versionados** — cada alteração gera uma nova versão, as anteriores ficam preservadas
- **Deployados** — um prompt só vai para produção após um deploy explícito
- **Monitorados** — cada execução é logada com modelo, tokens, latência, variáveis e output
- **Testáveis** — qualquer versão pode ser testada antes de ir para produção
- **Auditáveis** — o histórico separa execuções de playground (testes) de produção (API real)

### O problema que resolve

Sem uma ferramenta como essa, o ciclo de vida de um prompt é caótico:

```
Alguém escreve um prompt no código
        ↓
Abre PR, passa por review, faz merge
        ↓
Deploy da aplicação inteira para mudar 3 linhas de texto
        ↓
Algo dá errado em produção
        ↓
Ninguém sabe qual versão estava ativa, quem alterou, ou quando
```

Com o Prompt Catalog:

```
Escreve e testa no Playground (sem afetar produção)
        ↓
Faz Deploy — gera v1, v2, v3 com rastreabilidade completa
        ↓
Sistema externo chama POST /run com o nome do prompt
        ↓
Catálogo resolve a versão ativa, injeta variáveis, chama o modelo
        ↓
Qualquer problema → rollback em 1 clique ativando a versão anterior
```

### Governança e Qualidade

O Prompt Catalog implementa práticas de **AI Governance** que estão se tornando requisito em empresas que operam LLMs em produção:

**Rastreabilidade completa** — toda execução registra qual prompt foi usado, qual versão, quais variáveis foram passadas, qual modelo respondeu e qual foi o output. Isso é essencial para auditorias, investigações de incidentes e demonstração de conformidade.

**Separação entre teste e produção** — execuções de playground são marcadas como `playground`, chamadas reais como `production`. O histórico nunca mistura os dois contextos, evitando que testes contaminem métricas de produção.

**Controle de ativação** — uma versão só entra em produção quando explicitamente ativada. É possível ter múltiplas versões ativas simultaneamente para testes A/B controlados, ou desativar uma versão problemática sem afetar as demais.

**Desacoplamento entre prompt e código** — sistemas externos chamam o prompt pelo nome (`suporte_reclamacao`), não pela versão. Quando uma nova versão é ativada, todos os sistemas passam a usá-la automaticamente, sem nenhuma mudança de código.

**Controle de custo** — cada execução registra tokens de entrada e saída, modelo utilizado e latência. Isso permite calcular custo por prompt, identificar prompts ineficientes e tomar decisões baseadas em dados sobre qual modelo usar em cada caso.

### O que é possível fazer

| Capacidade | Descrição |
|------------|-----------|
| **Criar e versionar** | Escreva prompts com variáveis dinâmicas `{{nome}}`, faça deploy e o sistema cria v1, v2, v3 automaticamente |
| **Testar antes de ativar** | Qualquer versão pode ser testada com dados reais no playground antes de entrar em produção |
| **A/B Testing** | Mantenha múltiplas versões ativas simultaneamente e compare resultados no histórico |
| **Rollback imediato** | Desative uma versão problemática e reative a anterior com um toggle — sem deploys de código |
| **Integração via API** | Sistemas externos chamam `POST /run` com o nome do prompt e variáveis — o catálogo resolve o resto |
| **Auditoria de execuções** | Veja exatamente o que foi enviado ao modelo, quais variáveis foram usadas e qual foi o output |
| **Monitoramento por tipo** | Separe execuções de teste (playground) das execuções reais (produção) no histórico |
| **Documentação viva** | Cada prompt tem descrição de quando usar, tags de categorização e histórico de versões |

### Por que isso importa para cada time

**Time de Produto** — para de depender de engenharia para ajustar o tom, o contexto ou as instruções de um prompt. Faz o deploy diretamente, com segurança, sabendo que pode reverter se necessário.

**Time de Dados/IA** — compara modelos, temperaturas e variações de prompt com dados reais de produção. Identifica qual versão gera melhores resultados antes de ativar.

**Time de Engenharia** — integra via API uma única vez. Quando o prompt evolui, nenhum código muda. Foca em produto, não em gerenciar strings de texto.

**Time de QA** — testa prompts com variáveis reais antes do deploy. Compara o output da nova versão com o da versão atual e só aprova se estiver satisfeito.

**Compliance e Jurídico** — toda execução é rastreável, o que é um prompt estava ativo em determinada data e hora, e quem fez deploy de cada versão.

### Fluxo principal

```
Escrever prompt       →   Testar no Playground   →   Deploy para produção
(com variáveis {{x}})      (preencher variáveis)       (gera v1, v2, v3...)
                                                              ↓
                                                    Sistema externo chama
                                                    POST /run com o nome
                                                    do prompt e variáveis
```

---

## Estrutura de Arquivos

```
prompt-catalog/
│
├── streamlit-app/
│   ├── .streamlit/
│   │   ├── config.toml          # tema escuro
│   │   └── secrets.toml         # não versionar
│   ├── pages/
│   │   ├── 2_prompt_playground.py
│   │   ├── 3_detalhes.py
│   │   └── 4_historico.py
│   └── app.py                   # catálogo (porta principal)
│
├── lambdas/
│   ├── list-models/             # GET /models
│   │   ├── main.go
│   │   └── go.mod
│   ├── run-prompt/              # POST /run
│   │   ├── main.go
│   │   └── go.mod
│   ├── get-execution/           # GET /executions/*
│   │   ├── main.go
│   │   └── go.mod
│   ├── save-prompt/             # POST /prompts + PATCH /prompts/{id}/versions/{v}
│   │   ├── main.go
│   │   └── go.mod
│   └── get-prompts/             # GET /prompts + GET /prompts/{id}
│       ├── main.go
│       └── go.mod
│
├── terraform/
│   ├── modules/
│   │   └── lambda/
│   │       ├── main.tf          # IAM role, função, zip
│   │       └── variables.tf
│   ├── main.tf                  # provider, locals
│   ├── lambdas.tf               # módulos das lambdas
│   ├── api-gateway.tf           # rotas e integrações
│   ├── dynamodb.tf              # tabelas history e prompts
│   ├── iam.tf                   # políticas Bedrock e DynamoDB
│   └── outputs.tf
│
├── .gitignore
└── README.md
```

---

## Endpoints da API

| Método | Rota | Lambda | Descrição |
|--------|------|--------|-----------|
| `GET` | `/models` | list-models | Lista modelos Anthropic disponíveis no Bedrock |
| `GET` | `/prompts` | get-prompts | Lista todos os prompts (versão mais recente de cada) |
| `GET` | `/prompts/{name}` | get-prompts | Lista todas as versões de um prompt |
| `POST` | `/prompts` | save-prompt | Cria nova versão de um prompt |
| `PATCH` | `/prompts/{name}/versions/{v}` | save-prompt | Ativa ou desativa uma versão |
| `POST` | `/run` | run-prompt | Executa inferência no Bedrock e salva no histórico |
| `GET` | `/executions/{id}` | get-execution | Polling de uma execução específica |
| `GET` | `/executions?session_id=` | get-execution | Histórico de uma sessão (playground) |
| `GET` | `/executions?prompt_name=&run_type=` | get-execution | Histórico por prompt e tipo |
| `GET` | `/executions` | get-execution | Histórico global com filtros opcionais |

Todas as rotas exigem o header `x-api-key`.

---

## Tabelas DynamoDB

### `prompt-catalog-prompts`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `prompt_id` | String (PK) | Nome do prompt (ex: `suporte_reclamacao`) |
| `version` | String (SK) | Versão (ex: `v1`, `v2`) |
| `version_num` | Number | Número da versão para ordenação |
| `system_prompt` | String | Prompt original com `{{variáveis}}` |
| `description` | String | Documentação de quando usar |
| `tags` | List | Tags de categorização |
| `model_id` | String | ID do modelo Bedrock |
| `temperature` | Number | Temperatura usada |
| `max_tokens` | Number | Limite de tokens |
| `is_active` | Boolean | Versão ativa em produção |
| `status` | String | `prod` |
| `deployed_by` | String | Session ID de quem fez deploy |
| `created_at` | String | ISO 8601 UTC |

### `prompt-catalog-history`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `execution_id` | String (PK) | UUID da execução |
| `session_id` | String | UUID da sessão Streamlit |
| `prompt_name` | String | Nome do prompt |
| `prompt_version` | String | Versão executada |
| `run_type` | String | `playground` ou `production` |
| `system_prompt` | String | Prompt original com `{{variáveis}}` |
| `variables_used` | Map | Valores substituídos nas variáveis |
| `model_id` | String | Modelo usado |
| `temperature` | Number | Temperatura usada |
| `output` | String | Resposta do modelo |
| `input_tokens` | Number | Tokens de entrada |
| `output_tokens` | Number | Tokens de saída |
| `latency_ms` | Number | Tempo de inferência em ms |
| `status` | String | `pending`, `done` ou `error` |
| `created_at` | String | ISO 8601 UTC |
| `ttl` | Number | Unix timestamp — expira em 30 dias |

**GSIs:**
- `session-index` — `session_id` + `created_at` (histórico do playground)
- `prompt-index` — `prompt_name` + `created_at` (histórico por prompt)

---

## Pré-requisitos

- [Go 1.21+](https://go.dev/dl/)
- [Terraform 1.5+](https://developer.hashicorp.com/terraform/install)
- [AWS CLI configurado](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html) com permissões de Lambda, API Gateway, DynamoDB, IAM e Bedrock
- [Python 3.11+](https://www.python.org/downloads/) e pip
- Acesso ao Amazon Bedrock habilitado na região `us-east-1`

---

## Setup

### 1. Clonar o repositório

```bash
git clone https://github.com/seu-usuario/prompt-catalog.git
cd prompt-catalog
```

### 2. Configurar AWS CLI

Caso não tenha configurado ainda:

```bash
aws configure
```

Você precisará de:
- **AWS Access Key ID** — disponível no IAM > Users > Security credentials
- **AWS Secret Access Key** — gerado junto com o Access Key
- **Default region** — `us-east-1`
- **Output format** — `json`

Verifique se está funcionando:

```bash
aws sts get-caller-identity
```

### 3. Habilitar modelos no Bedrock

Acesse o [console do Bedrock](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) e solicite acesso aos modelos Anthropic Claude desejados.

### 4. Build das Lambdas

**Linux/macOS:**
```bash
for dir in lambdas/*/; do
  echo "Building $dir..."
  cd "$dir"
  go mod tidy
  GOOS=linux GOARCH=amd64 go build -o bootstrap main.go
  cd ../..
done
```

**Windows (PowerShell):**
```powershell
Get-ChildItem -Directory lambdas | ForEach-Object {
  Write-Host "Building $($_.Name)..."
  Set-Location $_.FullName
  go mod tidy
  $env:GOOS="linux"; $env:GOARCH="amd64"
  go build -o bootstrap main.go
  Set-Location ../..
}
```

### 5. Provisionar infraestrutura

```bash
cd terraform
terraform init
terraform apply
```

Anote os outputs:
```
api_url = "https://xxxx.execute-api.us-east-1.amazonaws.com/prod"
api_key = <sensitive>  # use: terraform output -raw api_key
```

### 6. Configurar o Streamlit

Crie o arquivo `streamlit-app/.streamlit/secrets.toml`:

```toml
API_GATEWAY_URL = "https://xxxx.execute-api.us-east-1.amazonaws.com/prod"
API_KEY         = "valor-retornado-pelo-terraform"
```

Para obter a API Key:
```bash
cd terraform
terraform output -raw api_key
```

### 7. Instalar dependências Python

```bash
cd streamlit-app
pip install streamlit httpx
```

### 8. Rodar o Streamlit

```bash
streamlit run app.py
```

Acesse em `http://localhost:8501`

---

## Deploy de atualizações

### Atualizar uma Lambda

```bash
cd lambdas/run-prompt
$env:GOOS="linux"; $env:GOARCH="amd64"  # PowerShell
go build -o bootstrap main.go

cd ../../terraform
terraform apply
```

### Forçar redeployment do API Gateway

Necessário quando adiciona novas rotas:

```bash
cd terraform
terraform apply -replace="aws_api_gateway_deployment.this"
```

### Adicionar nova Lambda

1. Crie a pasta em `lambdas/nova-lambda/` com `main.go` e `go.mod`
2. Adicione o módulo em `terraform/lambdas.tf`
3. Adicione a rota em `terraform/api-gateway.tf`
4. Adicione a política IAM necessária em `terraform/iam.tf`
5. Rode `terraform init && terraform apply`

---

## Variáveis nos prompts

Use `{{nome_da_variavel}}` no system prompt para criar campos dinâmicos:

```
Você é especialista de atendimento da {{empresa}}.
O cliente {{nome_cliente}} relatou: {{descricao_problema}}
```

- No **Playground**: um modal aparece para preencher os valores antes de executar
- Na **API de produção**: passe as variáveis no body do `POST /run`:

```json
{
  "prompt_name": "suporte_reclamacao",
  "model_id": "anthropic.claude-haiku-4-5-20251001-v1:0",
  "temperature": 0.7,
  "max_tokens": 1024,
  "variables_used": {
    "empresa": "Acme",
    "nome_cliente": "João Silva",
    "descricao_problema": "Produto com defeito"
  }
}
```

A Lambda busca automaticamente a versão ativa do prompt e substitui as variáveis antes de chamar o Bedrock.

---

## Segurança

- **API Key** obrigatória em todas as rotas — nunca exponha em código ou logs
- **`secrets.toml`** está no `.gitignore` — nunca versione
- **Bedrock**: Lambdas têm permissão mínima (`InvokeModel` e `ListFoundationModels`)
- **DynamoDB**: cada Lambda acessa apenas as tabelas que precisa
- **TTL**: logs expiram automaticamente em 30 dias

---

## .gitignore

```
# secrets
streamlit-app/.streamlit/secrets.toml

# binários Go
lambdas/**/bootstrap
lambdas/**/function.zip

# Terraform state
terraform/.terraform/
terraform/*.tfstate
terraform/*.tfstate.backup
terraform/.terraform.lock.hcl
```

---

## Troubleshooting

| Problema | Causa provável | Solução |
|----------|---------------|---------|
| `403 Forbidden` na API | API Key incorreta ou deployment desatualizado | Verifique `secrets.toml` e rode `terraform apply -replace="aws_api_gateway_deployment.this"` |
| `AccessDeniedException` DynamoDB | Política IAM sem a action necessária (ex: `Scan`) | Adicione a action em `iam.tf` e rode `terraform apply` |
| `ValidationException` Bedrock | Modelo requer inference profile | Lambda já adiciona prefixo `us.` automaticamente |
| Histórico não aparece | GSI criado após os registros | Registros antigos não são indexados retroativamente — execute novos testes |
| `Module not installed` no Terraform | Novo módulo adicionado | Rode `terraform init` antes do `apply` |

---