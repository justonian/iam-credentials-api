from locust import HttpUser, task, between
import uuid


creds = []
class GetCredentials(HttpUser):
    wait_time = between(0.1, 0.2)  # Adjust the wait time between requests


    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_0(self):
        c = creds[0]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })


    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_1(self):
        c = creds[1]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_2(self):
        c = creds[2]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_3(self):
        c = creds[3]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_4(self):
        c = creds[4]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_5(self):
        c = creds[5]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_6(self):
        c = creds[6]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_7(self):
        c = creds[7]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_8(self):
        c = creds[8]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })


    @task(6)  # Adjust the weight (6 here means it will be 6 times more frequent than weight 1)
    def request_type_(self):
        c = creds[9]
        self.client.get("/prod/sessions/"+c["sessionId"]+"/cluster/" + c["clusterName"] + "/project/" + c["projectId"] + "?clusterNodeId=2345", headers={
            "Authorization": c["body"]["AWS_CONTAINER_AUTHORIZATION_TOKEN"]
        })

    def on_start(self):
        project_ids = ["00010","00011","00012","00013","00014","00015","00016","00017","1234","12345"]
        for i in range(10):
            for j in range(2):
                session_id = str(uuid.uuid4())
                cluster_name = project_ids[i] + "-" + str(j)
                res = self.client.post("https://udz1dq0ne9.execute-api.us-east-1.amazonaws.com/prod/sessions",
                    headers={"Authorization": '!LwCzc0",y=;3\Jf`*n!!7+#c,xVAA1s'}, json={
                    "sessionId": session_id,
                    "projectId": project_ids[i],
                    "clusterName": cluster_name,
                    "clusterUser": "user"
                })
                print(res)
                if res.status_code != 200:
                    raise Exception("Could not create creds")
                creds.append({
                    "body": res.json(),
                    "projectId": project_ids[i],
                    "sessionId": session_id,
                    "clusterName": cluster_name
                })
        print(creds)