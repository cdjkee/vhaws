provider "aws" {
    region = var.region
    default_tags {
      tags = {
        Project = var.projectname
        Environmemnt = var.env
        Terraform = "true"
      }

    }
  
}
#security group for gateway
resource "aws_security_group" "sg_gw" {
    name = "sg_gw"
    description = "Ports for TGbot, Valheim dedicated server via FRPserver, SSH"

    dynamic "ingress" {
        for_each = ["7000","7080","22"]
        content{
            from_port = ingress.value
            to_port = ingress.value
            protocol = "tcp"
            cidr_blocks = ["0.0.0.0/0"]
        }
    }

    dynamic "ingress" {
        for_each = ["2456","2457","2458"]
        content {
          from_port = ingress.value
          to_port = ingress.value
          protocol = "udp"
          cidr_blocks = ["0.0.0.0/0"]
        }
    }

    egress {
        from_port = 0
        to_port = 0
        protocol = -1
        cidr_blocks = ["0.0.0.0/0"]
    }
    tags = {
        Name = concat(local.nameprefix, "sg_gw")
    }
    lifecycle {
        create_before_destroy = true
    }
}

resource "aws_security_group" "sg_gh" {
  name = "sg_gh"
  ingress {
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = -1
    cidr_blocks = ["0.0.0.0/0"]
   }
   tags = {
     name = concat(local.nameprefix, "sg_gh")
   }
   lifecycle {
     create_before_destroy = true
   }
}

resource "aws_instance" "gw" {
    ami = data.aws_ami.latest_ubuntu.id
    instance_type = local.gw_instance_type
    key_name = "cdjkeeaws"
    tags = {
        name = concat(local.nameprefix, "ec2_gw")
    }

    # tags = merge(local.common_tags,{name = "gw"})
}

resource "aws_instance" "gh" {
    ami = data.aws_ami.latest_ubuntu.id
    instance_type = local.gh_instance_type
    key_name = "cdjkeeaws"
    tags = {
        name = concat(local.nameprefix, "ec2_gh")
    }
}