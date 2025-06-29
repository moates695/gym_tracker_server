import asyncio
import json

from ..api.middleware.database import setup_connection

with open("app/local/exercises.json", "r") as file:
    exercises_json = json.load(file)

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
                (name, is_body_weight, description, weight_type)
                values
                ($1, $2, $3, $4)
                returning id
                """, exercise["name"], exercise["is_body_weight"],exercise["description"], exercise["weight_type"]
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
    await insert_exercises()

if __name__ == "__main__":
    asyncio.run(main())