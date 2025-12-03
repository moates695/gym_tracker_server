import json
import asyncio
import os
from dotenv import load_dotenv

from ..api.middleware.database import setup_connection
from .existing_users_db import check_totals
from .update_exercises import can_delete

load_dotenv(override=True)

async def main():
    if input(f"Update muscles in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return

    with open("app/local/muscles.json", "r") as file:
        muscles_json = json.load(file)

    await update(muscles_json)
    await check_totals()

async def update(muscles_json: dict):
    try:
        conn = await setup_connection()

        valid_group_ids = []
        valid_target_ids = []

        rows = await conn.fetch(
            """
            select id, name
            from muscle_groups;
            """
        )

        db_muscle_groups = {
            row["name"]: row["id"] for row in rows
        } 

        for muscle_group, muscle_targets in muscles_json.items():
            await update_muscle_groups(conn, muscle_group, muscle_targets, db_muscle_groups, valid_group_ids, valid_target_ids)     
        
        delete_map = {
            "muscle_groups": valid_group_ids,
            "muscle_targets": valid_target_ids,
        }
        
        for table, ids in delete_map.items():
            invalid_id_rows = await conn.fetch(
                f"""
                select id
                from {table}
                where not (id = any($1))
                """, ids
            )
            invalid_ids = [row["id"] for row in invalid_id_rows]
        
            if not can_delete(table, invalid_ids): continue
            
            await conn.execute(
                f"""
                delete 
                from {table}
                where not (id = any($1))
                """, ids
            )

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

async def update_muscle_groups(conn, muscle_group, muscle_targets, db_muscle_groups, valid_group_ids, valid_target_ids):
    if muscle_group not in db_muscle_groups.keys():
        temp_id = await conn.fetchval(
            """
            insert into muscle_groups
            (name)
            values
            ($1)
            returning id;
            """, muscle_group
        )
        db_muscle_groups[muscle_group] = temp_id

    valid_group_ids.append(db_muscle_groups[muscle_group])

    rows = await conn.fetch(
        """
        select id, name
        from muscle_targets
        where muscle_group_id = $1
        """, db_muscle_groups[muscle_group]
    )
    db_muscle_targets = {
        row["name"]: row["id"] for row in rows
    }

    for muscle_target in muscle_targets:
        await update_muscle_targets(conn, muscle_target, db_muscle_targets, valid_target_ids, db_muscle_groups[muscle_group])

async def update_muscle_targets(conn, muscle_target, db_muscle_targets, valid_target_ids, muscle_group_id):
    if muscle_target in db_muscle_targets.keys():
        valid_target_ids.append(db_muscle_targets[muscle_target])
        return
    
    temp_id = await conn.fetchval(
        """
        insert into muscle_targets
        (muscle_group_id, name)
        values
        ($1, $2)
        returning id;
        """, muscle_group_id, muscle_target
    )
    valid_target_ids.append(temp_id)

if __name__ == "__main__":
    asyncio.run(main())