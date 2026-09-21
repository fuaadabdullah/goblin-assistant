output "public_ip" {
  description = "VM public IP — point your DNS A record here"
  value       = oci_core_instance.goblin.public_ip
}

output "ssh_command" {
  value = "ssh ubuntu@${oci_core_instance.goblin.public_ip}"
}

output "next_steps" {
  value = <<-EOT

    Instance provisioned. Next steps:

    1. Wait ~2 min for cloud-init to finish:
         ssh ubuntu@${oci_core_instance.goblin.public_ip} "sudo cloud-init status --wait"

    2. Copy your .env to the VM:
         scp infra/oracle/.env ubuntu@${oci_core_instance.goblin.public_ip}:~/goblin-assistant/infra/oracle/.env

    3. Start the stack:
         ssh ubuntu@${oci_core_instance.goblin.public_ip} \
           "cd ~/goblin-assistant/infra/oracle && docker compose pull && docker compose up -d --no-build --remove-orphans"

    4. Point your DNS A record to ${oci_core_instance.goblin.public_ip}
       then Caddy handles TLS automatically.

    5. After the stack is healthy, run the OCI lifecycle monitor:
         ssh ubuntu@${oci_core_instance.goblin.public_ip} \
           "cd ~/goblin-assistant && python3 scripts/ops/oci_lifecycle_monitor.py --domain \"$${GOBLIN_API_DOMAIN}\""

  EOT
}
