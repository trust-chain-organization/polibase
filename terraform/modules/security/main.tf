# Service Account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "cloud-run-sa-${var.environment}"
  display_name = "Cloud Run Service Account (${var.environment})"
  project      = var.project_id
}

# Service Account for Cloud SQL Proxy
resource "google_service_account" "cloud_sql_proxy" {
  account_id   = "cloud-sql-proxy-${var.environment}"
  display_name = "Cloud SQL Proxy Service Account (${var.environment})"
  project      = var.project_id
}

# IAM Roles for Cloud Run Service Account
resource "google_project_iam_member" "cloud_run_roles" {
  for_each = toset([
    "roles/cloudsql.client",              # Cloud SQL Client
    "roles/secretmanager.secretAccessor", # Secret Manager Secret Accessor
    "roles/storage.objectAdmin",          # Storage Object Admin
    "roles/aiplatform.user",              # Vertex AI User
    "roles/logging.logWriter",            # Cloud Logging Writer
    "roles/monitoring.metricWriter",      # Cloud Monitoring Metric Writer
    "roles/cloudtrace.agent",             # Cloud Trace Agent
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# IAM Roles for Cloud SQL Proxy Service Account
resource "google_project_iam_member" "cloud_sql_proxy_roles" {
  for_each = toset([
    "roles/cloudsql.client", # Cloud SQL Client
  ])

  project = var.project_id
  role    = each.key
  member  = "serviceAccount:${google_service_account.cloud_sql_proxy.email}"
}

# Secret Manager - Google API Key
resource "google_secret_manager_secret" "google_api_key" {
  secret_id = "google-api-key-${var.environment}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "google_api_key" {
  secret      = google_secret_manager_secret.google_api_key.id
  secret_data = var.google_api_key
}

# Secret Manager - Database Password
resource "google_secret_manager_secret" "database_password" {
  secret_id = "database-password-${var.environment}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "database_password" {
  secret      = google_secret_manager_secret.database_password.id
  secret_data = var.database_password
}

# Secret Manager - Sentry DSN (optional)
resource "google_secret_manager_secret" "sentry_dsn" {
  count = var.sentry_dsn != "" ? 1 : 0

  secret_id = "sentry-dsn-${var.environment}"
  project   = var.project_id

  replication {
    auto {}
  }

  labels = {
    environment = var.environment
    managed_by  = "terraform"
  }
}

resource "google_secret_manager_secret_version" "sentry_dsn" {
  count = var.sentry_dsn != "" ? 1 : 0

  secret      = google_secret_manager_secret.sentry_dsn[0].id
  secret_data = var.sentry_dsn
}

# IAM Binding for Secret Access
resource "google_secret_manager_secret_iam_member" "google_api_key_access" {
  secret_id = google_secret_manager_secret.google_api_key.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "database_password_access" {
  secret_id = google_secret_manager_secret.database_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_secret_manager_secret_iam_member" "sentry_dsn_access" {
  count = var.sentry_dsn != "" ? 1 : 0

  secret_id = google_secret_manager_secret.sentry_dsn[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.cloud_run.email}"
}
