
#WIP
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
    #1 find sessions by cluster
    clustersessions = None
    if "cluster" in event["pathParameters"]:
        sessions = sessions_table.query(
            IndexName=sessions_clusters_index_name,
            KeyConditionExpression='clusterName = :cluster',
            ExpressionAttributeValues={
                ':cluster': event["pathParameters"]["cluster"]
            }
        )
        clustersessions = sessions['Items']

        if len(clustersessions) == 0:
            clustersessions = None
    #2 find sessions by project
    projectsessions = None
    sessions = sessions_table.query(
        IndexName=sessions_projects_index_name,
        KeyConditionExpression='clusterUserProjectIdClusterName = :project',
        ExpressionAttributeValues={
            ':project': event["pathParameters"]["project"]
        }
    )
    projectsessions = sessions['Items']

    if len(projectsessions) == 0:
        projectsessions = None

    #3 find sessions by user
    usersessions = None
    sessions = sessions_table.query(
        IndexName=sessions_users_index_name,
        KeyConditionExpression='clusterUserClusterName = :user',
        ExpressionAttributeValues={
            ':user': event["pathParameters"]["user"]
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

    if len(items) > 0:
        return {
            'statusCode': 200,
            'body': json.dumps(items)
        }
    
    return {
        'statusCode': 404,
        'body': json.dumps('No sessions found')
    }