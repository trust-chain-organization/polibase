output "cloud_run_service_account_email" {
  description = "The email of the Cloud Run service account"
  value       = google_service_account.cloud_run.email
}

output "cloud_run_service_account_name" {
  description = "The name of the Cloud Run service account"
  value       = google_service_account.cloud_run.name
}

output "cloud_sql_proxy_service_account_email" {
  description = "The email of the Cloud SQL Proxy service account"
  value       = google_service_account.cloud_sql_proxy.email
}

output "google_api_key_secret_id" {
  description = "The ID of the Google API Key secret"
  value       = google_secret_manager_secret.google_api_key.secret_id
}

output "google_api_key_secret_name" {
  description = "The full name of the Google API Key secret"
  value       = google_secret_manager_secret.google_api_key.name
}

output "database_password_secret_id" {
  description = "The ID of the database password secret"
  value       = google_secret_manager_secret.database_password.secret_id
}

output "database_password_secret_name" {
  description = "The full name of the database password secret"
  value       = google_secret_manager_secret.database_password.name
}

output "sentry_dsn_secret_id" {
  description = "The ID of the Sentry DSN secret"
  value       = var.sentry_dsn != "" ? google_secret_manager_secret.sentry_dsn[0].secret_id : ""
}

output "sentry_dsn_secret_name" {
  description = "The full name of the Sentry DSN secret"
  value       = var.sentry_dsn != "" ? google_secret_manager_secret.sentry_dsn[0].name : ""
}
