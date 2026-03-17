import os
import json
from flask import Flask, render_template, request, jsonify, send_file
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
import csv
import io

app = Flask(__name__)

# Initialize EC2 client with IAM role
# The IAM role is automatically detected from the EC2 instance or environment
ec2_client = boto3.client('ec2')

def get_ec2_instances():
    """Fetch all EC2 instances from all regions"""
    try:
        ec2_resource = boto3.resource('ec2')
        instances_by_region = {}
        
        # Get all regions
        regions = ec2_client.describe_regions()['Regions']
        
        for region in regions:
            region_name = region['RegionName']
            try:
                ec2 = boto3.resource('ec2', region_name=region_name)
                instances = []
                
                for instance in ec2.instances.all():
                    instance_data = {
                        'InstanceId': instance.id,
                        'InstanceType': instance.instance_type,
                        'State': instance.state['Name'],
                        'LaunchTime': instance.launch_time.isoformat() if instance.launch_time else 'N/A',
                        'PublicIpAddress': instance.public_ip_address or 'N/A',
                        'PrivateIpAddress': instance.private_ip_address or 'N/A',
                        'Region': region_name,
                        'AvailabilityZone': instance.placement['AvailabilityZone'],
                        'Tags': {tag['Key']: tag['Value'] for tag in (instance.tags or [])},
                        'KeyName': instance.key_name or 'N/A',
                        'SecurityGroups': [sg['GroupName'] for sg in instance.security_groups],
                        'RootDeviceType': instance.root_device_type,
                        'VpcId': instance.vpc_id,
                        'SubnetId': instance.subnet_id,
                        'Monitoring': instance.monitoring['State'],
                        'EbsOptimized': instance.ebs_optimized,
                    }
                    instances.append(instance_data)
                
                if instances:
                    instances_by_region[region_name] = instances
            except Exception as e:
                print(f"Error fetching instances from {region_name}: {str(e)}")
                continue
        
        return instances_by_region
    except ClientError as e:
        print(f"Error: {str(e)}")
        return {}

def get_instance_metrics(instance_id, region):
    """Get CloudWatch metrics for an instance"""
    try:
        cloudwatch = boto3.client('cloudwatch', region_name=region)
        
        metrics = {
            'CPUUtilization': None,
            'NetworkIn': None,
            'NetworkOut': None,
            'DiskReadOps': None,
            'DiskWriteOps': None,
        }
        
        for metric_name in metrics.keys():
            try:
                response = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName=metric_name,
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=datetime.now().replace(hour=0, minute=0, second=0, microsecond=0),
                    EndTime=datetime.now(),
                    Period=3600,
                    Statistics=['Average']
                )
                
                if response['Datapoints']:
                    metrics[metric_name] = response['Datapoints'][-1]['Average']
            except Exception as e:
                print(f"Error fetching {metric_name}: {str(e)}")
        
        return metrics
    except Exception as e:
        print(f"Error: {str(e)}")
        return {}

@app.route('/')
def index():
    """Main dashboard page"""
    instances_by_region = get_ec2_instances()
    return render_template('index.html', instances_by_region=instances_by_region)

@app.route('/api/instances')
def api_instances():
    """API endpoint to get instances with filters"""
    instances_by_region = get_ec2_instances()
    
    # Flatten instances for filtering
    all_instances = []
    for region, instances in instances_by_region.items():
        all_instances.extend(instances)
    
    # Apply filters
    state_filter = request.args.get('state', '').lower()
    region_filter = request.args.get('region', '').lower()
    search_query = request.args.get('search', '').lower()
    
    filtered_instances = []
    for instance in all_instances:
        if state_filter and instance['State'].lower() != state_filter:
            continue
        if region_filter and instance['Region'].lower() != region_filter:
            continue
        if search_query:
            search_fields = [
                instance['InstanceId'],
                instance['InstanceType'],
                instance['Region'],
                instance['PublicIpAddress'],
                instance['PrivateIpAddress'],
                str(instance['Tags'])
            ]
            if not any(search_query in field.lower() for field in search_fields):
                continue
        
        filtered_instances.append(instance)
    
    return jsonify(filtered_instances)

@app.route('/api/instance/<instance_id>/<region>')
def api_instance_details(instance_id, region):
    """API endpoint to get detailed metrics for an instance"""
    try:
        metrics = get_instance_metrics(instance_id, region)
        return jsonify({'metrics': metrics, 'timestamp': datetime.now().isoformat()})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/regions')
def api_regions():
    """API endpoint to get available regions"""
    try:
        regions = ec2_client.describe_regions()['Regions']
        region_list = [r['RegionName'] for r in regions]
        return jsonify(region_list)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/csv')
def export_csv():
    """Export instances data as CSV"""
    try:
        instances_by_region = get_ec2_instances()
        all_instances = []
        for region, instances in instances_by_region.items():
            all_instances.extend(instances)
        
        # Create CSV
        output = io.StringIO()
        if all_instances:
            fieldnames = all_instances[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for instance in all_instances:
                row = {k: v for k, v in instance.items() if k != 'Tags' and k != 'SecurityGroups'}
                row['Tags'] = json.dumps(instance.get('Tags', {}))
                row['SecurityGroups'] = ','.join(instance.get('SecurityGroups', []))
                writer.writerow(row)
        
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'ec2_instances_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export/json')
def export_json():
    """Export instances data as JSON"""
    try:
        instances_by_region = get_ec2_instances()
        
        output = io.StringIO()
        output.write(json.dumps(instances_by_region, indent=2, default=str))
        output.seek(0)
        
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='application/json',
            as_attachment=True,
            download_name=f'ec2_instances_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000
