# Random suffix for unique instance name
resource "random_id" "db_name_suffix" {
  byte_length = 4
}

# Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres" {
  name             = "polibase-db-${var.environment}-${random_id.db_name_suffix.hex}"
  database_version = var.database_version
  region           = var.region
  project          = var.project_id

  # Instance cannot be deleted if this is true
  deletion_protection = var.environment == "production" ? true : false

  settings {
    tier              = var.database_tier
    availability_type = var.enable_high_availability ? "REGIONAL" : "ZONAL"
    disk_type         = "PD_SSD"
    disk_size         = var.disk_size
    disk_autoresize   = true

    # Backup configuration
    backup_configuration {
      enabled                        = var.enable_backup
      start_time                     = "03:00" # 3 AM JST
      point_in_time_recovery_enabled = var.enable_backup
      transaction_log_retention_days = var.backup_retention_days

      backup_retention_settings {
        retained_backups = var.backup_retention_days
        retention_unit   = "COUNT"
      }
    }

    # Maintenance window
    maintenance_window {
      day          = 7 # Sunday
      hour         = 4 # 4 AM JST
      update_track = "stable"
    }

    # IP configuration - Private IP only
    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
      require_ssl     = true
    }

    # Insights configuration for monitoring
    insights_config {
      query_insights_enabled  = true
      query_plans_per_minute  = 5
      query_string_length     = 1024
      record_application_tags = true
    }

    # Database flags
    database_flags {
      name  = "max_connections"
      value = "100"
    }

    database_flags {
      name  = "shared_buffers"
      value = var.database_tier == "db-f1-micro" ? "32768" : "262144" # 32MB for micro, 256MB for others
    }
  }

  depends_on = [var.private_vpc_connection]
}

# Database
resource "google_sql_database" "database" {
  name     = var.database_name
  instance = google_sql_database_instance.postgres.name
  project  = var.project_id
}

# Database User
resource "google_sql_user" "user" {
  name     = var.database_user
  instance = google_sql_database_instance.postgres.name
  password = var.database_password
  project  = var.project_id
}

# Optional: Read Replica for reporting (only for production)
resource "google_sql_database_instance" "read_replica" {
  count = var.enable_read_replica ? 1 : 0

  name                 = "polibase-db-replica-${var.environment}-${random_id.db_name_suffix.hex}"
  database_version     = var.database_version
  master_instance_name = google_sql_database_instance.postgres.name
  region               = var.region
  project              = var.project_id

  replica_configuration {
    failover_target = false
  }

  settings {
    tier              = var.database_tier
    availability_type = "ZONAL"
    disk_type         = "PD_SSD"
    disk_autoresize   = true

    ip_configuration {
      ipv4_enabled    = false
      private_network = var.network_id
      require_ssl     = true
    }
  }

  depends_on = [google_sql_database_instance.postgres]
}
