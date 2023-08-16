import json
import uuid
import os
import boto3
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
table_name = os.environ['SESSIONS_TABLE_NAME']
table = dynamodb.Table(table_name)

class DecimalEncoder(json.JSONEncoder):
  def default(self, obj):
    if isinstance(obj, Decimal):
      return str(obj)
    return json.JSONEncoder.default(self, obj)

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
        KeyConditionExpression='ClusterNameSessionId = :clusterNameSessionId',
        ExpressionAttributeValues={
            ':clusterNameSessionId': event["pathParameters"]["clusterId"] + "-" + event["pathParameters"]["sessionId"],
        },
        ScanIndexForward=False,
        Limit=1
    )
    items = response['Items']

    if len(items) != 1:
        return {
            'statusCode': 404,
            'body': json.dumps({"message": "clusterName and sessionId combination invalid"})
        }
    # /sessions/{id}/cluster/{id}/project/{id}
    session = items[0]
    if body['status'] not in ["COMPLETED", "ACTIVE", "INVALIDATED"]:
        return {
            'statusCode': 400,
            'body': json.dumps({"message": "Status can only be updated to ACTIVE, COMPLETED, or INVALIDATED"})
        }
    session['Status'] = body['status']

    # Write session token to DynamoDB table
    table.put_item(
        Item=session
    )
    del session['SessionToken']
    return {
        'statusCode': 200,
        'body': json.dumps(session, cls=DecimalEncoder)
    }
