# VPC Network
resource "google_compute_network" "vpc_network" {
  name                    = "${var.network_name}-${var.environment}"
  auto_create_subnetworks = false
  project                 = var.project_id
}

# Subnet for the region
resource "google_compute_subnetwork" "subnet" {
  name          = "${var.network_name}-subnet-${var.environment}"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc_network.id
  project       = var.project_id

  # Enable private Google access for GCS, etc.
  private_ip_google_access = true
}

# VPC Access Connector for Cloud Run
resource "google_vpc_access_connector" "connector" {
  name          = "vpc-connector-${var.environment}"
  region        = var.region
  network       = google_compute_network.vpc_network.name
  project       = var.project_id

  ip_cidr_range = var.vpc_connector_cidr

  # Min and max instances for the connector
  min_instances = 2
  max_instances = 3

  machine_type = "e2-micro"
}

# Reserve IP range for private service connection (Cloud SQL)
resource "google_compute_global_address" "private_ip_address" {
  name          = "private-ip-address-${var.environment}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = 16
  network       = google_compute_network.vpc_network.id
  project       = var.project_id
}

# Private VPC Connection for Cloud SQL
resource "google_service_networking_connection" "private_vpc_connection" {
  network                 = google_compute_network.vpc_network.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_ip_address.name]
}

# Firewall rule to allow internal traffic
resource "google_compute_firewall" "allow_internal" {
  name    = "allow-internal-${var.environment}"
  network = google_compute_network.vpc_network.name
  project = var.project_id

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
}

# Firewall rule to allow health checks from Google Cloud
resource "google_compute_firewall" "allow_health_checks" {
  name    = "allow-health-checks-${var.environment}"
  network = google_compute_network.vpc_network.name
  project = var.project_id

  allow {
    protocol = "tcp"
  }

  # Google Cloud health check IP ranges
  source_ranges = [
    "35.191.0.0/16",
    "130.211.0.0/22"
  ]
}
