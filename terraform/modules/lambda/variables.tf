variable "name" {
  type        = string
  description = "Nome da Lambda e dos recursos associados"
}

variable "handler" {
  type        = string
  default     = "handler.handler"
  description = "Arquivo e função de entrada — formato: arquivo.funcao"
}

variable "source_dir" {
  type        = string
  description = "Caminho local da pasta da Lambda (ex: ../lambdas/list-models)"
}

variable "memory" {
  type        = number
  default     = 256
  description = "Memória em MB"
}

variable "timeout" {
  type        = number
  default     = 30
  description = "Timeout em segundos"
}

variable "env_vars" {
  type        = map(string)
  default     = {}
  description = "Variáveis de ambiente da Lambda"
}

variable "extra_policy_arns" {
  type        = list(string)
  default     = []
  description = "ARNs de políticas IAM adicionais para anexar à role da Lambda"
}
