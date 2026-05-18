terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # descomente após criar o bucket de state remoto
  # backend "s3" {
  #   bucket         = "prompt-catalog-tfstate"
  #   key            = "terraform.tfstate"
  #   region         = "us-east-1"
  #   dynamodb_table = "prompt-catalog-tfstate-lock"
  # }
}

provider "aws" {
  region = "us-east-1"
}

locals {
  project = "prompt-catalog"
}
