# ──────────────────────────────────────────────────────────
# REST API
# ──────────────────────────────────────────────────────────
resource "aws_api_gateway_rest_api" "this" {
  name        = local.project
  description = "Prompt Catalog API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# ──────────────────────────────────────────────────────────
# API KEY + USAGE PLAN
# ──────────────────────────────────────────────────────────
resource "aws_api_gateway_api_key" "streamlit" {
  name    = "${local.project}-streamlit-key"
  enabled = true
}

resource "aws_api_gateway_usage_plan" "this" {
  name = "${local.project}-usage-plan"

  api_stages {
    api_id = aws_api_gateway_rest_api.this.id
    stage  = aws_api_gateway_stage.prod.stage_name
  }

  throttle_settings {
    rate_limit  = 100
    burst_limit = 50
  }
}

resource "aws_api_gateway_usage_plan_key" "this" {
  key_id        = aws_api_gateway_api_key.streamlit.id
  key_type      = "API_KEY"
  usage_plan_id = aws_api_gateway_usage_plan.this.id
}

# ──────────────────────────────────────────────────────────
# RECURSO /models
# ──────────────────────────────────────────────────────────
resource "aws_api_gateway_resource" "models" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "models"
}

# GET /models
resource "aws_api_gateway_method" "get_models" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.models.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "get_models" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.models.id
  http_method             = aws_api_gateway_method.get_models.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.list-models.invoke_arn
}

resource "aws_lambda_permission" "get_models" {
  statement_id  = "AllowAPIGatewayGetModels"
  action        = "lambda:InvokeFunction"
  function_name = module.list-models.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

resource "aws_api_gateway_method" "get_prompts" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.prompts.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "get_prompts" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.prompts.id
  http_method             = aws_api_gateway_method.get_prompts.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.get-prompts.invoke_arn
}

# ── POST /prompts — salva novo prompt/versão ──────────────
resource "aws_api_gateway_resource" "prompts" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "prompts"
}

resource "aws_api_gateway_method" "post_prompts" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.prompts.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "post_prompts" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.prompts.id
  http_method             = aws_api_gateway_method.post_prompts.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.save-prompt.invoke_arn
}

# ── GET /prompts/{prompt_id} — busca versões ──────────────
resource "aws_api_gateway_resource" "prompt_id" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_resource.prompts.id
  path_part   = "{prompt_id}"
}

resource "aws_api_gateway_method" "get_prompt" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.prompt_id.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "get_prompt" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.prompt_id.id
  http_method             = aws_api_gateway_method.get_prompt.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.get-prompts.invoke_arn
}

resource "aws_lambda_permission" "get_prompts" {
  statement_id  = "AllowAPIGatewayGetPrompts"
  action        = "lambda:InvokeFunction"
  function_name = module.get-prompts.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

resource "aws_lambda_permission" "save_prompt" {
  statement_id  = "AllowAPIGatewaySavePrompt"
  action        = "lambda:InvokeFunction"
  function_name = module.save-prompt.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

# ── POST /run ─────────────────────────────────────────────
resource "aws_api_gateway_resource" "run" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "run"
}

resource "aws_api_gateway_method" "post_run" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.run.id
  http_method      = "POST"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "post_run" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.run.id
  http_method             = aws_api_gateway_method.post_run.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.run-prompt.invoke_arn
}

resource "aws_lambda_permission" "post_run" {
  statement_id  = "AllowAPIGatewayPostRun"
  action        = "lambda:InvokeFunction"
  function_name = module.run-prompt.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

# ── GET /executions?session_id=xxx ────────────────────────
resource "aws_api_gateway_resource" "executions" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_rest_api.this.root_resource_id
  path_part   = "executions"
}

resource "aws_api_gateway_method" "get_executions" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.executions.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "get_executions" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.executions.id
  http_method             = aws_api_gateway_method.get_executions.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.get-execution.invoke_arn
}

# ── GET /executions/{execution_id} — polling ──────────────
resource "aws_api_gateway_resource" "execution_id" {
  rest_api_id = aws_api_gateway_rest_api.this.id
  parent_id   = aws_api_gateway_resource.executions.id
  path_part   = "{execution_id}"
}

resource "aws_api_gateway_method" "get_execution_id" {
  rest_api_id      = aws_api_gateway_rest_api.this.id
  resource_id      = aws_api_gateway_resource.execution_id.id
  http_method      = "GET"
  authorization    = "NONE"
  api_key_required = true
}

resource "aws_api_gateway_integration" "get_execution_id" {
  rest_api_id             = aws_api_gateway_rest_api.this.id
  resource_id             = aws_api_gateway_resource.execution_id.id
  http_method             = aws_api_gateway_method.get_execution_id.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = module.get-execution.invoke_arn
}

resource "aws_lambda_permission" "get_executions" {
  statement_id  = "AllowAPIGatewayGetExecutions"
  action        = "lambda:InvokeFunction"
  function_name = module.get-execution.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.this.execution_arn}/*/*"
}

# ──────────────────────────────────────────────────────────
# DEPLOYMENT + STAGE
# ──────────────────────────────────────────────────────────
resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id

  depends_on = [
    aws_api_gateway_integration.get_models,
    aws_api_gateway_integration.get_prompts,
    aws_api_gateway_integration.post_prompts,
    aws_api_gateway_integration.get_prompt,
    aws_api_gateway_integration.post_run,
    aws_api_gateway_integration.get_executions,
    aws_api_gateway_integration.get_execution_id,
  ]

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.models.id,
      aws_api_gateway_resource.prompts.id,
      aws_api_gateway_resource.prompt_id.id,
      aws_api_gateway_resource.run.id,
      aws_api_gateway_resource.executions.id,
      aws_api_gateway_resource.execution_id.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "prod" {
  rest_api_id   = aws_api_gateway_rest_api.this.id
  deployment_id = aws_api_gateway_deployment.this.id
  stage_name    = "prod"
}

# ──────────────────────────────────────────────────────────
# OUTPUTS
# ──────────────────────────────────────────────────────────
output "api_url" {
  value       = aws_api_gateway_stage.prod.invoke_url
  description = "API_GATEWAY_URL"
}

output "api_key" {
  value       = aws_api_gateway_api_key.streamlit.value
  sensitive   = true
  description = "API_KEY"
}
