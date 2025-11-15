import asyncio
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
 
from ..api.middleware.database import *

load_dotenv(override=True)

async def main():
    if input(f"Insert existing user data in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return
    await check_totals()

async def check_totals():
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
            await check_exercise_totals(conn, user_id)
            # todo use new methods with redis
            # await check_overall_leaderboards(conn, user_id)

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
            ($1, $2, 0.0, 0, 0, 0)
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
            ($1, $2, 0.0, 0, 0, 0)
            """, user_id, target_id_row["id"]
        )

async def check_exercise_totals(conn, user_id):
    exercise_id_rows = await conn.fetch(
        """
        select id
        from exercises
        """
    )
    for exercise_id_row in exercise_id_rows:
        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from exercise_totals
                where user_id = $1
                and exercise_id = $2
            )
            """, user_id, exercise_id_row["id"]
        )
        if exists: continue

        await conn.execute(
            """
            insert into exercise_totals
            (user_id, exercise_id, volume, num_sets, reps, counter)
            values
            ($1, $2, 0.0, 0, 0, 0)
            """, user_id, exercise_id_row["id"]
        )

# async def check_overall_leaderboards(conn, user_id):
#     for table in ["volume", "sets", "reps"]:
#         column = table if table != "sets" else "num_sets"
#         exists = await conn.fetchval(
#             f"""
#             select exists (
#                 select 1
#                 from {table}_leaderboard
#                 where user_id = $1
#             )
#             """, user_id
#         )
#         if exists: continue

#         await conn.execute(
#             f"""
#             insert into {table}_leaderboard
#             (user_id, {column}, last_updated)
#             values
#             ($1, $2, $3)
#             """, user_id, 0.0, datetime.now(tz=timezone.utc).replace(tzinfo=None)
#         )

if __name__ == "__main__":
    asyncio.run(main())