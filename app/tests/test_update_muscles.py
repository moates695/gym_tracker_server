import pytest
import json

from ..api.middleware.database import setup_connection
from ..local.update_muscles import update

@pytest.mark.asyncio
async def test_update_muscles_base():
    with open("local/muscles.json", "r") as file:
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
        original_rows = await fetch_muscles_groups_targets(conn)

        await update(combined)
        rows1 = await fetch_muscles_groups_targets(conn)
        await update(combined)
        rows2 = await fetch_muscles_groups_targets(conn)

        assert rows1 == rows2
        assert len(rows2) == len(original_rows) + 5

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
        rows3 = await fetch_muscles_groups_targets(conn)
        assert len(rows3) == len(original_rows) + 2

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
            if row["target_name"] != "target1": 
                assert row["target_name"] == "target4"
                continue
            assert row["target_id"] == group2_target1_id

    except Exception as e:
        raise e
    finally:
        await update(muscles_json)
        assert original_rows == await fetch_muscles_groups_targets(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_invalid_inserts_group():
    with open("local/muscles.json", "r") as file:
        muscles_json = json.load(file)
        
    try:
        conn = await setup_connection()
        original_rows = await fetch_muscles_groups_targets(conn)

        name = "Pytest 1"
        await conn.execute(
            """
            insert into muscle_groups
            (name)
            values
            ($1);
            """, name
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into muscle_groups
                (name)
                values
                ($1);
                """, name.upper()
            )

        await conn.execute(
            """
            delete
            from muscle_groups
            where name = $1;
            """, name
        )

    except Exception as e:
        raise e
    finally:
        await update(muscles_json)
        assert original_rows == await fetch_muscles_groups_targets(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_invalid_inserts_targets():
    with open("local/muscles.json", "r") as file:
        muscles_json = json.load(file)
        
    try:
        conn = await setup_connection()
        original_rows = await fetch_muscles_groups_targets(conn)

        group_name = "Pytest 1"
        group_id = await conn.fetchval(
            """
            insert into muscle_groups
            (name)
            values
            ($1)
            returning id;
            """, group_name
        )

        target_name = "Pytest Target"
        await conn.execute(
            """
            insert into muscle_targets
            (muscle_group_id, name)
            values
            ($1, $2)
            """, group_id, target_name
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into muscle_targets
                (muscle_group_id, name)
                values
                ($1, $2)
                """, group_id, target_name.upper()
            )

        group_name2 = "Pytest 2"
        group_id2 = await conn.fetchval(
            """
            insert into muscle_groups
            (name)
            values
            ($1)
            returning id;
            """, group_name2
        )

        await conn.execute(
            """
            insert into muscle_targets
            (muscle_group_id, name)
            values
            ($1, $2)
            """, group_id2, target_name
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into muscle_targets
                (muscle_group_id, name)
                values
                ($1, $2)
                """, group_id2, target_name
            )

        for name in [group_name, group_name2]:
            await conn.execute(
                """
                delete
                from muscle_groups
                where name = $1;
                """, name
            )


    except Exception as e:
        raise e
    finally:
        await update(muscles_json)
        assert original_rows == await fetch_muscles_groups_targets(conn)
        if conn: await conn.close()

async def fetch_muscles_groups_targets(conn):
    return await conn.fetch(
        """
        select *
        from muscle_groups_targets
        """
    )
    