import asyncio
import json

from ..api.middleware.database import setup_connection

with open("app/local/muscles.json", "r") as file:
    muscle_groups_json = json.load(file)

async def insert_muscle_groups():
    try:
        conn = await setup_connection()

        await conn.execute(
            """
            delete from muscle_groups;
            """
        )

        for name, heads in muscle_groups_json.items():
            group_id = await conn.fetchval(
                """
                insert into muscle_groups
                (name)
                values
                ($1)
                returning id
                """, name
            )

            await insert_muscle_targets(conn, group_id, heads)

    except Exception as e:
        print(e)
    finally:
        if conn: await conn.close()

async def insert_muscle_targets(conn, group_id, heads):
    for head in heads:
        await conn.execute(
            """
            insert into muscle_targets
            (muscle_group_id, name)
            values
            ($1, $2)
            """, group_id, head
        )

async def main():
    await insert_muscle_groups()

if __name__ == "__main__":
    asyncio.run(main())