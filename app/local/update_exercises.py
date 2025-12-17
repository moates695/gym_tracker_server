import json
import asyncio
import os
from dotenv import load_dotenv
from copy import deepcopy

from ..api.middleware.database import *
from ..api.middleware.database import setup_connection
from .existing_users_db import check_totals

load_dotenv(override=True)

async def main():
    if input(f"Update exercises in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return

    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file)

    await update(exercises)
    await check_totals()

async def update(exercises):
    exercises_copy = deepcopy(exercises)

    check_json(exercises_copy)

    try:
        conn = tx = None
        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        valid_exercise_ids = []
        for exercise in exercises_copy:
            exercise_id = await update_exercise(conn, exercise)
            valid_exercise_ids.append(exercise_id)
            for variation in exercise.get("variations", []):
                variation_id = await update_exercise_variation(conn, variation, exercise, exercise_id)
                valid_exercise_ids.append(variation_id)

        # todo: delete old exercises with permission

        await conn.execute(
            """
            delete
            from exercises
            where not (id = any($1::uuid[]))
            and user_id is null
            """, valid_exercise_ids
        )

        await tx.commit()

    except Exception as e:
        if tx: await tx.rollback()
        raise e
    finally:
        if conn: await conn.close()

def check_json(exercises):
    exercise_names = []
    for exercise in exercises:
        variation_names = []
        for variation in exercise.get("variations", []):
            variation_names.append(variation["name"].strip().lower())

        if len(variation_names) != len(set(variation_names)):
            raise Exception(f"exercise {exercise['name']} have variations with same name")

        exercise_names.append(exercise["name"].strip().lower())

    if len(exercise_names) != len(set(exercise_names)):
        for e1 in exercise_names:
            for e2 in exercise_names:
                if e1 != e2: continue
                raise Exception(f"exercise {e1} have the same name")

async def update_exercise(conn, exercise, parent_id=None) -> str:
    if not await does_exercise_exist(conn, exercise, parent_id):
        exercise_id = await conn.fetchval(
            """
            insert into exercises
            (name, is_body_weight, description, weight_type, parent_id)
            values
            ($1, $2, $3, $4, $5)
            returning id
            """, 
            exercise["name"], 
            exercise["is_body_weight"], 
            exercise["description"], 
            exercise["weight_type"],
            parent_id
        )
    else:
        exercise_id = await conn.fetchval(
            """
            update exercises
            set 
                is_body_weight = $1, 
                description = $2, 
                weight_type = $3
            where name = $4
            and parent_id is not distinct from $5
            returning id
            """, 
            exercise["is_body_weight"],
            exercise["description"],
            exercise["weight_type"],
            exercise["name"],
            parent_id
        )

    if exercise["is_body_weight"]:
        await update_bodyweight_ratios(conn, exercise, exercise_id)

    await update_exercise_muscle_targets(conn, exercise, exercise_id)

    return exercise_id

async def update_exercise_variation(conn, variation, parent, parent_id):
    if "targets" not in variation.keys() or variation["targets"] == {}:
        variation["targets"] = deepcopy(parent["targets"])

    variation["is_body_weight"] = parent["is_body_weight"]
    if variation["is_body_weight"] and "ratio" not in variation:
        variation["ratio"] = deepcopy(parent["ratio"])

    if "description" not in variation.keys():
        variation["description"] = ""

    variation["weight_type"] = parent["weight_type"]

    return await update_exercise(conn, variation, parent_id)

async def update_bodyweight_ratios(conn, exercise, exercise_id):
    if isinstance(exercise["ratio"], dict):
        ratio = exercise["ratio"]
    else:
        ratio = {
            "male": exercise["ratio"],
            "female": exercise["ratio"]
        }

    for gender, ratio in ratio.items():
        await conn.execute(
            """
            insert into bodyweight_exercise_ratios
            (exercise_id, ratio, gender)
            values 
            ($1, $2, $3)
            on conflict (exercise_id, gender) do update
                set ratio = EXCLUDED.ratio
            """, exercise_id, ratio, gender
        )

async def update_exercise_muscle_targets(conn, exercise, exercise_id):
    target_data = await get_target_data(conn, exercise)

    valid_target_ids = []
    for target_id, ratio in target_data.items():
        id = await conn.fetchval(
            """
            insert into exercise_muscle_targets
            (muscle_target_id, exercise_id, ratio)
            values
            ($1, $2, $3)
            on conflict (muscle_target_id, exercise_id)
            do update
            set ratio = excluded.ratio
            returning id
            """,
            target_id,
            exercise_id,
            ratio
        )
        valid_target_ids.append(id)

    # todo, get names of targets for exercise and confirm deletion

    await conn.execute(
        """
        delete
        from exercise_muscle_targets
        where exercise_id = $1
        and not (id = any($2::uuid[]))
        """, exercise_id, valid_target_ids
    )

###########################################
### Helpers

async def get_target_data(conn, exercise):
    target_data = {}
    
    for muscle_str, ratio in exercise["targets"].items():
        if "/" in muscle_str: continue
        target_ids = await group_name_to_target_ids(conn, muscle_str)
        for target_id in target_ids:
            target_data[target_id] = ratio
    
    for muscle_str, ratio in exercise["targets"].items():
        if "/" not in muscle_str: continue
        target_id = await target_name_to_id(conn, muscle_str.split("/")[-1])
        if target_id == None: raise Exception("could not find target")
        target_data[target_id] = ratio

    return target_data

async def group_name_to_target_ids(conn, group_name):
    rows = await conn.fetch(
        """
        select target_id
        from muscle_groups_targets
        where group_name = $1
        """, group_name
    )
    return [row["target_id"] for row in rows]

async def target_name_to_id(conn, target_name):
    return await conn.fetchval(
        """
        select target_id
        from muscle_groups_targets
        where target_name = $1
        """, target_name
    )

async def does_exercise_exist(conn, exercise, parent_id):
    return await conn.fetchval(
        """
        select exists (
            select 1
            from exercises
            where name = $1
            and parent_id is not distinct from $2
            and user_id is null
        )
        """, exercise["name"], parent_id
    )

if __name__ == "__main__":
    asyncio.run(main())