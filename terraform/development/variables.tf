variable "region" {
  type        = string
  description = "The AWS region to deploy to"
  default     = "eu-west-1"
}

variable "aws_subnet_id" {
  type        = string
  description = "The public subnet ID for the Elastic Beanstalk environment"
}

variable "aws_vpc_id" {
  type        = string
  description = "The VPC ID to deploy the Elastic Beanstalk environment in"
}

variable "db_url" {
  type        = string
  description = "The connection URL for the forecast database"
  sensitive   = true
}

variable "sites_db_url" {
  type        = string
  description = "The connection URL for the PV sites database"
  sensitive   = true
}

variable "sentry_dsn" {
  type        = string
  description = "Sentry DSN for error tracking"
  sensitive   = true
}

variable "auth_domain" {
  type        = string
  description = "Auth0 domain"
}

variable "auth_dashboard_client_id" {
  type        = string
  description = "Auth0 client ID for the dashboard"
}

variable "data_platform_host" {
  type        = string
  description = "Hostname for the data platform API"
}

variable "internal_ui_version" {
  type        = string
  description = "Container image tag for the analysis dashboard"
}

variable "s3_nwp_read_policy_arn" {
  type        = string
  description = "IAM policy ARN for reading NWP S3 bucket"
}

variable "s3_sat_read_policy_arn" {
  type        = string
  description = "IAM policy ARN for reading satellite S3 bucket"
}

variable "forecasting_models_read_policy_arn" {
  type        = string
  description = "IAM policy ARN for reading forecasting models S3 bucket"
}
