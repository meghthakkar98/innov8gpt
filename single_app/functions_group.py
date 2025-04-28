# functions_group.py

from config import *
from functions_authentication import *
from functions_settings import *


def create_group(name, description):
    """Creates a new group. The creator is the Owner by default.
    Checks if a group with the same name already exists."""
    user_info = get_current_user_info()
    if not user_info:
        raise Exception("No user in session")

    # Check if a group with the same name already exists
    query = """
        SELECT VALUE COUNT(1)
        FROM c
        WHERE LOWER(c.name) = LOWER(@name)
    """
    params = [{"name": "@name", "value": name}]
    
    results = list(groups_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    
    # If count is greater than 0, a group with this name already exists
    if results and results[0] > 0:
        raise Exception("A group with this name already exists. Please choose a different name.")

    new_group_id = str(uuid.uuid4())
    now_str = datetime.utcnow().isoformat()

    group_doc = {
        "id": new_group_id,
        "name": name,
        "description": description,
        "owner":
            {
                "id": user_info["userId"],
                "email": user_info["email"],
                "displayName": user_info["displayName"]
            },
        "admins": [],
        "documentManagers": [],
        "users": [
            {
                "userId": user_info["userId"],
                "email": user_info["email"],
                "displayName": user_info["displayName"]
            }
        ],
        "pendingUsers": [],
        "createdDate": now_str,
        "modifiedDate": now_str
    }
    groups_container.create_item(group_doc)
    return group_doc

def search_groups(search_query, user_id):
    """
    Return a list of groups the user is in or (optionally)
    you can expand to also return public groups. 
    For simplicity, this only returns groups where the user is a member.
    """
    query = query = """
        SELECT *
        FROM c
        WHERE EXISTS (
            SELECT VALUE u
            FROM u IN c.users
            WHERE u.userId = @user_id
        )
    """

    params = [
        { "name": "@user_id", "value": user_id }
    ]
    if search_query:
        query += " AND CONTAINS(c.name, @search) "
        params.append({"name": "@search", "value": search_query})

    results = list(groups_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    return results

def get_user_groups(user_id):
    """
    Fetch all groups for which this user is a member.
    """
    query = query = """
        SELECT *
        FROM c
        WHERE EXISTS (
            SELECT VALUE x
            FROM x IN c.users
            WHERE x.userId = @user_id
        )
    """

    params = [{ "name": "@user_id", "value": user_id }]
    results = list(groups_container.query_items(
        query=query,
        parameters=params,
        enable_cross_partition_query=True
    ))
    return results

def find_group_by_id(group_id):
    """Retrieve a single group doc by its ID."""
    try:
        group_doc = groups_container.read_item(
            item=group_id,
            partition_key=group_id
        )
        return group_doc
    except exceptions.CosmosResourceNotFoundError:
        return None

def update_active_group_for_user(user_id, group_id):
    new_settings = {
        "settings": {
            "activeGroupOid": group_id
        },
        "lastUpdated": datetime.utcnow().isoformat()
    }
    update_user_settings(user_id, new_settings)

def get_user_role_in_group(group_doc, user_id):
    """Determine the user's role in the given group doc."""
    if not group_doc:
        return None

    if group_doc.get("owner", {}).get("id") == user_id:
        return "Owner"
    elif user_id in group_doc.get("admins", []):
        return "Admin"
    elif user_id in group_doc.get("documentManagers", []):
        return "DocumentManager"
    else:
        for u in group_doc.get("users", []):
            if u["userId"] == user_id:
                return "User"

    return None


def map_group_list_for_frontend(groups, current_user_id):
    """
    Utility to produce a simplified list of group data
    for the front-end, including userRole and isActive.
    """
    active_group_id = session.get("active_group")
    response = []
    for g in groups:
        role = get_user_role_in_group(g, current_user_id)
        response.append({
            "id": g["id"],
            "name": g["name"],
            "description": g.get("description", ""),
            "userRole": role,
            "isActive": (g["id"] == active_group_id)
        })
    return response

def delete_group(group_id):
    """
    Deletes a group from Cosmos DB. Typically only owner can do this.
    """
    groups_container.delete_item(item=group_id, partition_key=group_id)

def is_user_in_group(group_doc, user_id):
    """
    Helper to check if a user is in the given group's users[] or is the owner.
    """
    if group_doc.get("owner", {}).get("id") == user_id:
        return True

    for u in group_doc.get("users", []):
        if u["userId"] == user_id:
            return True
    return False