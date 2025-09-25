import asyncio
import json

from ..api.middleware.database import *

async def main():
    if input(f"Insert existing user data in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return

    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select id
            from users
            where is_verified = true;
            """
        )

        for row in rows:
           user_id = str(row["id"])
           await check_workout_totals(conn, user_id)
           await check_workout_muscle_group_totals(conn, user_id)
           await check_workout_muscle_target_totals(conn, user_id)

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

async def check_workout_totals(conn, user_id):
    exists = await conn.fetchval(
        """
        select exists (
            select 1
            from workout_totals
            where user_id = $1
        )
        """, user_id
    )
    if exists: return

    await conn.execute(
        """
        insert into workout_totals
        values
        ($1, 0.0, 0, 0, 0.0, 0, 0)
        """, user_id
    )

async def check_workout_muscle_group_totals(conn, user_id):
    group_id_rows = await conn.fetch(
        """
        select id
        from muscle_groups
        """
    )

    for group_id_row in group_id_rows:
        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from workout_muscle_group_totals
                where user_id = $1
                and muscle_group_id = $2
            )
            """, user_id, group_id_row["id"]
        )
        if exists: continue

        await conn.execute(
            """
            insert into workout_muscle_group_totals
            values
            ($1, $2, 0.0, 0, 0, 0, 0)
            """, user_id, group_id_row["id"]
        )

async def check_workout_muscle_target_totals(conn, user_id):
    target_id_rows = await conn.fetch(
        """
        select id
        from muscle_targets
        """
    )

    for target_id_row in target_id_rows:
        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from workout_muscle_target_totals
                where user_id = $1
                and muscle_target_id = $2
            )
            """, user_id, target_id_row["id"]
        )
        if exists: continue

        await conn.execute(
            """
            insert into workout_muscle_target_totals
            values
            ($1, $2, 0.0, 0, 0, 0, 0)
            """, user_id, target_id_row["id"]
        )

if __name__ == "__main__":
    asyncio.run(main())