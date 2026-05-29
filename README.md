# project_manager
This is a manager app to track files from different projects for authorized users only.
# Internal Architecture
## 3 layers
1. Data Access Object
2. Models
3. Routes
4. Services

root
|
|-dao / postgreSQL functions for DB manipulation
    |- user_dao.py
    |- project_dao.py
    |- document_dao.py
    |- access_dao.py
|-models / Models defined for specific DB entities 
    |- user_model.py
    |- project_model.py
    |- document_model.py
    |- access_dao.py
|-routes / Endpoint exposed to the user
    |- auth.py
    |- project_routes.py
|-services / Busines logic for all the app functions
    |- project_service.py
    |- document_service.py
|-main.py

Flow Example:
Client request -> [Routes] -> [Services] -> [Models] -> [Services] -> [DAO]

- Client make a request and arrives to PROXY Server.
- Routes direct the request to a specific service.
- Service extract the specific model to manipulate.
- Service uses a function of DAO to manipulate data.
