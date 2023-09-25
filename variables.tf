variable "region" {
  default = "eu-north-1"
}
variable "env" {
  default = "dev"
}
variable "projectname" {
  default = "vhfrp"
}

variable "gh_instance_size" {
    default = {
        "dev" = "t3.micro"
        "prod" = "t3.medium"
    } 
}
#gateway has not much load, so it micro anyway
#whereas
#gamehost in prod require the way more RAM than micro provide
locals {
  gw_instance_type = "t3.micro"
  gh_instance_type = lookup(var.gh_instance_size, var.env)
}

locals  {
  common_tags = {"Project" = "${var.projectname}","Environmemnt" = "${var.env}"}  
  nameprefix = "${var.env}-${var.projectname}-"
}

variable "gw_port_list_tcp" {
  type = list
  default = ["7000","7080","22"]
}
variable "gw_port_list_udp" {
  type = list
  default = ["2456","2457","2458"]
}

variable "gh_port_list_tcp" {
  type = list
  default = ["22"]
}