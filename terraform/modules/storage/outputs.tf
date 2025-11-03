output "minutes_bucket_name" {
  description = "The name of the GCS bucket for scraped minutes"
  value       = google_storage_bucket.minutes.name
}

output "minutes_bucket_url" {
  description = "The URL of the GCS bucket for scraped minutes"
  value       = google_storage_bucket.minutes.url
}

output "backups_bucket_name" {
  description = "The name of the GCS bucket for backups"
  value       = google_storage_bucket.backups.name
}

output "backups_bucket_url" {
  description = "The URL of the GCS bucket for backups"
  value       = google_storage_bucket.backups.url
}

output "exports_bucket_name" {
  description = "The name of the GCS bucket for exports"
  value       = google_storage_bucket.exports.name
}

output "exports_bucket_url" {
  description = "The URL of the GCS bucket for exports"
  value       = google_storage_bucket.exports.url
}
