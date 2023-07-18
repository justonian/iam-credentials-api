
# Welcome to your IAM Credentials API project.

## Project overview

This project deploys an IAM assume-role service for integration with SLURM jobs. It uses a project ID passed in the session creation API to look up the appropriate IAM role and return IAM temporary role credentials (access key, secret access key, and session token) using the ECS container credentials provider features built into the AWS CLI and SDKs.

To enable transparent integration to any existing jobs that use the AWS CLI or SDK, you must run a localhost proxy to forward any calls made to a local listener service on the compute/worker nodes to the credentials vending API.

## API overview

* **/sessions (POST)** - Create a new session/job. Exclusively for use by SLURM head node  
* **/sessions/{sessionId} (PUT)** - Update an existing session. Exclusively for use by SLURM head node  
* **/sessions/{sessionId}/cluster/{clusterId}/project/{projectId}/clusterNode/{clusterNodeId} (GET)** - Retrieves IAM role credentails with access key, secret access key, and session token. Used by all compute/worker nodes running a given job/session.

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

### New account setup

Whenever deploying this solution to a new account for the first time, run CDK bootstrap to setup the needed S3 bucket and infrastructure
```
$ cdk bootstrap
```

### Regular deployments

To deploy any changes to the environment, run cdk deploy which will deploy only the changed template resources.
```
$ cdk deploy
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
2. Next, deploy the CDK project by using **_cdk deploy_**
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
                "AWS": "arn:aws:iam::1234567890:role/IamCredentialsApiStack-GetCredentialsServiceRole52-1U1JLE"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
```
### Populating the DynamoDB Role Mapping table

5. Browse to the DynamoDB role mapping table that was specified in the CloudFormation stack outputs.
6. Manually populate this table one item for each SLURM project ID. The items should use projectID as the partition key and have an attribute called roleArn. These are case sensititve attributes.

### Setting up SLURM head node integration

7. The SLURM head node should invoke the **/sessions** POST method upon job/session creation.

The head node secret token should be sent in the Authorization header.

Request body should include the following payload attributes:

{
    "sessionId": "1300",
    "projectId": "abc",
    "clusterName": "alpha",
    "clusterUser": "user1"
}

8. The SLURM head node should invoke the **/sessions/{sessionId}** PUT method upon job/session completion or failure. Only the job/session status can be set. Valid session statuses include ACTIVE and COMPLETED.

{
    "status": "ACTIVE"
}

The head node secret token should be sent in the Authorization header.


### Setting up the compute/worker nodes

7. Since the AWS CLIs and SDKs only allow retrieving credentials from Localhost and a 169... IP address, you next need to install a localhost proxy service. Copy localhost_proxy.py to each compute worker node and setup a persistent process to launch this service at boot of each instance.

```
python localhost_proxy.py --host 'your_api_endpoint_here' 
```
You should include any path beyond the hostname, including the /prod. The default endpoint when not specified is t7b9p81x86.execute-api.us-east-1.amazonaws.com.