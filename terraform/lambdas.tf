module "list-models" {
  source     = "./modules/lambda"
  name       = "${local.project}-list-models"
  source_dir = "${path.root}/../lambdas/list-models"
  memory     = 256
  timeout    = 30

  extra_policy_arns = [aws_iam_policy.bedrock_list.arn]

  env_vars = {
    REGION = "us-east-1"
  }
}

module "run-prompt" {
  source     = "./modules/lambda"
  name       = "${local.project}-run-prompt"
  source_dir = "${path.root}/../lambdas/run-prompt"
  memory     = 512
  timeout    = 300

  extra_policy_arns = [
    aws_iam_policy.bedrock_invoke.arn,
    aws_iam_policy.dynamodb_history.arn,
  ]

  env_vars = {
    REGION        = "us-east-1"
    HISTORY_TABLE = aws_dynamodb_table.history.name
  }
}

module "get-execution" {
  source     = "./modules/lambda"
  name       = "${local.project}-get-execution"
  source_dir = "${path.root}/../lambdas/get-execution"
  memory     = 256
  timeout    = 30

  extra_policy_arns = [aws_iam_policy.dynamodb_history.arn]

  env_vars = {
    REGION        = "us-east-1"
    HISTORY_TABLE = aws_dynamodb_table.history.name
  }
}

module "save-prompt" {
  source     = "./modules/lambda"
  name       = "${local.project}-save-prompt"
  source_dir = "${path.root}/../lambdas/save-prompt"
  memory     = 256
  timeout    = 30

  extra_policy_arns = [aws_iam_policy.dynamodb_prompts.arn]

  env_vars = {
    REGION        = "us-east-1"
    PROMPTS_TABLE = aws_dynamodb_table.prompts.name
  }
}

module "get-prompts" {
  source     = "./modules/lambda"
  name       = "${local.project}-get-prompts"
  source_dir = "${path.root}/../lambdas/get-prompts"
  memory     = 256
  timeout    = 30

  extra_policy_arns = [aws_iam_policy.dynamodb_prompts.arn]

  env_vars = {
    REGION        = "us-east-1"
    PROMPTS_TABLE = aws_dynamodb_table.prompts.name
  }
}
