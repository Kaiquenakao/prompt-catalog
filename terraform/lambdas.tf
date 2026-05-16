module "list-models" {
  source     = "./modules/lambda"
  name       = "${local.project}-list-models"
  source_dir = "${path.root}/../lambdas/list-models"
  handler    = "handler.handler"
  memory     = 256
  timeout    = 30

  extra_policy_arns = [aws_iam_policy.bedrock_list.arn]

  env_vars = {
    REGION = "us-east-1"
  }
}

# proximas lambdas — mesmo padrão:
#
# module "render-prompt" {
#   source     = "./modules/lambda"
#   name       = "${local.project}-render-prompt"
#   source_dir = "${path.root}/../lambdas/render-prompt"
#   handler    = "handler.handler"
#   memory     = 256
#   timeout    = 30
#   extra_policy_arns = [
#     aws_iam_policy.bedrock_invoke.arn,
#     aws_iam_policy.dynamodb_rw.arn,
#   ]
# }
