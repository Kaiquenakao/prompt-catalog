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
        Resource = "*"
      }
    ]
  })
}

resource "aws_iam_policy" "dynamodb_history" {
  name = "${local.project}-dynamodb-history"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:UpdateItem",
        ]
        Resource = [
          aws_dynamodb_table.history.arn,
          "${aws_dynamodb_table.history.arn}/index/*",
        ]
      }
    ]
  })
}

# dynamodb_rw — adicionar quando criar o dynamodb.tf

