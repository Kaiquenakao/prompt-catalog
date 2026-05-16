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

# ──────────────────────────────────────────────────────────
# DEPLOYMENT + STAGE
# ──────────────────────────────────────────────────────────
resource "aws_api_gateway_deployment" "this" {
  rest_api_id = aws_api_gateway_rest_api.this.id

  # força novo deployment quando rotas mudam
  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.models.id,
      aws_api_gateway_method.get_models.id,
      aws_api_gateway_integration.get_models.id,
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
