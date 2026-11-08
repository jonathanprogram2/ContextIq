
output "container_name" {
  description = "Name of the provisioned container"
  value       = docker_container.web.name
}

output "container_id" {
  description = "Docker identifier of the provisioned container"
  value       = docker_container.web.id
}
