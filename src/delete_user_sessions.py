import json
import os
import boto3
import re
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
iam = boto3.client('iam')
sessions_table_name = os.environ['SESSIONS_TABLE_NAME']
sessions_table = dynamodb.Table(sessions_table_name)
sessions_cluster_user_index_name = 'ClusterUserGSI'
iam_role_mapping_table_name = os.environ['IAM_ROLE_MAPPING_TABLE_NAME']
iam_role_mapping_table = dynamodb.Table(iam_role_mapping_table_name)

def handler(event, context):
    # Capture current time for consistent use across all revocation activities
    revocation_time = get_current_time()
    user_id = event["pathParameters"]["userId"]
    
    # Lookup all active sessions associated with user
    response = sessions_table.query(
        IndexName=sessions_cluster_user_index_name,
        KeyConditionExpression='ClusterUser = :cluserUser',
        ExpressionAttributeValues={
            ':cluserUser': user_id,
            ':statusValue': 'ACTIVE'
        },
        # Using AttributeNames since Status is a DynamoDB reserved keyword
        ExpressionAttributeNames={
            '#SessionStatus': 'Status'
        },
        FilterExpression='#SessionStatus = :statusValue'
    )
    items = response['Items']
    roleArns = set()
    print("items", items)
    # Update active sessions for user to invalidated status. Lookup all applicable IAM role ARNs associated to projects
    for item in items:
        item["Status"] = "INVALIDATED"
        sessions_table.put_item(Item=item)
        roleArns.add(query_role_arn(item["ProjectId"]))
    for role_arn in roleArns:
        put_role_revocation_policy(revocation_time, role_arn, "*" + user_id + "*")
    print('roleArns', roleArns)
    # TODO: Add IAM call integration
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
    
def get_current_time():
    current_time = datetime.now(timezone.utc)
    formatted_time = current_time.strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    return formatted_time
    
def generate_iam_revocation_policy(revocation_time, role_id, role_session_name_pattern):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": [
                    "*/" + role_session_name_pattern
                ],
                "Resource": [
                    "*"
                ],
                "Condition": {
                    "DateLessThan": {
                        "aws:TokenIssueTime": revocation_time
                    },
                    "StringLike": {
					    "aws:userId": role_id + ":" + role_session_name_pattern
				    },
                }
            }
        ]
    }

def put_role_revocation_policy(revocation_time, role_arn, role_session_name_pattern):
    arn_pattern = r'arn:aws:iam::\d+:role/([^/]+)'
    role_name = re.match(arn_pattern, role_arn).group(1)
    if role_name:
        response = iam.get_role(RoleName=role_name)
        role_id = response["Role"],["RoleId"]
        response = iam.put_role_policy(
            RoleName=role_name,
            PolicyName=revocation_time,
            PolicyDocument=generate_iam_revocation_policy(revocation_time, role_id, role_session_name_pattern)
        )
        return response
    else:
        return None


