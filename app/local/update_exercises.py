import json
import asyncio
import os

from ..api.middleware.database import setup_connection

async def main():
    if input(f"Update exercises in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return

    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file)

    await update(exercises)

async def update(exercises):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select *
            from exercises
            where user_id is null;
            """
        )
        db_exercises = {
            row["name"]: row for row in rows
        }

        rows = await conn.fetch(
            """
            select group_name, target_name, target_id
            from muscle_groups_targets;
            """
        )
        
        group_name_to_target_ids = {}
        for row in rows:
            if row["group_name"] not in group_name_to_target_ids.keys():
                group_name_to_target_ids[row["group_name"]] = []
            group_name_to_target_ids[row["group_name"]].append(row["target_id"])

        target_name_to_id = {
            row["target_name"]: row["target_id"] for row in rows
        }

        valid_exercise_ids = []
        
        for exercise in exercises:
            valid_exercise_muscle_target_ids = []

            if exercise["name"] not in db_exercises.keys():
                exercise_id = await conn.fetchval(
                    """
                    insert into exercises
                    (name, is_body_weight, description, weight_type)
                    values
                    ($1, $2, $3, $4)
                    returning id;
                    """, 
                    exercise["name"], 
                    exercise["is_body_weight"], 
                    exercise["description"], 
                    exercise["weight_type"]
                )
            elif not is_exercise_same(exercise, db_exercises[exercise["name"]]):
                await conn.execute(
                    """
                    update exercises
                    set is_body_weight = $1, description = $2, weight_type = $3
                    where name = $4
                    """, 
                    exercise["is_body_weight"],
                    exercise["description"],
                    exercise["weight_type"],
                    exercise["name"],
                )

            if exercise["name"] in db_exercises.keys():
                exercise_id = db_exercises[exercise["name"]]["id"]

            valid_exercise_ids.append(exercise_id)

            rows = await conn.fetch(
                """
                select *
                from exercise_muscle_targets
                where exercise_id = $1
                """, exercise_id
            )
            db_exercise_target_ids = {
                row["muscle_target_id"]: row for row in rows
            }

            target_data = {}
            for target_str, ratio in exercise["targets"].items():
                if "/" in target_str: continue
                for target_id in group_name_to_target_ids[target_str]:
                    target_data[target_id] = ratio
            
            for target_str, ratio in exercise["targets"].items():
                if "/" not in target_str: continue
                target_data[target_name_to_id[target_str.split("/")[-1]]] = ratio

            for target_id, ratio in target_data.items():
                if target_id not in db_exercise_target_ids.keys():
                    exercise_muscle_target_id = await conn.fetchval(
                        """
                        insert into exercise_muscle_targets
                        (muscle_target_id, exercise_id, ratio)
                        values
                        ($1, $2, $3)
                        returning id;
                        """, target_id, exercise_id, ratio
                    )
                elif db_exercise_target_ids[target_id]["ratio"] != ratio:
                    await conn.execute(
                        """
                        update exercise_muscle_targets
                        set ratio = $1
                        where id = $2
                        """, ratio, db_exercise_target_ids[target_id]["id"]
                    )

                if target_id in db_exercise_target_ids.keys():
                    exercise_muscle_target_id = db_exercise_target_ids[target_id]["id"]
                
                valid_exercise_muscle_target_ids.append(exercise_muscle_target_id)
                
            await conn.execute(
                """
                delete
                from exercise_muscle_targets
                where exercise_id = $1
                and not (id = any($2::uuid[]))
                """, exercise_id, valid_exercise_muscle_target_ids
            )

        await conn.execute(
            f"""
            delete 
            from exercises
            where not (id = any($1))
            and user_id is null;
            """, valid_exercise_ids
        )


    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

def is_exercise_same(exercise1, exercise2) -> bool:
    fields = ["is_body_weight", "description", "weight_type"]
    for field in fields:
        if exercise1[field] != exercise2[field]: return False
    return True

if __name__ == "__main__":
    asyncio.run(main())