output "instance_name" {
  description = "The name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.name
}

output "connection_name" {
  description = "The connection name of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.connection_name
}

output "private_ip_address" {
  description = "The private IP address of the Cloud SQL instance"
  value       = google_sql_database_instance.postgres.private_ip_address
  sensitive   = true
}

output "database_url" {
  description = "The database connection URL"
  value       = "postgresql://${var.database_user}:${var.database_password}@${google_sql_database_instance.postgres.private_ip_address}:5432/${var.database_name}"
  sensitive   = true
}

output "database_name" {
  description = "The database name"
  value       = google_sql_database.database.name
}

output "database_user" {
  description = "The database user"
  value       = google_sql_user.user.name
}

output "read_replica_connection_name" {
  description = "The connection name of the read replica"
  value       = var.enable_read_replica ? google_sql_database_instance.read_replica[0].connection_name : null
}
