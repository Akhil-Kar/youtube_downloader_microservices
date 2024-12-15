#### Register Api

curl -X POST http://127.0.0.1:5001/api/register \
     -H "Content-Type: application/json" \
     -d '{"username": "user1", "password": "password123"}'


{
  "message": "User created successfully!"
}


#### Login Api

curl -X POST http://127.0.0.1:5001/api/login \
     -H "Content-Type: application/json" \
     -d '{"username": "user1", "password": "password123"}'


{
  "token": "<JWT_TOKEN>"
}


#### Protected Api

curl -X GET http://127.0.0.1:5001/api/protected \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxLCJleHAiOjE3MzM2NzM3MDZ9.clRpYmhDGcQloPOPAOiVfvxwYs2g_YC1KsG9z6cjiAI"


{
  "message": "Hello, user1"
}


#### Validate Api

curl -X POST http://127.0.0.1:5000/api/validate \
     -H "Content-Type: application/json" \
     -d '{"token": "<JWT_TOKEN>"}'


{
  "message": "Token is valid!",
  "user": "user1"
}

{
  "message": "Token is invalid!"
}
