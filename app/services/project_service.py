from fastapi import fastapi
from fastapi import APIRouter, HTTPException, status
from typing import List
from dao.postgresql_controller import postgresql_controller

router = APIRouter(prefix="/projects", tags=["projects"])


# Create a new project
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_project(project_data: dict):
    """Create a new project"""
    try:
        result = postgresql_controller.create_project(project_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Get all projects
@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_projects():
    """Get all projects"""
    try:
        projects = postgresql_controller.get_all_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Get project by ID
@router.get("/{project_id}/info", status_code=status.HTTP_200_OK)
async def get_project_by_id(project_id: int):
    """Get a specific project by ID"""
    try:
        project = postgresql_controller.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return project
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# Update a project
@router.put("/{project_id}/info", status_code=status.HTTP_200_OK)
async def update_project(project_id: int, project_data: dict):
    """Update an existing project"""
    try:
        result = postgresql_controller.update_project(project_id, project_data)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Delete a project
@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project_id: int):
    """Delete a project"""
    try:
        result = postgresql_controller.delete_project(project_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{project_id}/documents", status_code=status.HTTP_200_OK)
async def get_documents_by_project_id(project_id: int):
    """Get documents associated with a specific project by ID"""
    try:
        documents = postgresql_controller.get_documents_by_project_id(project_id)
        if not documents:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No documents found for this project")
        return documents
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/{project_id}/documents", status_code=status.HTTP_201_CREATED)
async def upload_document_to_project(project_id: int, document_data: dict):
    """Upload a document to a specific project"""
    try:
        result = postgresql_controller.upload_document_to_project(project_id, document_data)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or unable to upload document")
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{project_id}/invite?user_id={user_id}", status_code=status.HTTP_201_CREATED)
async def grant_access_to_project(project_id: int, user_id: int):
    """Grant access to a specific project for a user"""
    try:
        result = postgresql_controller.grant_access_to_project(project_id, user_id)
        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project or user not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
