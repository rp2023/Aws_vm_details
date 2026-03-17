# Aws_vm_details
Use for development
# AWS VM Details Dashboard

A comprehensive Python Flask-based dashboard for monitoring and managing AWS EC2 instances across all regions in real-time with IAM role authentication.

## Features

✨ **Real-time Monitoring**
- Live EC2 instance data from all AWS regions
- Auto-refresh every 30 seconds
- Real-time CloudWatch metrics integration

🔍 **Advanced Search & Filtering**
- Search by Instance ID, IP address, instance type, or region
- Filter by instance state (running, stopped, pending, terminated)
- Filter by AWS region
- Instant search results

📊 **Data Visualization**
- Interactive table view with sortable columns
- Global map visualization showing instance distribution by region
- Instance statistics dashboard
- Region-wise instance count display

📥 **Export Capabilities**
- Export to CSV format
- Export to JSON format
- Download with timestamp

🔐 **Security**
- IAM role-based authentication (no hardcoded credentials)
- Automatic credential detection from EC2 instance metadata

🎨 **User Interface**
- Modern, responsive Bootstrap 5 design
- AWS-themed styling
- Mobile-friendly interface
- Interactive modals for detailed instance information

## Prerequisites

- AWS EC2 instance or local environment with AWS credentials
- Python 3.7+
- IAM role with permissions to describe EC2 instances and CloudWatch metrics

## Required IAM Permissions

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeRegions",
                "cloudwatch:GetMetricStatistics"
            ],
            "Resource": "*"
        }
    ]
}
