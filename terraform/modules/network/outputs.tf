output "network_name" {
  description = "The name of the VPC network"
  value       = google_compute_network.vpc_network.name
}

output "network_id" {
  description = "The ID of the VPC network"
  value       = google_compute_network.vpc_network.id
}

output "network_self_link" {
  description = "The self link of the VPC network"
  value       = google_compute_network.vpc_network.self_link
}

output "subnet_name" {
  description = "The name of the subnet"
  value       = google_compute_subnetwork.subnet.name
}

output "subnet_id" {
  description = "The ID of the subnet"
  value       = google_compute_subnetwork.subnet.id
}

output "vpc_connector_name" {
  description = "The name of the VPC Access Connector"
  value       = google_vpc_access_connector.connector.name
}

output "vpc_connector_id" {
  description = "The ID of the VPC Access Connector"
  value       = google_vpc_access_connector.connector.id
}

output "private_vpc_connection" {
  description = "The private VPC connection for Cloud SQL"
  value       = google_service_networking_connection.private_vpc_connection.network
}
