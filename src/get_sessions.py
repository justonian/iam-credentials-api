import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['SESSIONS_TABLE_NAME']
sessions_table = dynamodb.Table(table_name)
sessions_clusters_index_name = 'ClusterNameGSI'
sessions_projects_index_name = 'ProjectIdGSI'
sessions_users_index_name = 'ClusterUserGSI'

def handler(event, context):
    # Lookup for sessions

    #0 all sessions should we need them
    sessions = sessions_table.scan(
        ExpressionAttributeValues={
            ':statusValue': 'ACTIVE'
        },
        ExpressionAttributeNames={
            '#SessionStatus': 'Status'
        },
        FilterExpression='#SessionStatus = :statusValue'
    )
    allsessions = sessions['Items']

    #1 find sessions by cluster
    clustersessions = None
    if "cluster" in event["pathParameters"]:
        if event["pathParameters"]["cluster"] != "null":
            sessions = sessions_table.query(
                IndexName=sessions_clusters_index_name,
                KeyConditionExpression='ClusterName = :cluster',
                ExpressionAttributeValues={
                    ':cluster': event["pathParameters"]["cluster"],
                    ':statusValue': 'ACTIVE'
                },
            # Using AttributeNames since Status is a DynamoDB reserved keyword
            ExpressionAttributeNames={
                '#SessionStatus': 'Status'
            },
            FilterExpression='#SessionStatus = :statusValue'
            )
            clustersessions = sessions['Items']
        else:
            clustersessions = allsessions

        if len(clustersessions) == 0:
            clustersessions = None

    #2 find sessions by project
    projectsessions = None
    if "project" in event["pathParameters"]:
        if event["pathParameters"]["project"] != "null":
            sessions = sessions_table.query(
                IndexName=sessions_projects_index_name,
                KeyConditionExpression='ProjectId = :project',
                ExpressionAttributeValues={
                    ':project': event["pathParameters"]["project"],
                    ':statusValue': 'ACTIVE'
                },
            # Using AttributeNames since Status is a DynamoDB reserved keyword
            ExpressionAttributeNames={
                '#SessionStatus': 'Status'
            },
            FilterExpression='#SessionStatus = :statusValue'
            )
            projectsessions = sessions['Items']
        else:
            projectsessions = allsessions

        if len(projectsessions) == 0:
            projectsessions = None

    #3 find sessions by user
    usersessions = None
    if "user" in event["pathParameters"]:
        if event["pathParameters"]["user"] != "null":
            sessions = sessions_table.query(
                IndexName=sessions_users_index_name,
                KeyConditionExpression='ClusterUser = :user',
                ExpressionAttributeValues={
                    ':user': event["pathParameters"]["user"],
                    ':statusValue': 'ACTIVE'
                },
            # Using AttributeNames since Status is a DynamoDB reserved keyword
            ExpressionAttributeNames={
                '#SessionStatus': 'Status'
            },
            FilterExpression='#SessionStatus = :statusValue'
            )
            usersessions = sessions['Items']
        else:
            usersessions = allsessions

        if len(usersessions) == 0:
            usersessions = None
    
    # if clustersessions, projectsessions and usersessions are not None, compute intersection of them
    items = intersection(clustersessions, projectsessions, usersessions)


    if items is not None and len(items) > 0:
        return {
            'statusCode': 200,
            'body': json.dumps(items, default=str)
        }
    
    return {
        'statusCode': 404,
        'body': json.dumps('No sessions found')
    }

def intersection(list1, list2, list3):
    if list1 is None or list2 is None or list3 is None:
        return None
    return [v for v in list1 if v in list2 and v in list3]