import asyncio
import json

from ..api.middleware.database import setup_connection

with open("app/local/muscles.json", "r") as file:
    muscle_groups_json = json.load(file)

with open("app/local/exercises.json", "r") as file:
    exercises_json = json.load(file)

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

async def insert_exercises():
    try:
        conn = await setup_connection()

        await conn.execute(
            """
            delete from exercises;
            """
        )

        muscle_target_rows = await conn.fetch(
            """
            select t.id target_id, g.name group_name, t.name as target_name
            from muscle_targets t
            inner join muscle_groups g
            on t.muscle_group_id = g.id
            """
        )

        muscle_group_ids = {}
        for row in muscle_target_rows:
            if row["group_name"] not in muscle_group_ids.keys():
                muscle_group_ids[row["group_name"]] = []
            muscle_group_ids[row["group_name"]].append(str(row["target_id"]))

        muscle_target_ids = {}
        for row in muscle_target_rows:
            muscle_target_ids[f"{row['group_name']}/{row['target_name']}"] = str(row["target_id"])

        for exercise in exercises_json:
            exercise_id = await conn.fetchval(
                """
                insert into exercises
                (name, is_body_weight)
                values
                ($1, $2)
                returning id
                """, exercise["name"], exercise["is_body_weight"]
            )

            for target_str, percentage in exercise["targets"].items():
                if "/" not in target_str:
                    target_ids = muscle_group_ids[target_str]
                else:
                    target_ids = [muscle_target_ids[target_str]]

                for target_id in target_ids:
                    await conn.execute(
                        """
                        insert into exercise_muscle_targets
                        (muscle_target_id, exercise_id, ratio)
                        values
                        ($1, $2, $3)
                        """, target_id, exercise_id, int(percentage / 10)
                    )
       
    except Exception as e:
        print(e)
    finally:
        if conn: await conn.close()

async def main():
    await insert_muscle_groups()
    await insert_exercises()

if __name__ == "__main__":
    asyncio.run(main())