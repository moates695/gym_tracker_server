import json
import asyncio

from ..api.middleware.database import setup_connection

async def main():
    if input("Run update muscles? [y/n] ").lower() != 'y': return

    with open("app/local/muscles.json", "r") as file:
        muscles_json = json.load(file)

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
                if muscle_target in db_muscle_targets.keys():
                    valid_target_ids.append(db_muscle_targets[muscle_target])
                    continue
                
                temp_id = await conn.fetchval(
                    """
                    insert into muscle_targets
                    (muscle_group_id, name)
                    values
                    ($1, $2)
                    returning id;
                    """, db_muscle_groups[muscle_group], muscle_target
                )
                valid_target_ids.append(temp_id)
        
        delete_map = {
            "muscle_groups": valid_group_ids,
            "muscle_targets": valid_target_ids,
        }

        for table, ids in delete_map.items():
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

if __name__ == "__main__":
    asyncio.run(main())