import json
import asyncio
import os
from dotenv import load_dotenv

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
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select *
            from exercises
            where user_id is null
            and parent_id is null;
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
            exercise_id = await update_exercise(conn, exercise, db_exercises, group_name_to_target_ids, target_name_to_id)
            valid_exercise_ids.append(exercise_id)

        invalid_id_rows = await conn.fetch(
            """
            select id
            from exercises
            where not (id = any($1))
            and user_id is null
            and parent_id is null;
            """, valid_exercise_ids
        )
        invalid_ids = [row["id"] for row in invalid_id_rows]

        if can_delete("exercises", invalid_ids):
            await conn.execute(
                f"""
                delete 
                from exercises
                where not (id = any($1))
                and user_id is null
                and parent_id is null;
                """, valid_exercise_ids
            )

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

async def update_exercise(conn, exercise, db_exercises, group_name_to_target_ids, target_name_to_id) -> str:    
    exercise_id = await update_exercise_base(conn, exercise, db_exercises, group_name_to_target_ids, target_name_to_id)
    await update_exercise_variations(conn, exercise_id, exercise, db_exercises, group_name_to_target_ids, target_name_to_id)
    return exercise_id

async def update_exercise_base(conn, exercise, db_exercises, group_name_to_target_ids, target_name_to_id) -> str:
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

    if exercise["is_body_weight"]:
        ratios = exercise["ratio"]
        if isinstance(ratios, (int, float)):
            ratios = {
                "male": ratios,
                "female": ratios
            }

        for gender, ratio in ratios.items():
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

    target_data = get_target_data(exercise, group_name_to_target_ids, target_name_to_id)

    valid_exercise_muscle_target_ids = []
    for target_id, ratios in target_data.items():
        muscle_target_id = await update_exercise_muscle_target(conn, target_id, ratios, exercise_id, db_exercise_target_ids)
        valid_exercise_muscle_target_ids.append(muscle_target_id)

    invalid_id_rows = await conn.fetch(
        """
        select id
        from exercise_muscle_targets
        where exercise_id = $1
        and not (id = any($2::uuid[]))
        """, exercise_id, valid_exercise_muscle_target_ids
    )
    invalid_ids = [row["id"] for row in invalid_id_rows]

    if can_delete("exercise_muscle_targets", invalid_ids):
        await conn.execute(
            """
            delete
            from exercise_muscle_targets
            where exercise_id = $1
            and not (id = any($2::uuid[]))
            """, exercise_id, valid_exercise_muscle_target_ids
        )

    return exercise_id

async def update_exercise_variations(conn, parent_id, parent_exercise, db_exercises, group_name_to_target_ids, target_name_to_id):    
    rows = await conn.fetch(
        """
        select *
        from exercises
        where parent_id = $1
        """, parent_id
    )
    db_variations = {
        row["name"]: row for row in rows
    }
    
    valid_variation_ids = []
    for variation_config in parent_exercise.get("variations", []):
        variation = variation_config.copy()
        valid_id = await update_exercise_variation(conn, parent_id, parent_exercise, variation, db_variations, group_name_to_target_ids, target_name_to_id)
        valid_variation_ids.append(valid_id)

    invalid_id_rows = await conn.fetch(
        """
        select id
        from exercises
        where parent_id = $1
        and not (id = any($2)) 
        """, parent_id, valid_variation_ids
    )
    invalid_ids = [row["id"] for row in invalid_id_rows]

    if can_delete("variations", invalid_ids):
        await conn.execute(
            """
            delete 
            from exercises
            where parent_id = $1
            and not (id = any($2)) 
            """, parent_id, valid_variation_ids
        )

async def update_exercise_variation(conn, parent_id, parent_exercise, variation, db_variations, group_name_to_target_ids, target_name_to_id) -> str:
    if "targets" not in variation.keys() or variation["targets"] == {}:
        variation["targets"] = parent_exercise["targets"].copy()

    if "description" not in variation.keys():
        variation["description"] = ""

    if variation["name"] not in db_variations.keys():
        variation_id = await conn.fetchval(
            """
            insert into exercises
            (name, is_body_weight, description, weight_type, parent_id)
            values
            ($1, $2, $3, $4, $5)
            returning id;
            """, 
            variation["name"],
            parent_exercise["is_body_weight"],
            variation["description"],
            parent_exercise["weight_type"],
            parent_id
        )
    elif variation["description"] != parent_exercise["description"]:
        await conn.execute(
            """
            update exercises
            set description = $1
            where name = $2
            and parent_id = $3
            """,
            variation["description"],
            variation["name"],
            parent_id
        )

    if variation["name"] in db_variations.keys():
        variation_id = db_variations[variation["name"]]["id"]

    rows = await conn.fetch(
        """
        select *
        from exercise_muscle_targets
        where exercise_id = $1
        """, variation_id
    )
    db_exercise_target_ids = {
        row["muscle_target_id"]: row for row in rows
    }

    target_data = get_target_data(variation, group_name_to_target_ids, target_name_to_id)

    valid_exercise_muscle_target_ids = []
    for target_id, ratio in target_data.items():
        muscle_target_id = await update_exercise_muscle_target(conn, target_id, ratio, variation_id, db_exercise_target_ids)
        valid_exercise_muscle_target_ids.append(muscle_target_id)

    invalid_id_rows = await conn.fetch(
        """
        select id
        from exercise_muscle_targets
        where exercise_id = $1
        and not (id = any($2::uuid[]))
        """, variation_id, valid_exercise_muscle_target_ids
    )
    invalid_ids = [row["id"] for row in invalid_id_rows]

    if can_delete("exercise_muscle_targets", invalid_ids):
        await conn.execute(
            """
            delete
            from exercise_muscle_targets
            where exercise_id = $1
            and not (id = any($2::uuid[]))
            """, variation_id, valid_exercise_muscle_target_ids
        )

    return variation_id

async def update_exercise_muscle_target(conn, target_id, ratio, exercise_id, db_exercise_target_ids):
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
    
    return exercise_muscle_target_id

def is_exercise_same(exercise1, exercise2) -> bool:
    fields = ["is_body_weight", "description", "weight_type"]
    for field in fields:
        if exercise1[field] != exercise2[field]: return False
    return True

def get_target_data(exercise, group_name_to_target_ids, target_name_to_id):
    target_data = {}
    for muscle_str, ratio in exercise["targets"].items():
        if "/" in muscle_str: continue
        for target_id in group_name_to_target_ids[muscle_str]:
            target_data[target_id] = ratio
    
    for muscle_str, ratio in exercise["targets"].items():
        if "/" not in muscle_str: continue
        target_data[target_name_to_id[muscle_str.split("/")[-1]]] = ratio

    return target_data

def can_delete(key: str, to_delete_ids: list[str]) -> bool:
    if len(to_delete_ids) == 0 or os.environ["ENVIRONMENT"] in ["dev", "pytest"]: return True
    return input(f"From {key} delete rows with id {to_delete_ids}? (y/n)").lower() == 'y'

if __name__ == "__main__":
    asyncio.run(main())