
#WIP once identified the session to invalidate, update the status to INVALIDATED

import json
import uuid
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['SESSIONS_TABLE_NAME']
table = dynamodb.Table(table_name)

def handler(event, context):
    # Lookup for sessions
    #1 /sessions/cluster/{id}/project/{id}/user/{id}
    sessions = table.query(
        KeyConditionExpression='clusterUserProjectIdClusterName = :clusterprojectuser',
        ExpressionAttributeValues={
            ':clusterprojectuser': event["pathParameters"]["cluster"] + '|' + event["pathParameters"]["project"] + '|' + event["pathParameters"]["user"]
        }
    )
    items = sessions['Items']

    if len(items) == 0:
        # /sessions/cluster/{id}/project/{id}
        sessions = table.query(
            KeyConditionExpression='clusterUserProjectIdClusterName = :clusterproject',
            ExpressionAttributeValues={
                ':clusterproject': event["pathParameters"]["cluster"] + '|' + event["pathParameters"]["project"]
            }
        )
        items = sessions['Items']

        if len(items) == 0:
            # /sessions/cluster/{id}/user/{id}
            sessions = table.query(
                KeyConditionExpression='clusterUserClusterName = :clusteruser',
                ExpressionAttributeValues={
                    ':clusteruser': event["pathParameters"]["cluster"] + '|' + event["pathParameters"]["user"]
                }
            )
            items = sessions['Items']

            if len(items) == 0:
                # /sessions/user/{id}/project/{id}
                sessions = table.query(
                    KeyConditionExpression='clusterUserProjectId = :userproject',
                    ExpressionAttributeValues={
                        ':userproject': event["pathParameters"]["user"] + '|' + event["pathParameters"]["project"]
                    }
                )
                items = sessions['Items']

                if len(items) == 0:
                    # /sessions/cluster/{id}
                    sessions = table.query(
                        KeyConditionExpression='clusterName = :cluster',
                        ExpressionAttributeValues={
                            ':cluster': event["pathParameters"]["cluster"]
                        }
                    )
                    items = sessions['Items']

                    if len(items) == 0:
                        # /sessions/project/{id}
                        sessions = table.query(
                            KeyConditionExpression='projectId = :project',
                            ExpressionAttributeValues={
                                ':project': event["pathParameters"]["project"]
                            }
                        )
                        items = sessions['Items']

                        if len(items) == 0:
                            # /sessions/user/{id}
                            sessions = table.query(
                                KeyConditionExpression='clusterUser = :user',
                                ExpressionAttributeValues={
                                    ':user': event["pathParameters"]["user"]
                                }
                            )
                            items = sessions['Items']

                            if len(items) == 0:
                                # /sessions/session{id}/cluster/{id}
                                sessions = table.query(
                                    KeyConditionExpression='clusterUserProjectIdClusterName = :clustersession',
                                    ExpressionAttributeValues={
                                        ':clustersession': event["pathParameters"]["cluster"] + '|' + event["pathParameters"]["sessionId"]
                                    }
                                )
                                items = sessions['Items']

                                if len(items) == 0:
                                    return {
                                        'statusCode': 404,
                                        'body': json.dumps('No sessions found')
                                    }
    # Invalidate sessions
    # put status=INVALIDATED