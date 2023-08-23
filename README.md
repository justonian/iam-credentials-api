
# Welcome to your IAM Credentials API project.

## Project overview

This project deploys an IAM assume-role service for integration with SLURM jobs. It uses a project ID passed in the session creation API to look up the appropriate project-aligned IAM role and return IAM temporary role credentials (access key, secret access key, and session token) using the ECS container credentials provider features built into the AWS CLI and SDKs.

To enable transparent integration to any existing jobs that use the AWS CLI or SDK, you must run a localhost proxy to forward any calls made to a localhost listener service on the compute/worker nodes to the credentials vending API.

## API overview

* **/sessions (POST)** - Create a new session/job. Exclusively for use by SLURM head node  
* **/sessions/{sessionId} (PUT)** - Update an existing session. Exclusively for use by SLURM head node  
* **/sessions/{sessionId}/cluster/{clusterId}/project/{projectId}?roleSessionName={roleSessionName} (GET)** - Retrieves IAM role credentails with access key, secret access key, and session token. Used by all compute/worker nodes running a given job/session.
* **/sessions/users/{userId} (DELETE)** - Invalidate all active sessions for specified user, and revoke all existing IAM credentials issued to user's sessions.

Additional methods and paths to be added shortly, such as revocation paths.
 
## CDK Overview

This project uses the AWS Cloud Development Kit (CDK) to deploy this app.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

Note: installing python dependencies requires docker to be installed and running.

### New account setup

Whenever deploying this solution to a new account for the first time, run CDK bootstrap to setup the needed S3 bucket and infrastructure
```
$ cdk bootstrap
```

### Regular deployments

To deploy any changes to the environment, run cdk deploy which will deploy the stack. For subsequent deployments, a CloudFormation Change Set is created which will only the changed template resources. All stack resources include the env variable.

To install and/or update the stack resources:

```
$ cdk deploy -c env=Dev
```

To destroy/uninstall the stack, specify -c env=Dev or the environment name that will be destroyed
```
$ cdk destroy -c env=Dev
```

### Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

## Installation instructions

### Boostrap and deploy the API

1. First bootstrap the CDK project if using a new account (each account only needs bootstrapping one time)
2. Next, deploy the CDK project by using **_cdk deploy -c env=Dev_** 
*Change the env variable to any value desired. Ex. dev, test, prod*
3. Browse to the AWS CloudFormation console.
4. Check the stack outputs for the DynamoDB role mapping table name, Lambda execution role, and API Gateway deployed endpoint. Save these values locally for later use.

### Per-project IAM role creation

5. Next create one IAM role for each SLURM project ID planned for use with the credentials API. using a custom trust policy for each IAM role that enables the Lambda function's execution role as the only trusted entity to assume the newly created role(s). The trust policy should look similar to the following:

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "Statement1",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::554161763323:role/IamApiDev-GetCredentialsServiceRole...YOUR_ROLE_ARN"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```
### Populating the DynamoDB Role Mapping table

6. Browse to the DynamoDB role mapping table that was specified in the CloudFormation stack outputs.
7. Manually populate this table one item for each SLURM project ID. The items should use ProjectId as the partition key and have an attribute called RoleArn. These are case sensititve attributes.

### Establish the head node secret for head node API authentication

8. Browse to the Secrets Manager console and find the head node secret
9. Select the head node secret and choose to "Retrieve secret value"
10. You can now Edit to include your customzied secret specific to head node or copy the existing auto-generated secret and provide to the head node in a secure way.
11. Whichever secret you choose, save the secret and popuate the secret on the head node for use when authenticating to the head node.

*Note: This is a temporary PoC setup and the head node authentication should ideally be hardened to use IAM-based authorization or time-limited bearer tokens (OAuth flows) as a more secure approach for a productioin installation.*

### Setting up SLURM head node integration

12. The SLURM head node should invoke the **/sessions** POST method upon job/session creation.

The head node secret token should be sent in the Authorization header.

Request body should include the following payload attributes:

{
    "sessionId": "1300",
    "projectId": "abc",
    "clusterName": "alpha",
    "clusterUser": "user1"
    "submittedTime": "2023-08-15T00:00:00"
}

8. The SLURM head node should invoke the **/sessions/{sessionId}** PUT method upon job/session completion or failure. Only the job/session status can be set. Valid session statuses include ACTIVE, INVALIDATED, and COMPLETED.

{
    "status": "ACTIVE"
}

The head node secret token should also be sent in the Authorization header.

### Setting up the compute/worker nodes

#### Configure compute/worker node localhost credentials API proxy

13. Since the AWS CLIs and SDKs only allow retrieving credentials from localhost and a 169... IP address, you next need to install a localhost proxy service. Copy the localhost_proxy.py file to each compute worker node and setup a persistent process to launch this service at boot of each instance.

```
python3 localhost_proxy.py --hostname 'your_api_endpoint_here' --cache_mode=store
```
You should not include any path beyond the hostname, so be sure to exclude the stage name such as /prod. The default endpoint when not specified is t7b9p81x86.execute-api.us-east-1.amazonaws.com.

##### Configure local credentials cache

There are two flags that configure the localhost proxy credentials cache behavior:

* Set **cache_mode=store** to enable the local credentials cache. This is the default beahvior if not specified.
* The max amount of items to be stored can be configured with **max_queue_size** flag, which defaults to 1000000. Items beyond this point will be evicted based on cache item age and which are the oldest items in the cache.

### Configure the CLI or AWS SDKs

14. If the compute/worker nodes are running jobs on an EC2 instance without an instance profile (ex. an EC2 instance without an IAM role associated during launch), then the AWS CLI and SDKs should auto-discover the ECS credential provider when it searches for credentials and locates the named environmental variables indicating where to query for credentials.

If you are using an instance with an existing IAM role at the EC2 instance level, then it is necessary to explicitly set the AWS CLI to use the ECS container credentials provider so it searches the environmental variables and the credentials take precedence over the EC2 instance profile or role credentials.

Configure your AWS config file (found at ~/.aws/config) to include credential_source set to EcsContainer. If using the AWS CLI, you can use the command aws configure set default.credential_source EcsContainer to set this value.

```
[default]
region = us-west-2
output = json
credential_source = EcsContainer
```

Additionally, a new profile can be created with *aws configure* not specifying any credentials which will automatically detect and use the IAM Credentials API credentials.

Be sure that no other access key credentials are set for the profile in the ~/.aws/credentials file. Only the config file is needed so if ~/.aws/credentials does not exist, the credential authentication flow should still work as expected.

### Integrate compute/worker nodes with Credentials API

15. In response to the head node creating a new job/session, the following payload (with different values) will be returned.

```
{
    "APIGATEWAY_AWS_CONTAINER_CREDENTIALS_FULL_URI": "https://uwulcdei61.execute-api.us-east-1.amazonaws.com/prod/sessions/1321/cluster/alpha/project/abc",
    "LOCALHOST_AWS_CONTAINER_CREDENTIALS_FULL_URI": "http://localhost:9999/prod/sessions/1321/cluster/alpha/project/abc",
    "AWS_CONTAINER_AUTHORIZATION_TOKEN": "c8f16d73-7152-43a8-97fc-14f2575308fb"
}
```
**As part of the setup on each compute/worker node, you will need to append an additional query string parameter *roleSessionName* value to the end of the LOCALHOST_AWS_CONTAINER_CREDENTIALS_FULL_URI.** This will ensure each node uses a unique IAM role session name to better track audit history of each node's activity. This is used as the IAM role session name allowing activity logging, auditing, and revocation for a specific cluster node.

*To fully support all revocation scenarios, the roleSessionName string is recommended to be the following structure: clusterName-userId-clusterNodeId.*

Set the following two variables on each of the worker nodes:

AWS_CONTAINER_CREDENTIALS_FULL_URI="http://localhost:9999/sessions/11100/cluster/alpha/project/abc?roleSessionName=clusterName-userId-clusterNodeId"

*You should always use the localhost API endpoint provided in the return response from the creation session call along with the appended cluster node ID query string parameter.*

AWS_CONTAINER_AUTHORIZATION_TOKEN="6c2ccc8a-b039-481e-80b7-82e6116e1497"

*You should set the session token sent in response to the create session as this value.*

More details on the significance of these variables and how they're used with the ECS Container credentials provider can be found at https://docs.aws.amazon.com/sdkref/latest/guide/feature-container-credentials.html. Both of these values should remain constant for each node while a specific job/session is running.

16. Test the job/session dynamic credentials gathering by running a CLI command such as 'aws sts get-caller-identity' to confirm which identity is being used for CLI calls.

These IAM credentials are dynamic and provided through IAM role chaining where the Lambda function assumes the role and passes back the credentials.