#WIP
import json
import os
import boto3
import re
import time
from datetime import datetime, timezone

dynamodb = boto3.resource('dynamodb')
iam = boto3.client('iam')
sessions_table_name = os.environ['SESSIONS_TABLE_NAME']
sessions_table = dynamodb.Table(sessions_table_name)
sessions_clusters_index_name = 'ClusterNameGSI'
sessions_projects_index_name = 'ProjectIdGSI'
sessions_users_index_name = 'ClusterUserGSI'
iam_role_mapping_table_name = os.environ['IAM_ROLE_MAPPING_TABLE_NAME']
iam_role_mapping_table = dynamodb.Table(iam_role_mapping_table_name)


def handler(event, context):
    # Capture current time for consistent use across all revocation activities
    revocation_time = get_current_epoch_time()
    role_session_name_pattern = "*"
    
    clustersessions = None
    if "cluster" in event["pathParameters"]:
        sessions = sessions_table.query(
            IndexName=sessions_clusters_index_name,
            KeyConditionExpression='ClusterName = :cluster',
            ExpressionAttributeValues={
                ':cluster': event["pathParameters"]["cluster"],
                ':statusValue': 'ACTIVE'
            }
        )
        clustersessions = sessions['Items']

        if len(clustersessions) == 0:
            clustersessions = None
    #2 find sessions by project
    projectsessions = None
    sessions = sessions_table.query(
        IndexName=sessions_projects_index_name,
        KeyConditionExpression='ProjectId = :project',
        ExpressionAttributeValues={
            ':project': event["pathParameters"]["project"],
            ':statusValue': 'ACTIVE'
        }
    )
    projectsessions = sessions['Items']

    if len(projectsessions) == 0:
        projectsessions = None

    #3 find sessions by user
    usersessions = None
    sessions = sessions_table.query(
        IndexName=sessions_users_index_name,
        KeyConditionExpression='ClusterUser = :user',
        ExpressionAttributeValues={
            ':user': event["pathParameters"]["user"],
            ':statusValue': 'ACTIVE'
        }
    )
    usersessions = sessions['Items']

    if len(usersessions) == 0:
        usersessions = None
    
    # if clustersessions, projectsessions and usersessions are not None, compute intersection of them
    if clustersessions is not None and projectsessions is not None and usersessions is not None:
        items = list(set(clustersessions) & set(projectsessions) & set(usersessions))
    elif clustersessions is not None and projectsessions is not None:
        items = list(set(clustersessions) & set(projectsessions))
    elif clustersessions is not None and usersessions is not None:
        items = list(set(clustersessions) & set(usersessions))
    elif projectsessions is not None and usersessions is not None:
        items = list(set(projectsessions) & set(usersessions))
    elif clustersessions is not None:
        items = clustersessions
    elif projectsessions is not None:
        items = projectsessions
    elif usersessions is not None:
        items = usersessions
    else:
        items = None

    role_arns = set()
    print("Active sessions for revocation associated with user", items)
    # Update active sessions for user to invalidated status. Lookup all applicable IAM role ARNs associated to projects
    for item in items:
        item["Status"] = "INVALIDATED"
        item["LastUpdatedTime"] = get_current_epoch_time()
        sessions_table.put_item(Item=item)
        role_arns.add(query_role_arn(item["ProjectId"]))
    for role_arn in role_arns:
        put_role_revocation_policy(revocation_time, role_arn, role_session_name_pattern)
    print('Role ARNs associated with user sessions for revocation ', role_arns)
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

def get_current_epoch_time():
    epoch_time = int(time.time())
    return epoch_time

def get_formatted_iso_time(epoch_time):
    formatted_time = datetime.fromtimestamp(epoch_time, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
    return formatted_time
    
def generate_iam_revocation_policy(revocation_time, role_id, role_session_name_pattern):
    return {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Deny",
                "Action": [
                    "*"
                ],
                "Resource": [
                    "*"
                ],
                "Condition": {
                    "DateLessThan": {
                        "aws:TokenIssueTime": get_formatted_iso_time(revocation_time)
                    },
                    "StringLike": {
					    "aws:userId": role_id + ":" + role_session_name_pattern
				    }
                }
            }
        ]
    }

def remove_non_alphanumeric(input_string):
    # Define the pattern to match non-alphanumeric characters and additional characters to keep
    pattern = r'[^a-zA-Z0-9+=,.@_-]'
    cleaned_string = re.sub(pattern, '', input_string)
    return cleaned_string

def put_role_revocation_policy(revocation_time, role_arn, role_session_name_pattern):
    arn_pattern = r'arn:aws:iam::\d+:role/([^/]+)'
    role_name = re.match(arn_pattern, role_arn).group(1)
    if role_name:
        response = iam.get_role(RoleName=role_name)
        role_id = response["Role"]["RoleId"]
        response = iam.put_role_policy(
            RoleName=role_name,
            PolicyName="Revocation-" + str(revocation_time) + "-" + "User-" + remove_non_alphanumeric(role_session_name_pattern),
            PolicyDocument=json.dumps(generate_iam_revocation_policy(revocation_time, role_id, role_session_name_pattern))
        )
        return response
    else:
        return None


