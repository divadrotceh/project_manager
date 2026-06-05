# Project Manager App
## Apendix:
1. Executive Summary
2. Requirements
3. High-Level Architecture Diagram
4. Technology Stack
5. Data Model
6. Authentication & Authorization
7. API Design
8. Deployment Diagram
9. Architectural Decisions

## Executive Summary
Project Management/profiles dashboard.
A service to create, update, share, and delete projects information (details, attached
documents).

## Requirements
1. User login/auth
2. Create/Delete projects
3. Add/Update project’s info/details - name, description
4. Add/Update/Remove projects documents (docx, pdf)
5. Share project with other users to access

## High-level Architecture Diagram
```mermaid
flowchart TB
 subgraph s1["Business Logic"]
        n4["Project Service"]
        n8["Document Service"]
  end
 subgraph s2["Data Access Layer"]
        n12["S3 Controller"]
        n13["PostgreSQL Controller"]
  end
    n1(["User"]) --> n2["API Gateway Layer"]
    n2 --> n3["Auth Layer"]
    s1 --> s2
    s2 --> n7["S3 Storage"] & n5["PostgreSQL"]
    n3 --> s1

    n4@{ shape: proc}
    n8@{ shape: proc}
    n11@{ shape: proc}
    n12@{ shape: proc}
    n13@{ shape: proc}
    n2@{ shape: proc}
    n3@{ shape: proc}
    n6@{ shape: db}
    n7@{ shape: db}
    n5@{ shape: db}
     n4:::businessLogic
     n8:::businessLogic
     n11:::dataAccess
     n12:::dataAccess
     n13:::dataAccess
     n2:::gateway
     n3:::gateway
     n6:::storage
     n7:::storage
     n5:::storage
```

### Request Flow
1. User sends HTTPS request
|
v
2. API Gateway receives the request
|
v
3. Authentication Layer
- Validates JWT token
- Authenticates user
- Extracts user claims
|
v
4. Request is routed to the corresponding service
- Project Service
- Document Service
|
v
5. Service executes business rules
|
v
6. Service accesses required storage through
the Data Access Layer
|
+--> PostgreSQL
|
+--> Key-Value Storage
|
+--> S3 Storage
|
v
7. Data is returned to the service
|
v
8. Service builds response
|
v
9. Response flows back through:
Service -> Gateway -> User

### Component Responsibilities
| Layer | Responsibility |
|--------|---------------|
| User | Consumes the application |
| API Gateway | Entry point, routing, HTTPS handler |
| Authentication Layer | User authentication, JWT validation, identity extraction |
| Project Service | Project management business rules |
| Document Service | Document management, upload, retrieval, processing |
| Data Access Layer | Abstracts persistence technologies from business services |
| PostgreSQL Adapter | Relational data access |
| Key/Value Adapter | Project documents quick access |
| S3 Controller | Object storage integration |
| PostgreSQL | Structured persistent data |
| Key-Value Storage | High-performance non-relational storage |
| S3 Storage | Document and file storage |

## Technology Stack
- Python 3.12+
- FastAPI
- PostgreSQL +Optional ORM (SQLAlchemy)
- Docker
- AWS S3 (file storage)
- AWS lambda functions (for image processing, size calculations on s3 event)
- CI/CD Github Actions/Gitlab CI (testing/linting/building/pushing to registry/deploy to
cloud on merge request)

## Data Model
PostgreSQL DB -
Stores relational data from users, projects, roles and document's metadata. It maintains strong consistency, strict
schema and ensures data integrity
AWS S3 -
For document storage.
Documents will be stored as objects, adding support for multiple formats along with its
metadata. Documents will be assigned to buckets and each bucket will be a project.

```mermaid
erDiagram
project ||--|{ access : has
project {
    bigint p_id PK "id, not null, unique"
    text p_name "not null, unique"
    text p_description
}
user ||--|{ access : has
user {
    bigint u_id PK "id, not null, unique"
    text u_name "not null, unique"
    text u_pwd  "not null"
}
access {
    bigint p_id PK "foreign key, not null"
    bigint u_id PK "foreign key, not null"
    text role "not null"
}
document }|--|| project : has
document {
    bigint d_id PK "not null, unique"
    bigint p_id PK "foreign key, not null"
    text d_s3key "not null"
    text d_mime "not null"
}
```

## Authentication & Authorization
### Authentication Flow

User
|
Login
|
Auth Service
|
JWT Token

### Authorization

- Roles:
User
Admin

- Permissions
| Action | User | Admin |
|---------|------|-------|
| Create/Delete Projects | No | Yes |
| Add/Update Project Information and Details | Yes | Yes |
| Add/Update/Remove Project Documents | Yes | Yes |
| Share Project with Other Users | No | Yes |

API Design
1. 2. 3. 4. 5. 6. 7. 8. 9. 10. 11. 12. 
1. POST /auth - Create user (login, password, repeat password)
2. POST /login - Login into service (login, password)
3. POST /projects - Create project from details (name, description). Automatically gives access to
    created project to user, making him the owner (admin of the project).
4. GET /projects - Get all projects, accessible for a user. Returns list of projects full info(details +
    documents).
5. GET /project/<project_id>/info - Return project’s details, if user has access
6. PUT /project/<project_id>/info - Update projects details - name, description. Returns the updated
    project’s info
7. DELETE /project/<project_id>- Delete project, can only be performed by the projects’ owner.
    Deletes the corresponding documents
8. GET /project/<project_id>/documents- Return all of the project's documents
9. POST /project/<project_id>/documents - Upload document/documents for a specific project
10. GET /document/<document_id> - Download document, if the user has access to the corresponding
    project
11. ** PUT /document/<document_id> - Update document
12. DELETE /document/<document_id> - Delete document and remove it from the corresponding
    project
13. POST /project/<project_id>/invite?user=<login> - Grant access to the project for a specific user.
    If the request is not coming from the owner of the project, results in error. Granting access gives
    participant permissions to receiving user

User and Project flows
```mermaid
flowchart TB
subgraph fig2["Figure 2 - User and Project Flows"]
    b4(("Create User")) --> b9["API Gateway"]
    b9 <--> b1["Auth Layer"]
    b9 --> b10["Token + Home Page"]
    b1 <--> b2["PostgreSQL Controller"]
    b2 <--> b3["PostgreSQL DB"]
    b5(("Login")) --> b8["API Gateway"]
    b8 <--> b6["Auth Layer"]
    b8 --> b11["Token + Home Page"]
    b6 <--> b7["PostgreSQL Controller"]
    b7 <--> b42["PostgreSQL DB"]
    b12(("New Project")) --> b13["API Gateway/Auth Layer"]
    b13 <--> b14["Project Service"]
    b13 --> b18["Confirmation + Home Page"]
    b14 <--> b17["PostgreSQL Controller"]
    b17 <--> b46["PostgreSQL DB"]
    b19(("Get Projects")) --> b20["API Gateway"]
    b20 <--> b21["Auth Layer"]
    b20 --> b43[Projects List]
    b21 <--> b22["Project Service"]
    b22 <--> b23["PostgreSQL Controller"]
    b23 <--> b25["PostgreSQL DB"]
    b27(("Project Details")) --> b28["API Gateway"]
    b28 <--> b29["Auth Layer"]
    b28 --> b44[Projects Details]
    b29 <--> b30["Project Service"]
    b30 <--> b31["PostgreSQL Controller"]
    b31 <--> b33["PostgreSQL DB"]
    b35(("Update project")) --> b36["API Gateway"]
    b36 <--> b37["Auth Layer"]
    b36 --> b45["Confirmation + Home Page"]
    b37 <--> b38["Project Service"] 
    b38 <--> b39["PostgreSQL Controller"]
    b39 <--> b40["PostgreSQL DB"]
  end
```

Document and Access Flows
```mermaid
flowchart TB
  subgraph fig1["Figure 1 - Document and Access Flows"]
    a1(("Delete Project")) --> a2["API Gateway"]
    a2 <--> a3["Auth Layer"]
    a2 --> a48["Confirmation + Home Page"]
    a3 <--> a4["Project Service"]
    a4 <--> a5["S3 Controller"] & a7["PostgreSQL Controller"]
    a9(("Get Documents")) --> a10["API Gateway"]
    a10 <--> a11["Auth Layer"]
    a11 <--> a12["Project Service"]
    a12 <--> a13["postgreSQL Controller"]
    a13 <--> a49["postgreSQL DB"]
    a10 --> a14["List"]
    a15(("Upload Document")) --> a16["API Gateway"]
    a16 <--> a17["Auth Layer"]
    a16 --> a25["Confirmation + Home Page"]
    a17 <--> a18["Document Service"]
    a18 <--> a19["S3 Controller"] & a20["postgreSQL Controller"]
    a21(("Download Document")) --> a22["API Gateway"]
    a22 <--> a23["Auth Layer"]
    a22 --> a50["file"]
    a23 <--> a24["Document Service"]
    a24 <--> a26["S3 Controller"]
    a26 <--> a27["S3 DB"]
    a28(("Update Document")) --> a29["API Gateway"]
    a29 <--> a30["Auth Layer"]
    a30 <--> a31["Document Service"]
    a31 <--> a32["S3 Controller"] & a53["postgreSQL Controller"]
    a32 <--> a51[S3 DB]
    a53 <--> a54[postgreSQL DB]
    a29 --> a33["Confirmation + Home Page"]
    a34(("Delete Document")) --> a35["API Gateway"]
    a35 <--> a36["Auth Layer"]
    a35 --> a41["Confirmation + Home Page"]
    a36 <--> a37["Document Service"]
    a37 <--> a38["S3 Controller"] & a40["postgreSQL Controller"]
    a42(("Grant Access")) --> a43["API Gateway"]
    a43 <--> a44["Auth Layer"]
    a44 <--> a45["Project Service"]
    a45 <--> a46["PostgreSQL Controller"]
    a43 --> a52["Confirmation + Home Page"]
  end
```

## Deployment Diagram
Following the 3 layer style
⁃ Data Access Object
⁃ Models
⁃ Routes
⁃ Services
⁃ main.py

### Folder Structure
project_manager/
│
|── app/
│ |── main.py
│ |── services/
│ |── models/
| |── routes/
│ └── dao/
│—— documents/
│
|── Dockerfile
|── docker-compose.yml
|── .env
|── .gitignore
|── README.md

The application will run in a single container, as it will be deployed as monolithic.
The internal architecture is designed as separated blocks for future service
extraction in case the application grows and one service becomes a bottleneck.

### Container Diagram

Internet
|
API Gateway
|
+———————————+
| FastAPI Application |
|——————————— |
| Project Module |
| Document Module |
| Authentication Module |
+———————————+
|
+ —> PostgreSQL
+ —> key/value
+ —> S3

## Security Considerations
OAuth2 -
Used for Authorization standard flow, allows easy extraction of authentication headers from
requests and use of tokens with a expiration time. The Authentication module is the owner for
this entire process.
JWT -
Used to encrypt the authorization data for OAuth2 processes. It is easy to implement in
FastAPI allowing fast extraction from the same container instead of checking user identity on
every request.
DB Security -
Every DBMS will its own layer of security, only specific roles can do certain type of actions.
NGINX -
Used for HTTPS decoding/encoding. HTTPS avoids external users intercept or stole critical
information with SSL/TLS certificates.