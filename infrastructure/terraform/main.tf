
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "4.6.0"
    }
  }
}

provider "docker" {
  host = "npipe:////.//pipe//docker_engine"
}

resource "docker_image" "web" {
  name         = "nginx:alpine"
  keep_locally = true
}

resource "docker_container" "web" {
  name  = var.container_name
  image = docker_image.web.image_id

  restart = "no"

  labels {
    label = "project"
    value = "ContextIQ"
  }

  labels {
    label = "purpose"
    value = "terraform-learning"
  }
}
