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
module "lambda-stop" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "6.0.1"

  function_name          = "lambda-stop"
  description            = "Stops game host by request"
  handler                = "lambda-stop-ec2.lambda_handler"
  runtime                = "python3.11"
  publish                = true

  source_path = "files/lambda-stop"
  attach_policy_json = true
  policy_json = file("files/amazon_ec2_full_policy.json")
}
module "lambda-start" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "6.0.1"

  function_name          = "lambda-start"
  description            = "Starts game host by request"
  handler                = "lambda-start-ec2.lambda_handler"
  runtime                = "python3.11"
  publish                = true

  source_path = "files/lambda-start"
  attach_policy_json = true
  policy_json = file("files/amazon_ec2_full_policy.json")
}

module "lambda-status" {
  source  = "terraform-aws-modules/lambda/aws"
  version = "6.0.1"

  function_name          = "lambda-status"
  description            = "Starts game host by request"
  handler                = "lambda-status-ec2.lambda_handler"
  runtime                = "python3.11"
  publish                = true

  source_path = "files/lambda-status"
  attach_policy_json = true
  policy_json = file("files/amazon_ec2_full_policy.json")
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
     Name = "${local.nameprefix}sg_gh"
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
    iam_instance_profile = "${aws_iam_instance_profile.profile_gw.name}"
    user_data = file("files/user_data.sh")
    tags = {
        Name = "${local.nameprefix}ec2_gw"
    }

    # tags = merge(local.common_tags,{name = "gw"})
}

resource "aws_instance" "ec2_gh" {
    ami = data.aws_ami.latest_ubuntu.id
    instance_type = local.gh_instance_type
    key_name = "cdjkeeaws"
    vpc_security_group_ids = [aws_security_group.sg_gh.id]
    iam_instance_profile = "${aws_iam_instance_profile.profile_gh.name}"
    user_data = file("files/user_data.sh")
    tags = {
        Name = "${local.nameprefix}ec2_gh"
        Ctl = "lambda"
    }
}

resource "aws_eip" "eip_gw" {
  instance = aws_instance.ec2_gw.id
  tags = {
      Name = "${local.nameprefix}eip_gw"
  }
}


#Role related
#All the names with prefix to ensure uniqueness

#Role for game host
#Game host required s3 access to store and retrieve worlds files
resource "aws_iam_instance_profile" "profile_gh" {
  name = "${local.nameprefix}profile_gh"
  role = "${aws_iam_role.role_s3readonly.name}"
}
resource "aws_iam_role" "role_s3readonly" {
  name = "${local.nameprefix}role_s3readonly"
  description = "S3 readonly for a single bucket with valheim worlds"
  assume_role_policy = file("files/assume_role_policy_ec2.json")
  tags = {
    Name = "${local.nameprefix}role_s3readonly"
  }
}
resource "aws_iam_role_policy" "policy_s3readonly" {
  name = "${local.nameprefix}policy_s3readonly"
  role = "${aws_iam_role.role_s3readonly.id}"
  #TODO: make an actual template and fill the name of S3 bucket
  policy =  templatefile("templates/s3_readonly_policy.json.tmpl", {"test"="test"})
}

#Role for gateway
#gateway hosting telegram bot requires access to Start, stop and restart game host
resource "aws_iam_instance_profile" "profile_gw" {
  name = "${local.nameprefix}profile_gw"
  role = "${aws_iam_role.role_control_gh.name}"
}
resource "aws_iam_role" "role_control_gh" {
  name = "${local.nameprefix}role_control_gh"
  description = "Allow to start, stop  and restart the game host"
  assume_role_policy = file("files/assume_role_policy_ec2.json")
  tags = {
    Name = "${local.nameprefix}role_control_gh"
  }
}
resource "aws_iam_role_policy" "policy_control_gh" {
  name = "${local.nameprefix}policy_control_gh"
  role = "${aws_iam_role.role_control_gh.id}"
  policy = templatefile("templates/control_gh_policy.json.tmpl", {gh_name = "${aws_instance.ec2_gh.tags.Name}", region = "${var.region}"})
  
}
#role for lambda
#requires access to Start, stop and restart game host
resource "aws_iam_instance_profile" "profile_lambda" {
  name = "${local.nameprefix}profile_lambda"
  role = "${aws_iam_role.role_lambda_control_gh.name}"
}
resource "aws_iam_role" "role_lambda_control_gh" {
  name = "${local.nameprefix}role_lambda_control_gh"
  description = "Allow Lambda to start, stop  and restart the game host"
  assume_role_policy = file("files/assume_role_policy_lambda.json")
  tags = {
    Name = "${local.nameprefix}role_lambda_control_gh"
  }
}
resource "aws_iam_role_policy" "lambda_policy_control_gh" {
  name = "${local.nameprefix}lambda_policy_control_gh"
  role = "${aws_iam_role.role_lambda_control_gh.id}"
  policy = templatefile("templates/lambda_control_gh_policy.json.tmpl", {gh_name = "${aws_instance.ec2_gh.tags.Name}", region = "${var.region}", accountid ="${data.aws_caller_identity.current.account_id}"})
  
}

# Iventory generation
data "template_file" "servers" {
  template = file("templates/inventory.tmpl")
  depends_on = [
    aws_instance.ec2_gh,
    aws_instance.ec2_gw,
    aws_eip.eip_gw
    ]
  vars = {
    gw_ip = "${aws_eip.eip_gw.public_ip}"
    gh_ip = "${aws_instance.ec2_gh.public_ip}"
  }
}

resource "null_resource" "servers" {
  triggers = {
    template_rendered = "${data.template_file.servers.rendered}"
  }
  provisioner "local-exec" {
    command = "echo '${data.template_file.servers.rendered}' > ../ansible/inventory"
  }
}