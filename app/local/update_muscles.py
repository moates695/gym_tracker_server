import json
import asyncio
import os
from dotenv import load_dotenv

from ..api.middleware.database import setup_connection
from .existing_users_db import check_totals
from .update_exercises import can_delete

load_dotenv(override=True)

# valid_group_ids = []
# valid_target_ids = []

async def main():
    if input(f"Update muscles in {os.environ['ENVIRONMENT']}? [y/n] ").lower() != 'y': return

    with open("app/local/muscles.json", "r") as file:
        muscles_json = json.load(file)

    await update(muscles_json)
    await check_totals()


async def update(muscles_json: dict):
    try:
        conn = tx = None
        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        rows = await conn.fetch(
            """
            select id, name
            from muscle_groups;
            """
        )
        db_groups = {
            row["name"]: row["id"] for row in rows
        } 

        valid_group_ids = []
        valid_target_ids = []

        for group, targets in muscles_json.items():
            group_id, target_ids = await update_muscle_group(conn, group, targets, db_groups)     
            valid_group_ids.append(group_id)
            valid_target_ids.extend(target_ids)

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

        await tx.commit()

    except Exception as e:
        if tx: await tx.rollback()
        raise e
    finally:
        if conn: await conn.close()

async def update_muscle_group(conn, group, targets, db_groups):
    if group not in db_groups.keys():
        group_id = await conn.fetchval(
            """
            insert into muscle_groups
            (name)
            values
            ($1)
            returning id;
            """, group
        )
    else:
        group_id = db_groups[group]

    rows = await conn.fetch(
        """
        select id, name
        from muscle_targets
        where muscle_group_id = $1
        """, group_id
    )
    db_targets = {
        row["name"]: row["id"] for row in rows
    }

    valid_target_ids = []
    for target in targets:
        target_id = await update_muscle_targets(conn, target, db_targets, group_id)
        valid_target_ids.append(target_id)

    return group_id, valid_target_ids

async def update_muscle_targets(conn, target, db_targets, group_id):
    if target in db_targets.keys():
        return db_targets[target]
    
    return await conn.fetchval(
        """
        insert into muscle_targets
        (muscle_group_id, name)
        values
        ($1, $2)
        returning id;
        """, group_id, target
    )

if __name__ == "__main__":
    asyncio.run(main())