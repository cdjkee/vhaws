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
        Name = "${local.nameprefix}sg_gw"
    }
    lifecycle {
        create_before_destroy = true
    }
}

//all the connections initiate gh (via FRP client), so only open port required is 22 for SSH
resource "aws_security_group" "sg_gh" {
  name = "sg_gh"
  description = "Ports for SSH" 
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
     name = "${local.nameprefix}sg_gh"
   }
   lifecycle {
     create_before_destroy = true
   }
}

resource "aws_instance" "ec2_gw" {
    ami = data.aws_ami.latest_ubuntu.id
    instance_type = local.gw_instance_type
    key_name = "cdjkeeaws"
    vpc_security_group_ids = [aws_security_group.sg_gw.id]
    tags = {
        name = "${local.nameprefix}ec2_gw"
    }

    # tags = merge(local.common_tags,{name = "gw"})
}

resource "aws_instance" "ec2_gh" {
    ami = data.aws_ami.latest_ubuntu.id
    instance_type = local.gh_instance_type
    key_name = "cdjkeeaws"
    vpc_security_group_ids = [aws_security_group.sg_gh.id]
    iam_instance_profile = "${aws_iam_instance_profile.profile_gh.name}"
    tags = {
        name = "${local.nameprefix}ec2_gh"
    }
}

resource "aws_eip" "eip_gw" {
  instance = aws_instance.ec2_gw.id
  tags = {
      name = "${local.nameprefix}eip_gw"
  }
}

#Role related
#All the names with prefix to ensure uniqueness
resource "aws_iam_instance_profile" "profile_gh" {
  name = "${local.nameprefix}profile_gh"
  role = "${aws_iam_role.role_s3readonly.name}"
}

resource "aws_iam_role" "role_s3readonly" {
  name = "${local.nameprefix}role_s3readonly"
  description = "S3 readonly for a single bucket with valheim worlds"

  assume_role_policy = file("files/assume_role_policy.json")

  tags = {
    name = "${local.nameprefix}role_s3readonly"
  }
}

resource "aws_iam_role_policy" "policy_s3readonly" {
  name = "${local.nameprefix}policy_s3readonly"
  role = "${aws_iam_role.role_s3readonly.id}"
  #TODO: make an actual template and fill the name of S3 bucket
  policy =  templatefile("templates/s3_readonly_policy.json.tmpl", {"test"="test"})
}

# Iventory generation
data "template_file" "servers" {
  template = file("templates/inventory.tmpl")
  depends_on = [
    aws_instance.ec2_gh,
    aws_instance.ec2_gw
    ]
  vars = {
    gw_ip = "${aws_instance.ec2_gw.public_ip}"
    gh_ip = "${aws_instance.ec2_gh.public_ip}"
  }
}

resource "null_resource" "servers" {
  triggers = {
    template_rendered = "${data.template_file.servers.rendered}"
  }
  provisioner "local-exec" {
    command = "echo '${data.template_file.servers.rendered}' > inventory"
  }
}