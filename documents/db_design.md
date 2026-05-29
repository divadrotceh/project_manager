# DataBase Design
## Info-logical design
### Defining:
1. Entities
2. Attributes
3. Comments

### Entities
* User
* Project
* Document
* Project Access / Membership (Association relation)

### Entity/Attributes
#### User
* Username -> username (NOT NUL, UNIQUE)
* Password -> password (NOT NULL)
* User ID: <PK> -> user_id (auto, UNIQUE, NOT NULL)

#### Project
* Project Name -> project_name (UNIQUE, NOT NULL)
* Project Description -> project_description
* Project ID <PK> -> project_id (UNIQUE, auto, NOT NULL)

#### Document (S3)
* Project ID
* Object

#### Project Access / Membership (Association relation - User & Project)
* Project ID -> project_id (<PfK>)
* User ID -> user_id (<PfK>)
* Role -> role (USER | ADMINISTRATOR)

## Data-logical design
### Defining
1. DBMS Conventions
    DBMS Type
    particular DBMS
    minimal DBMS version
    DBMS infrastructure details
2. Naming conventions
    Structures naming
    SQL code formating
    Comments principles
    Other specifics
3. Table Description
    Database table
    Database table fields
    Data type
    Comments

