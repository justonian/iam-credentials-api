import boto3
import json
import os
import re
import requests

DYNAMODB_TABLE=os.environ["IAM_POLICY_STORAGE_TABLE_NAME"]
iam_role_mapping_table_name = os.environ['IAM_ROLE_MAPPING_TABLE_NAME']
URL = os.environ['URL']
TOKEN = os.environ['TOKEN']
lambda_role_arn = os.environ['LAMBDA_ROLE_ARN']

dynamo_resource = boto3.resource('dynamodb')
iam_client = boto3.client('iam')

def lambda_handler(event, context):
    table = dynamo_resource.Table(DYNAMODB_TABLE)
    iam_role_mapping_table = dynamo_resource.Table(iam_role_mapping_table_name)

    headers = {"Authorization":"Bearer "+TOKEN}
    response = requests.get(URL, headers=headers)
    response_json = response.json() # comment to test
    #response_json = event # uncomment to test

    for project in response_json:
        project_name = project['project'] 
        storage = project['storage']
        if storage[0] != None:
            print("Project: %s" % project_name)
            r = table.get_item( Key = {'projectId': project_name})
            if 'Item' in r:
                item = r['Item']
                storage_table = item['storage']
                policy_arn = item['Arn']

                _storage = update_policy(project_name,policy_arn,storage,storage_table)
                if _storage != None:
                    r = table.update_item(
                        Key = {
                            'projectId': project_name
                        },
                        AttributeUpdates = {
                            'storage':  {
                                'Value': _storage,
                                'Action': 'PUT'
                            }
                        }
                    )
                # check if the role exists (maybe it was deleted/renamed/crashed)
                r = iam_role_mapping_table.get_item( Key = {'projectId': project_name})
                if not 'Item' in r:
                    rr = create_role(project_name, policy_arn)                   
                    if rr != None:
                        p = iam_role_mapping_table.put_item(Item= {'projectId': project_name,'roleName': rr['Role']['RoleName'], 'roleArn': rr['Role']['Arn']})
            else:
                rp = create_policy(project_name, storage)
                if rp != None:
                    # create the role and attach the policy
                    r = table.put_item(Item= {'projectId': project_name,'storage':  rp['storage'], 'PolicyName': rp['Policy']['PolicyName'], 'Arn': rp['Policy']['Arn']})
                    rr = create_role(project_name, rp['Policy']['Arn'])                   
                    if rp != None:
                        p = iam_role_mapping_table.put_item(Item= {'projectId': project_name,'roleName': rr['Role']['RoleName'], 'roleArn': rr['Role']['Arn']})

    return {
        'statusCode': 200,
        'body': 'Successful'#response_json
    }

def create_role(project_name, policy_arn):

    trust = """{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "TrustLambda",
                "Effect": "Allow",
                "Principal": {
                    "AWS": "${lambda_role_arn}"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }"""
    # Create the policy in IAM
    try:
        r = iam_client.create_role(
            RoleName='project-'+project_name,
            AssumeRolePolicyDocument=json.dumps(json.loads(trust)),
            Description='Role to allow access to the buckets of the project '+project_name,
            Tags=[
                {
                    'Key': 'Project',
                    'Value': project_name
                },
            ]
        )
        iam_client.attach_role_policy(
            RoleName=r['Role']['RoleName'],
            PolicyArn=policy_arn
        )
        return {
            'Role' : r['Role']
        }
    except Exception as e:
        print('Error in the role for the project ' + project_name + ':' + str(e))
        return None

def create_policy(project_name, storage):
    statements = []
    for bucket in storage:
        if not bucket['read'] and bucket['write']:
            bucket['write'] = False
        statements.append(get_statement(bucket))
    new_policy = {
        "Version": "2012-10-17",
        "Statement": statements
    }

    # Create the policy in IAM
    try:
        r = iam_client.create_policy(
            PolicyName='project-'+project_name,
            PolicyDocument=json.dumps(new_policy),
            Description='Policy to allow access to the buckets of the project '+project_name,
            Tags=[
                {
                    'Key': 'Project',
                    'Value': project_name
                },
            ]
        )
        return {
            'Policy' : r['Policy'],
            'storage': storage 
        }
    except Exception as e:
        print('Error in the policy for the project ' + project_name + ':' + str(e))
        return None

def update_policy(project_name, policy_arn, storage, storage_table):
    try:
        policy = iam_client.get_policy(PolicyArn = policy_arn)
        policy_version = iam_client.get_policy_version(
            PolicyArn = policy_arn, 
            VersionId = policy['Policy']['DefaultVersionId']
        )
    except Exception as e:
        print('Error in the update of the policy for the project ' + project_name + ':' + str(e))
        return None

    statements  = policy_version['PolicyVersion']['Document']['Statement']
    trigger_policy_update = False

    storage = list_to_dict(storage)
    storage_table = list_to_dict(storage_table)
    storage_set = set(storage)
    storage_table_set = set(storage_table)
    statements = list_to_dict(statements,'Sid')

    delete_bucket_statements = storage_table_set - storage_set
    create_bucket_statements = storage_set - storage_table_set
    update_bucket_statements = storage.keys() & storage_table.keys()

    for bucket in delete_bucket_statements:
        trigger_policy_update = True
        del statements[format_bucket_name(bucket)]

    for bucket in create_bucket_statements:
        trigger_policy_update = True
        if not storage[bucket]['read'] and storage[bucket]['write']:
            storage[bucket]['write'] = False
        statements[format_bucket_name(bucket)] = get_statement(storage[bucket])

    for bucket in update_bucket_statements:
        read = storage[bucket]['read']
        write = storage[bucket]['write']
        old_read = storage_table[bucket]['read']
        old_write = storage_table[bucket]['write']

        if not read and write:
            print('You cannot remove read permissions and stil have write permissions, it is not supported in the '+project_name+' for bucket <<'+bucket+'>>. No changes applied')
            storage[bucket] = storage_table[bucket]
            continue

        bucket_name = format_bucket_name(bucket)
        actions = statements[bucket_name]['Action']

        if read != old_read:
            trigger_policy_update = True
            if read:
                actions.append('s3:Get*')
            else:
                actions.remove('s3:Get*')
        if write != old_write:
            trigger_policy_update = True
            if write:
                actions.append('s3:Put*')
                actions.append('s3:Delete*')
            else:
                actions.remove('s3:Put*')
                actions.remove('s3:Delete*')
        statements[bucket_name]['Action'] = actions

    if trigger_policy_update:
        fmt_statements = list(statements.values())
        new_policy = {
            "Version": "2012-10-17",
            "Statement": fmt_statements
        }

        try:
            response_create = iam_client.create_policy_version(
                PolicyArn=policy_arn,
                PolicyDocument=json.dumps(new_policy),
                SetAsDefault=True
            )

            response_list = iam_client.list_policy_versions(PolicyArn=policy_arn)

            # After create the new policy make sure to delete the old ones, since you cannot have more than five
            versions = response_list['Versions']
            for v in versions:
                if not v['IsDefaultVersion']:
                    response = iam_client.delete_policy_version(
                        PolicyArn=policy_arn,
                        VersionId=v['VersionId']
                    )
            return list(storage.values())
        except Exception as e:
            print('Error in the policy for the project ' + project_name + ':' + str(e))
            return None
    return None

def get_statement(bucket):
    bucket_name = bucket['bucket']
    new_bucket_name = format_bucket_name(bucket_name)
    read = bucket['read']
    write = bucket['write']

    # By default the bucket and objects can be listed even when read: False and write: False
    statement = {
        "Sid": new_bucket_name,
        "Effect": "Allow",
        "Action": ["s3:List*"],
        "Resource": [
            "arn:aws:s3:::" + bucket_name,
            "arn:aws:s3:::" + bucket_name + "/*"
        ]
    }
    if not read and write:
            print('You cannot add read permissions and without write permissions, it is not supported in the for bucket '+bucket_name+'. Only list permissions applied')

    if read:
        statement['Action'].append("s3:Get*")
        if write:
            statement['Action'].append("s3:Put*")
            statement['Action'].append("s3:Delete*")
    return statement

def format_bucket_name(bucket_name):
    new_bucket_name = re.sub('[^a-zA-Z0-9 \n\.]', '', bucket_name)
    return new_bucket_name

def list_to_dict(_list, attribute='bucket'):
    return {_list[i][attribute]: _list[i] for i in range(len(_list))} 