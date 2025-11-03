output "streamlit_url" {
  description = "The URL of the Streamlit UI service"
  value       = google_cloud_run_v2_service.streamlit_ui.uri
}

output "streamlit_service_name" {
  description = "The name of the Streamlit UI service"
  value       = google_cloud_run_v2_service.streamlit_ui.name
}

output "monitoring_url" {
  description = "The URL of the monitoring dashboard service"
  value       = google_cloud_run_v2_service.monitoring_dashboard.uri
}

output "monitoring_service_name" {
  description = "The name of the monitoring dashboard service"
  value       = google_cloud_run_v2_service.monitoring_dashboard.name
}

output "scraper_worker_url" {
  description = "The URL of the scraper worker service"
  value       = google_cloud_run_v2_service.scraper_worker.uri
}

output "scraper_worker_service_name" {
  description = "The name of the scraper worker service"
  value       = google_cloud_run_v2_service.scraper_worker.name
}

output "processor_worker_url" {
  description = "The URL of the processor worker service"
  value       = google_cloud_run_v2_service.processor_worker.uri
}

output "processor_worker_service_name" {
  description = "The name of the processor worker service"
  value       = google_cloud_run_v2_service.processor_worker.name
}

output "matcher_worker_url" {
  description = "The URL of the matcher worker service"
  value       = google_cloud_run_v2_service.matcher_worker.uri
}

output "matcher_worker_service_name" {
  description = "The name of the matcher worker service"
  value       = google_cloud_run_v2_service.matcher_worker.name
}
