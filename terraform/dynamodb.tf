resource "aws_dynamodb_table" "prompts" {
  name         = "${local.project}-prompts"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "prompt_id"
  range_key    = "version"

  attribute {
    name = "prompt_id"
    type = "S"
  }

  attribute {
    name = "version"
    type = "S"
  }

  tags = { Project = local.project }
}

resource "aws_dynamodb_table" "history" {
  name         = "${local.project}-history"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "execution_id"

  attribute {
    name = "execution_id"
    type = "S"
  }

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  # índice para buscar histórico por sessão ordenado por data
  global_secondary_index {
    name            = "session-index"
    hash_key        = "session_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = { Project = local.project }
}
