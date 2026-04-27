locals {
  environment = "development"
  domain      = "uk"
}

# 4.1 - OCF Analysis Dashboard
module "analysis_dashboard" {
  source             = "github.com/openclimatefix/ocf-infrastructure//terraform/modules/services/eb_app"
  domain             = local.domain
  aws-region         = var.region
  aws-environment    = local.environment
  aws-subnet_id      = var.aws_subnet_id
  aws-vpc_id         = var.aws_vpc_id
  container-command  = ["uv", "run", "streamlit", "run", "main.py", "--server.port=8501", "--browser.serverAddress=0.0.0.0", "--server.address=0.0.0.0", "--server.enableCORS=False"]
  container-env_vars = [
    { "name" : "DB_URL", "value" : var.db_url },
    { "name" : "SITES_DB_URL", "value" : var.sites_db_url },
    { "name" : "SHOW_PVNET_GSP_SUM", "value" : "true" },
    { "name" : "ORIGINS", "value" : "*" },
    { "name" : "SENTRY_DSN", "value" : var.sentry_dsn },
    { "name" : "AUTH0_DOMAIN", "value" : var.auth_domain },
    { "name" : "AUTH0_CLIENT_ID", "value" : var.auth_dashboard_client_id },
    { "name" : "REGION", "value" : local.domain },
    { "name" : "ENVIRONMENT", "value" : local.environment },
    { "name" : "DATA_PLATFORM_HOST", "value" : var.data_platform_host },
  ]
  container-name = "analysis-dashboard"
  container-tag  = var.internal_ui_version
  container-registry = "ghcr.io/openclimatefix"
  container-port-mappings = [
    { "host" : "80", "container" : "8501" },
  ]
  eb-app_name      = "internal-ui"
  eb-instance_type = "t3.medium"
  s3_bucket = [
    { bucket_read_policy_arn = var.s3_nwp_read_policy_arn },
    { bucket_read_policy_arn = var.s3_sat_read_policy_arn },
    { bucket_read_policy_arn = var.forecasting_models_read_policy_arn },
  ]
}
