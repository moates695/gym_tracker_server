import pytest
import json

from ..api.middleware.database import setup_connection
from ..local.update_muscles import update

@pytest.mark.asyncio
async def test_update_muscles():
    with open("app/local/muscles.json", "r") as file:
        muscles_json = json.load(file)

    dummy_json = {
        "group1": [
            "target1",
            "target2"
        ],
        "group2": [
            "target1",
            "target2",
            "target3"
        ]
    }

    combined = muscles_json | dummy_json

    try:
        conn = await setup_connection()

        await update(combined)
        rows1 = await get_muscles_groups_targets(conn)
        await update(combined)
        rows2 = await get_muscles_groups_targets(conn)

        assert rows1 == rows2
        for row in rows2:
            if row["group_name"] != "group2": continue
            group2_id = row["group_id"]
            if row["target_name"] != "target1": continue
            group2_target1_id = row["target_id"]

        dummy_json = {
            "group2": [
                "target1",
                "target4"
            ]
        }

        combined = muscles_json | dummy_json

        await update(combined) 
        assert not await conn.fetchval(
            """
            select exists (
                select 1
                from muscle_groups_targets
                where group_name = $1
            );
            """, "group1"
        )

        rows = await conn.fetch(
            """
            select *
            from muscle_groups_targets
            where group_id = $1
            """, group2_id
        )
        assert len(rows) == 2

        for row in rows:
            assert row["target_name"] in dummy_json["group2"]
            if row["target_name"] != "target1": continue
            assert row["target_id"] == group2_target1_id

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()
        await update(muscles_json)


async def get_muscles_groups_targets(conn):
    return await conn.fetch(
        """
        select *
        from muscle_groups_targets
        """
    )
