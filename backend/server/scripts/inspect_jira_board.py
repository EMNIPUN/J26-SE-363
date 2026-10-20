"""Read-only inspection of the configured Jira issue types and board filter."""
import asyncio
import json

from app.modules.planning.jira_service import get_jira_client


async def main():
    client = get_jira_client()
    project = await client.get_project()
    print(json.dumps({"project_key": project.get("key"), "project_type": project.get("projectTypeKey"), "style": project.get("style"), "simplified": project.get("simplified")}))
    board_id = await client.discover_board_id()
    print(json.dumps({"board_id": board_id, "issue_types": await client.get_issue_types()}))
    async with client._client() as http:
        response = await http.get(f"/rest/agile/1.0/board/{board_id}/configuration")
        response.raise_for_status()
        data = response.json()
        print(json.dumps({"columns": data.get("columnConfig"), "filter": data.get("filter")}))
        filter_id = (data.get("filter") or {}).get("id")
        if filter_id:
            response = await http.get(f"/rest/api/3/filter/{filter_id}")
            print(json.dumps({"filter_status": response.status_code, "jql": response.json().get("jql")}))


if __name__ == "__main__":
    asyncio.run(main())
