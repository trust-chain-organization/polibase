# GCS Bucket for Scraped Minutes
resource "google_storage_bucket" "minutes" {
  name          = "${var.project_id}-sagebase-minutes-${var.environment}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  # Prevent accidental deletion in production
  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 90 # Days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 365 # Days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "COLDLINE"
    }
  }

  labels = {
    environment = var.environment
    purpose     = "minutes"
    managed_by  = "terraform"
  }
}

# GCS Bucket for Database Backups
resource "google_storage_bucket" "backups" {
  name          = "${var.project_id}-sagebase-backups-${var.environment}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30 # Days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "NEARLINE"
    }
  }

  lifecycle_rule {
    condition {
      age = 1095 # 3 years
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    purpose     = "backups"
    managed_by  = "terraform"
  }
}

# GCS Bucket for Data Exports
resource "google_storage_bucket" "exports" {
  name          = "${var.project_id}-sagebase-exports-${var.environment}"
  location      = var.region
  project       = var.project_id
  storage_class = "STANDARD"

  force_destroy = var.environment != "production"

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 180 # Days
    }
    action {
      type = "Delete"
    }
  }

  labels = {
    environment = var.environment
    purpose     = "exports"
    managed_by  = "terraform"
  }

  # CORS configuration (if needed for web access)
  cors {
    origin          = ["*"]
    method          = ["GET", "HEAD"]
    response_header = ["Content-Type"]
    max_age_seconds = 3600
  }
}
