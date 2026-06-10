# Services
## API Gateway
- Handle SSL/TLS (https)
- route requests

## Auth Layer
- middleware for authentication
- Check/provide tokens
- Token consists of:
    - username
    - password_hashed
    - user_id
- Only checks if user is registered
(it never checks for specific roles)
URLs:
create user - POST /auth
login/logout - POST /login, POST /logout

*Bussines Logic*
# Project Service
- Get a request from the auth layer with the token
- It always check user roles
URLs:
Create a new project - POST /projects
Get projects - GET /projects
Get project details - GET /projects/<project_id>/info
Update a project - PUT /projects/<project_id>/info
Delete a project - DELETE /projects/<project_id>
Get documents - GET /projects/<project_id>/documents-
Grant access - POST /projects/<project_id>/invite?user=<login>

# Document Service
- Get a request from the auth layer with the token
- It always check user roles
- Checks document format
URLs
Upload document - POST /project/<project_id>/documents
Download document - GET /document/<document_id>
Update document - PUT /document/<document_id>
Delete document - DELETE /document/<document_id>

*DAO*
- S3 Controller
Upload, download, update, delete
- postgreSQL Controller (always checks if the user has access)
get user roles, by u_id
create a project, cascade operation, stored routine
get projects, by u_id
create new user
check u_pwd, by u_id
get project details, by p_id
update a project, by p_id
delete a project, by p_id, cascade operation
get documents, by p_id
change roles, by p_id

*DB*
S3 Storage
postgreSQL
