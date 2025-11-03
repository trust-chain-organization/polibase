# Cloud Run Service - Streamlit UI
resource "google_cloud_run_v2_service" "streamlit_ui" {
  name     = "streamlit-ui-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.environment == "production" ? 1 : 0
      max_instance_count = var.environment == "production" ? 10 : 3
    }

    vpc_access {
      connector = var.vpc_connector_name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Enable Cloud SQL connection via Unix socket
    cloud_sql_instances = [var.database_connection_name]

    containers {
      image = var.streamlit_image

      ports {
        container_port = 8501
      }

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = true
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Cloud SQL Proxy configuration
      env {
        name  = "USE_CLOUD_SQL_PROXY"
        value = "true"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = var.database_connection_name
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.google_api_key_secret
            version = "latest"
          }
        }
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = var.minutes_bucket
      }

      env {
        name  = "GCS_PROJECT_ID"
        value = var.project_id
      }

      env {
        name = "SENTRY_DSN"
        value_source {
          secret_key_ref {
            secret  = var.sentry_dsn_secret
            version = "latest"
          }
        }
      }

      env {
        name  = "LLM_MODEL"
        value = "gemini-2.0-flash"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Cloud Run Service - Monitoring Dashboard
resource "google_cloud_run_v2_service" "monitoring_dashboard" {
  name     = "monitoring-dashboard-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = var.environment == "production" ? 1 : 0
      max_instance_count = var.environment == "production" ? 5 : 2
    }

    vpc_access {
      connector = var.vpc_connector_name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Enable Cloud SQL connection via Unix socket
    cloud_sql_instances = [var.database_connection_name]

    containers {
      image = var.monitoring_image

      ports {
        container_port = 8502
      }

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
        cpu_idle = true
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Cloud SQL Proxy configuration
      env {
        name  = "USE_CLOUD_SQL_PROXY"
        value = "true"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = var.database_connection_name
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Cloud Run Service - Scraper Worker
resource "google_cloud_run_v2_service" "scraper_worker" {
  name     = "scraper-worker-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    vpc_access {
      connector = var.vpc_connector_name
      egress    = "ALL_TRAFFIC"
    }

    # Enable Cloud SQL connection via Unix socket
    cloud_sql_instances = [var.database_connection_name]

    timeout = "3600s" # 1 hour timeout for long-running scraping jobs

    containers {
      image = var.scraper_image

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
        cpu_idle = false
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Cloud SQL Proxy configuration
      env {
        name  = "USE_CLOUD_SQL_PROXY"
        value = "true"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = var.database_connection_name
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.google_api_key_secret
            version = "latest"
          }
        }
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = var.minutes_bucket
      }

      env {
        name  = "GCS_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCS_UPLOAD_ENABLED"
        value = "true"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Cloud Run Service - Processor Worker
resource "google_cloud_run_v2_service" "processor_worker" {
  name     = "processor-worker-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = 0
      max_instance_count = 10
    }

    vpc_access {
      connector = var.vpc_connector_name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Enable Cloud SQL connection via Unix socket
    cloud_sql_instances = [var.database_connection_name]

    timeout = "3600s" # 1 hour timeout for LLM processing

    containers {
      image = var.processor_image

      resources {
        limits = {
          cpu    = "2"
          memory = "4Gi"
        }
        cpu_idle = false
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Cloud SQL Proxy configuration
      env {
        name  = "USE_CLOUD_SQL_PROXY"
        value = "true"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = var.database_connection_name
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.google_api_key_secret
            version = "latest"
          }
        }
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = var.minutes_bucket
      }

      env {
        name  = "GCS_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "LLM_MODEL"
        value = "gemini-2.0-flash"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Cloud Run Service - Matcher Worker
resource "google_cloud_run_v2_service" "matcher_worker" {
  name     = "matcher-worker-${var.environment}"
  location = var.region
  project  = var.project_id

  template {
    service_account = var.service_account_email

    scaling {
      min_instance_count = 0
      max_instance_count = 5
    }

    vpc_access {
      connector = var.vpc_connector_name
      egress    = "PRIVATE_RANGES_ONLY"
    }

    # Enable Cloud SQL connection via Unix socket
    cloud_sql_instances = [var.database_connection_name]

    timeout = "1800s" # 30 minutes timeout

    containers {
      image = var.matcher_image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
        cpu_idle = false
      }

      env {
        name  = "ENVIRONMENT"
        value = var.environment
      }

      # Cloud SQL Proxy configuration
      env {
        name  = "USE_CLOUD_SQL_PROXY"
        value = "true"
      }

      env {
        name  = "CLOUD_SQL_CONNECTION_NAME"
        value = var.database_connection_name
      }

      env {
        name  = "DATABASE_URL"
        value = var.database_url
      }

      env {
        name = "GOOGLE_API_KEY"
        value_source {
          secret_key_ref {
            secret  = var.google_api_key_secret
            version = "latest"
          }
        }
      }

      env {
        name  = "LLM_MODEL"
        value = "gemini-2.0-flash"
      }
    }
  }

  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# IAM Policy for Public Access (UI services only)
resource "google_cloud_run_service_iam_member" "streamlit_public" {
  count = var.allow_public_access ? 1 : 0

  location = google_cloud_run_v2_service.streamlit_ui.location
  service  = google_cloud_run_v2_service.streamlit_ui.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

resource "google_cloud_run_service_iam_member" "monitoring_public" {
  count = var.allow_public_access ? 1 : 0

  location = google_cloud_run_v2_service.monitoring_dashboard.location
  service  = google_cloud_run_v2_service.monitoring_dashboard.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
