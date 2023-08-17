import json
import os
import boto3
import re
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
iam = boto3.client('iam')
sessions_table_name = os.environ['SESSIONS_TABLE_NAME']
sessions_table = dynamodb.Table(sessions_table_name)
sessions_last_updated_time_index_name = "LastUpdatedTimeGSI"
iam_role_mapping_table_name = os.environ['IAM_ROLE_MAPPING_TABLE_NAME']
iam_role_mapping_table = dynamodb.Table(iam_role_mapping_table_name)

# Set the number of days looking backwards from the current day that should be queried and cleaned-up. The most recent 24 hours is excluded to prevent removing active revocations.
cleanup_window_days = 3

def handler(event, context):
    # Capture current time for consistent use across all revocation activities
    last_updated_date_time_max = datetime.now() - timedelta(days=1)
    last_updated_epoch_time_max = int(last_updated_date_time_max.timestamp())
    print('last_updated_epoch_time_max', last_updated_epoch_time_max)
    
    last_updated_date_time_min = datetime.now() - timedelta(days=cleanup_window_days)
    last_updated_epoch_time_min = int(last_updated_date_time_min.timestamp())
    print('last_updated_epoch_time_min', last_updated_epoch_time_min)
    
    # Lookup all "Invalidated" sessions that are dated within cleanup window days timeframe specified in cleanup_window_days variable
    # TODO: Add handling for scans where returned values exceed 1 MB of data suing LastEvaluatedKey token
    response = sessions_table.scan(
        IndexName=sessions_last_updated_time_index_name,
        FilterExpression='#SessionStatus = :statusValue AND LastUpdatedTime >= :lastUpdatedTimeMin',
        ExpressionAttributeValues={
            ':statusValue': 'INVALIDATED',
            ':lastUpdatedTimeMin': last_updated_epoch_time_min
        },
        # Using AttributeNames since Status is a DynamoDB reserved keyword
        ExpressionAttributeNames={
            '#SessionStatus': 'Status'
        },
        ProjectionExpression="ClusterName,LastUpdatedTime,ProjectId,SessionId",
        Select="SPECIFIC_ATTRIBUTES"
    )
    items = response['Items']
    role_arns = set()
    print("Invalidated sessions within cleanup window specified", items)

    # Lookup all applicable IAM role ARNs associated to projects and remove any obsolete IAM role inline revocation policies
    for item in items:
        role_arns.add(query_role_arn(item["ProjectId"]))
    print('Role ARNs associated with invalidated sessions to clean up', role_arns)
    for role_arn in role_arns:
        delete_obsolete_role_revocation_policies(role_arn, last_updated_epoch_time_min, last_updated_epoch_time_max)
    return {
            'statusCode': 200,
            'body': '{}'
        }

def query_role_arn(project_id):
    response = iam_role_mapping_table.query(
        KeyConditionExpression='ProjectId = :id',
        ExpressionAttributeValues={
            ':id': project_id
        }
    )
    items = response['Items']
    if len(items) == 1:
        return items[0]["RoleArn"]
    else:
        raise Exception('')
    
def delete_obsolete_role_revocation_policies(role_arn, revocation_time_min, revocation_time_max):
    arn_pattern = r'arn:aws:iam::\d+:role/([^/]+)'
    role_name = re.match(arn_pattern, role_arn).group(1)
    if role_name:
        policy_names = iam.list_role_policies(RoleName=role_name)["PolicyNames"]
        print("Inline policies found for " + role_name, policy_names)
        policies_for_removal = []
        pattern = r'Revocation-(\d+)'
        for policy in policy_names:
            match = re.match(pattern, policy)
            if match:
                revocation_time = int(match.group(1))
                if revocation_time_min <= revocation_time <= revocation_time_max:
                    policies_for_removal.append(policy)
        print('Inline policies for removal from ' + role_name, policies_for_removal)
        for policy in policies_for_removal:
            response = iam.delete_role_policy(
                RoleName=role_name,
                PolicyName=policy
            )
            print("Removed policy " + policy + " from role " + role_name)
        return
    else:
        return None