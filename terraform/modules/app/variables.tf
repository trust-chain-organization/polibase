variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "vpc_connector_name" {
  description = "VPC connector name for Cloud Run"
  type        = string
}

variable "service_account_email" {
  description = "Service account email for Cloud Run services"
  type        = string
  default     = ""
}

variable "database_connection_name" {
  description = "Cloud SQL connection name"
  type        = string
}

variable "database_url" {
  description = "Database connection URL"
  type        = string
  sensitive   = true
}

variable "google_api_key_secret" {
  description = "Secret Manager secret ID for Google API key"
  type        = string
}

variable "sentry_dsn_secret" {
  description = "Secret Manager secret ID for Sentry DSN"
  type        = string
}

variable "minutes_bucket" {
  description = "GCS bucket name for minutes"
  type        = string
}

variable "backups_bucket" {
  description = "GCS bucket name for backups"
  type        = string
}

variable "exports_bucket" {
  description = "GCS bucket name for exports"
  type        = string
}

variable "streamlit_image" {
  description = "Docker image for Streamlit UI"
  type        = string
}

variable "monitoring_image" {
  description = "Docker image for monitoring dashboard"
  type        = string
}

variable "scraper_image" {
  description = "Docker image for scraper worker"
  type        = string
}

variable "processor_image" {
  description = "Docker image for processor worker"
  type        = string
}

variable "matcher_image" {
  description = "Docker image for matcher worker"
  type        = string
}

variable "allow_public_access" {
  description = "Allow public access to UI services"
  type        = bool
  default     = true
}
