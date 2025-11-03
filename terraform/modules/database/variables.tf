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

variable "network_id" {
  description = "The VPC network ID"
  type        = string
}

variable "private_vpc_connection" {
  description = "The private VPC connection"
  type        = string
}

variable "database_version" {
  description = "PostgreSQL version"
  type        = string
  default     = "POSTGRES_15"
}

variable "database_tier" {
  description = "Cloud SQL instance tier"
  type        = string
  default     = "db-f1-micro"
}

variable "database_name" {
  description = "Database name"
  type        = string
  default     = "polibase_db"
}

variable "database_user" {
  description = "Database user"
  type        = string
  default     = "polibase_user"
}

variable "database_password" {
  description = "Database password"
  type        = string
  sensitive   = true
}

variable "disk_size" {
  description = "Disk size in GB"
  type        = number
  default     = 10
}

variable "enable_high_availability" {
  description = "Enable high availability (regional)"
  type        = bool
  default     = false
}

variable "enable_backup" {
  description = "Enable automated backups"
  type        = bool
  default     = true
}

variable "backup_retention_days" {
  description = "Number of days to retain backups"
  type        = number
  default     = 7
}

variable "enable_read_replica" {
  description = "Enable read replica for reporting"
  type        = bool
  default     = false
}
