terraform {
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = "~> 6.0"
    }
  }
}

provider "oci" {
  tenancy_ocid     = var.tenancy_ocid
  user_ocid        = var.user_ocid
  fingerprint      = var.fingerprint
  private_key_path = var.private_key_path
  region           = var.region
}

# ── Network ───────────────────────────────────────────────────────────────────

resource "oci_core_vcn" "goblin" {
  compartment_id = var.compartment_ocid
  display_name   = "goblin-vcn"
  cidr_blocks    = ["10.0.0.0/16"]
  dns_label      = "goblin"
}

resource "oci_core_internet_gateway" "goblin" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.goblin.id
  display_name   = "goblin-igw"
  enabled        = true
}

resource "oci_core_default_route_table" "goblin" {
  manage_default_resource_id = oci_core_vcn.goblin.default_route_table_id
  route_rules {
    network_entity_id = oci_core_internet_gateway.goblin.id
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
  }
}

resource "oci_core_security_list" "goblin" {
  compartment_id = var.compartment_ocid
  vcn_id         = oci_core_vcn.goblin.id
  display_name   = "goblin-seclist"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 22
      max = 22
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 80
      max = 80
    }
  }

  ingress_security_rules {
    protocol = "6"
    source   = "0.0.0.0/0"
    tcp_options {
      min = 443
      max = 443
    }
  }
}

resource "oci_core_subnet" "goblin" {
  compartment_id    = var.compartment_ocid
  vcn_id            = oci_core_vcn.goblin.id
  display_name      = "goblin-subnet"
  cidr_block        = "10.0.0.0/24"
  dns_label         = "goblinapi"
  security_list_ids = [oci_core_security_list.goblin.id]
  route_table_id    = oci_core_default_route_table.goblin.id
}

# ── Latest Ubuntu 22.04 ARM image ─────────────────────────────────────────────

data "oci_core_images" "ubuntu_arm" {
  compartment_id           = var.compartment_ocid
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.A1.Flex"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

# ── Persistent block volume for Docker, Redis, and app state ─────────────────

resource "oci_core_volume" "goblin_data" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = "goblin-data-volume"
  size_in_gbs         = 100
}

# ── ARM instance (Always Free: 2 OCPU / 12 GB; 200 GB combined boot+block) ────

resource "oci_core_instance" "goblin" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_ocid
  display_name        = "goblin-api"
  shape               = "VM.Standard.A1.Flex"

  shape_config {
    ocpus         = 2
    memory_in_gbs = 12
  }

  source_details {
    source_type             = "image"
    source_id               = data.oci_core_images.ubuntu_arm.images[0].id
    boot_volume_size_in_gbs = 50
  }

  create_vnic_details {
    subnet_id        = oci_core_subnet.goblin.id
    assign_public_ip = true
    hostname_label   = "goblin-api"
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
    user_data = base64encode(templatefile("${path.module}/cloud-init.yml", {
      repo_url = var.repo_url
    }))
  }

  launch_options {
    is_consistent_volume_naming_enabled = true
  }

  preserve_boot_volume = false
}

resource "oci_core_volume_attachment" "goblin_data" {
  attachment_type                     = "paravirtualized"
  device                              = "oraclevdb"
  instance_id                         = oci_core_instance.goblin.id
  volume_id                           = oci_core_volume.goblin_data.id
  is_pv_encryption_in_transit_enabled = true
  display_name                        = "goblin-data-attachment"
}

# ── Scheduled backups for durable state ───────────────────────────────────────

resource "oci_core_volume_backup_policy" "goblin_data" {
  compartment_id = var.compartment_ocid
  display_name   = "goblin-data-backup-policy"

  schedules {
    backup_type                 = "INCREMENTAL"
    period                      = "ONE_DAY"
    retention_seconds           = 1209600
    hour_of_day                 = 3
    offset_type                 = "STRUCTURED"
    time_zone                   = "UTC"
    is_prevent_deletion_enabled = true
  }
}

resource "oci_core_volume_backup_policy_assignment" "goblin_data" {
  asset_id  = oci_core_volume.goblin_data.id
  policy_id = oci_core_volume_backup_policy.goblin_data.id
}
