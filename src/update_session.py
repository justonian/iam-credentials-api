import json
import uuid
import os
import boto3

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['SESSIONS_TABLE_NAME']
table = dynamodb.Table(table_name)

def handler(event, context):
    try:
        body = json.loads(event['body'])
    except KeyError:
        return {
            'statusCode': 400,
            'body': 'Missing request body'
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': 'Invalid JSON format'
        }
    response = table.query(
        KeyConditionExpression='sessionId = :id',
        ExpressionAttributeValues={
            ':id': event["pathParameters"]["sessionId"]
        }
    )
    items = response['Items']

    if len(items) != 1:
        raise Exception("Session does not exist")
    # /sessions/{id}/cluster/{id}/project/{id}/clusterNode/{id}
    session = items[0]
    # TODO Validate status
    session['status'] = body['status']

    # Write session token to DynamoDB table
    table.put_item(
        Item=session
    )
    del session['sessionToken']
    return {
        'statusCode': 200,
        'body': json.dumps(session)
    }
