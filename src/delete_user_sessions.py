import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
sessions_table_name = os.environ['SESSIONS_TABLE_NAME']
sessions_table = dynamodb.Table(sessions_table_name)
sessions_cluster_user_index_name = 'ClusterUserGSI'
iam_role_mapping_table_name = os.environ['IAM_ROLE_MAPPING_TABLE_NAME']
iam_role_mapping_table = dynamodb.Table(iam_role_mapping_table_name)

def handler(event, context):
    # Lookup all active sessions associated with user
    response = sessions_table.query(
        IndexName=sessions_cluster_user_index_name,
        KeyConditionExpression='ClusterUser = :cluserUser',
        ExpressionAttributeValues={
            ':cluserUser': event["pathParameters"]["userId"],
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
        roleArns.add(queryRoleArn(item["ProjectId"]))
    print('roleArns', roleArns)
    # TODO: Add IAM call integration
    return {
            'statusCode': 200,
            'body': '{}'
        }

def queryRoleArn(projectId):
    response = iam_role_mapping_table.query(
        KeyConditionExpression='ProjectId = :id',
        ExpressionAttributeValues={
            ':id': projectId
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
    
def generateIamRevocationPolicy(roleSessionNameString):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": [
                    "*/" + roleSessionNameString
                ],
                "Resource": [
                    "*"
                ],
                "Condition": {
                    "DateLessThan": {
                        "aws:TokenIssueTime": get_current_time()
                    }
                }
            }
        ]
    }

