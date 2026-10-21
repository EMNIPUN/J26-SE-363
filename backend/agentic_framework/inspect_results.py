import asyncio
from shared.queue import app

async def main():
    async with app.open_async():
        rows = await app.connector.execute_query_all_async(
            "SELECT student_id, sprint_id, mark, status, factors FROM perf_assessment_results ORDER BY updated_at DESC LIMIT 5"
        )
        for r in rows:
            print("STUDENT:", r["student_id"], "SPRINT:", r["sprint_id"], "MARK:", r["mark"], "STATUS:", r["status"])
            print("FACTORS:", r["factors"])
            print("---")

if __name__ == "__main__":
    asyncio.run(main())
