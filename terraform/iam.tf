resource "aws_iam_policy" "bedrock_list" {
  name = "${local.project}-bedrock-list"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["bedrock:ListFoundationModels"]
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_policy" "bedrock_invoke" {
  name = "${local.project}-bedrock-invoke"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["bedrock:InvokeModel"]
        Resource = "arn:aws:bedrock:us-east-1::foundation-model/*"
      }
    ]
  })
}

# dynamodb_rw — adicionar quando criar o dynamodb.tf

