import json
import asyncio
import os
from dotenv import load_dotenv

from ..api.middleware.database import *
from ..api.middleware.database import setup_connection
from .existing_users_db import check_totals

load_dotenv(override=True)

valid_exercise_ids = []

async def main():
    if input(f"Update exercises in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return

    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file)

    check_json(exercises)

    await update(exercises)
    await check_totals()

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
        raise Exception("exercises have the same name")

# todo: delete old exercises with permission

async def update(exercises):
    try:
        conn = tx = None
        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        for exercise in exercises:
            exercise_id = await update_exercise(conn, exercise)
            for variation in exercise.get("variations", []):
                await update_exercise_variation(conn, variation, exercise, exercise_id)

        await tx.commit()

    except Exception as e:
        if tx: await tx.rollback()
        raise e
    finally:
        if conn: await conn.close()

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
            set is_body_weight = $1, description = $2, weight_type = $3
            where name = $4
            returning id
            """, 
            exercise["is_body_weight"],
            exercise["description"],
            exercise["weight_type"],
            exercise["name"],
        )

    if exercise["is_body_weight"]:
        await update_bodyweight_ratios(conn, exercise, exercise_id)

    await update_exercise_muscle_targets(conn, exercise, exercise_id)

    return exercise_id

async def update_exercise_variation(conn, variation, parent, parent_id):
    if "targets" not in variation.keys() or variation["targets"] == {}:
        variation["targets"] = parent["targets"]

    variation["is_body_weight"] = parent["is_body_weight"]
    if variation["is_body_weight"]:
        variation["ratio"] = parent["ratio"]

    if "description" not in variation.keys():
        variation["description"] = ""

    variation["weight_type"] = parent["weight_type"]

    await update_exercise(conn, variation, parent_id)

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
        for target_id in await group_name_to_target_ids(conn, muscle_str):
            target_data[target_id] = ratio
    
    for muscle_str, ratio in exercise["targets"].items():
        if "/" not in muscle_str: continue
        target_id = await target_name_to_id(conn, muscle_str.split("/")[-1])
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

def can_delete(table: str, to_delete_ids: list[str]) -> bool:
    if len(to_delete_ids) == 0 or os.environ["ENVIRONMENT"] in ["dev", "pytest"]: return True
    return input(f"From {table} delete rows with id {to_delete_ids}? (y/n)").lower() == 'y'

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