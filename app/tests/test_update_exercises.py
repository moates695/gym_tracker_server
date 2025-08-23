import pytest
import json

from ..api.middleware.database import setup_connection
from ..local.update_exercises import update

@pytest.mark.asyncio
async def test_update_exercises():
    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file)

    dummy1 = [
        {
            "name": "Pytest 1",
            "targets": {
                "arms/exterior forearm": 8,
                "arms/interior forearm": 8,
                "back/traps": 6,
                "core": 4
            },
            "is_body_weight": False,
            "description": "description1",
            "weight_type": "machine"
        },
        {
            "name": "Pytest 2",
            "targets": {
                "chest/upper": 8,
                "chest/lower": 8,
                "core/lower abs": 6,
                "core": 4,
            },
            "is_body_weight": True,
            "description": "description1",
            "weight_type": "free"
        },
    ]

    combined = exercises + dummy1

    try:
        conn = await setup_connection()

        original_rows = await fetch_exercises(conn)

        await update(combined)
        rows1 = await fetch_exercises(conn)
        await update(combined)
        rows2 = await fetch_exercises(conn)

        assert rows1 == rows2
        assert len(rows2) > len(original_rows)

        dummy1_exercise_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            and user_id is null;
            """, "Pytest 1"
        )

        dummy1_target_id_1 = await fetch_target_id(conn, dummy1_exercise_id, 'arms', 'exterior forearm')
        dummy1_target_id_2 = await fetch_target_id(conn, dummy1_exercise_id, 'back', 'traps')

        back_traps_ratio = 2
        dummy2 = [
            {
                "name": "Pytest 1",
                "targets": {
                    "arms/exterior forearm": 8,
                    "back/traps": back_traps_ratio,
                    "core": 4
                },
                "is_body_weight": True,
                "description": "description1NEW",
                "weight_type": "cable"
            }
        ]

        combined = exercises + dummy2

        await update(combined)

        assert not await conn.fetchval(
            """
            select exists (
                select 1
                from exercises
                where name = $1
                and user_id is null
            );
            """, "Pytest 2"
        )

        rows = await conn.fetchrow(
            """
            select *
            from exercises
            where name = $1
            and user_id is null
            """, "Pytest 1"
        )

        fields = ["is_body_weight","description","weight_type"]
        for field in fields:
            assert dummy2[0][field] == rows[field]

        dummy2_target_id_1 = await fetch_target_id(conn, dummy1_exercise_id, 'arms', 'exterior forearm')
        dummy2_target_id_2 = await fetch_target_id(conn, dummy1_exercise_id, 'back', 'traps')

        assert dummy1_target_id_1 == dummy2_target_id_1
        assert dummy1_target_id_2 == dummy2_target_id_2

        assert back_traps_ratio == await conn.fetchval(
            """
            select ratio
            from exercise_muscle_targets
            where exercise_id = $1
            and muscle_target_id = $2
            """, dummy1_exercise_id, dummy2_target_id_2
        )

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercises(conn)
        if conn: await conn.close()


async def fetch_exercises(conn, include_custom=False):
    return await conn.fetch(
        f"""
        select e.*, emt.*
        from exercises e
        inner join exercise_muscle_targets emt
        on emt.exercise_id = e.id
        {"" if include_custom else "where e.user_id is null"}
        """
    )

async def fetch_target_id(conn, exercise_id, group_name, target_name):
    return await conn.fetchval(
        """
        select target_id
        from exercise_muscle_data
        where exercise_id = $1
        and group_name = $2
        and target_name = $3
        """, exercise_id, group_name, target_name
    )