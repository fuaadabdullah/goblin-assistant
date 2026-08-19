variable "tenancy_ocid" {
  description = "Your OCI tenancy OCID (Governance → Tenancy Details)"
}

variable "user_ocid" {
  description = "Your OCI user OCID (Identity → Users → your user)"
}

variable "fingerprint" {
  description = "API key fingerprint (xx:xx:... format)"
}

variable "private_key_path" {
  description = "Path to your OCI API private key PEM file"
  default     = "~/.oci/oci_api_key.pem"
}

variable "region" {
  description = "OCI region — pick one with Always Free ARM availability"
  default     = "us-ashburn-1"
}

variable "compartment_ocid" {
  description = "Compartment OCID — use tenancy_ocid for root compartment"
}

variable "availability_domain" {
  description = "Full AD name, e.g. 'Uocm:US-ASHBURN-AD-1' — run: oci iam availability-domain list"
}

variable "ssh_public_key" {
  description = "Contents of your SSH public key (e.g. ~/.ssh/id_ed25519.pub)"
}

variable "repo_url" {
  description = "Git repo URL — cloned during cloud-init"
  default     = "https://github.com/fuaadabdullah/goblin-assistant.git"
}
