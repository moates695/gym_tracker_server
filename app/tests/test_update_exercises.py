import pytest
import json
from uuid import uuid4

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

        assert back_traps_ratio == await fetch_target_ratio(conn, dummy1_exercise_id, dummy2_target_id_2)

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercises(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_override():
    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file)

    dummy1 = [
        {
            "name": "Pytest 1",
            "targets": {
                "arms/exterior forearm": 8,
                "arms/interior forearm": 8,
                "core/lower abs": 6,
                "core": 4,
                "core/upper abs": 5,
            },
            "is_body_weight": False,
            "description": "description1",
            "weight_type": "machine"
        }
    ]

    combined = exercises + dummy1

    try:
        conn = await setup_connection()

        original_rows = await fetch_exercises(conn)

        await update(combined)

        exercise_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            and user_id is null;
            """, "Pytest 1"
        )

        target_id_1 = await fetch_target_id(conn, exercise_id, 'core', 'lower abs')
        target_id_2 = await fetch_target_id(conn, exercise_id, 'core', 'upper abs')
        target_id_3 = await fetch_target_id(conn, exercise_id, 'core', 'obliques')

        assert 6 == await fetch_target_ratio(conn, exercise_id, target_id_1)
        assert 5 == await fetch_target_ratio(conn, exercise_id, target_id_2)
        assert 4 == await fetch_target_ratio(conn, exercise_id, target_id_3)

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercises(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_variations():
    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file)

    dummy = [
        {
            "name": "Pytest 1",
            "targets": {
                "arms/exterior forearm": 8,
                "arms/interior forearm": 8,
                "core/lower abs": 6,
                "core": 4,
                "core/upper abs": 5,
            },
            "is_body_weight": False,
            "description": "description1",
            "weight_type": "machine",
            "variations": [
                {
                    "name": "wide grip"
                },
                {
                    "name": "close grip",
                    "description": "description2"
                },
                {
                    "name": "narrow grip",
                    "targets": {
                        "arms/exterior forearm": 3,
                    }
                }
            ]
        }
    ]

    try:
        conn = await setup_connection()

        original_rows = await fetch_exercises(conn)

        combined = exercises + dummy

        await update(combined)

        parent_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            """, dummy[0]["name"]
        )

        length = await conn.fetchval(
            """
            select count(*)
            from exercises
            where parent_id = $1
            """, parent_id
        )
        assert length == len(dummy[0]["variations"])

        parent_targets = await conn.fetch(
            """
            select *
            from exercise_muscle_data
            where exercise_id = $1
            """, parent_id
        )
        assert len(parent_targets) > 0

        for i in range(0, 2):
            var_targets = await conn.fetch(
                """
                select *
                from exercise_muscle_data
                where exercise_id = (
                    select id
                    from exercises
                    where name = $1
                    and parent_id = $2
                )
                """, dummy[0]["variations"][i]["name"], parent_id
            )

            assert len(parent_targets) == len(var_targets)
            for row1 in parent_targets:
                is_found = False
                for row2 in var_targets:
                    fields = ["group_id", "target_id", "ratio"]
                    for field in fields:
                        if row1[field] != row2[field]: break
                    else:
                        is_found = True
                        break

                if not is_found: assert False

        var_targets = await conn.fetch(
                """
                select *
                from exercise_muscle_data
                where exercise_id = (
                    select id
                    from exercises
                    where name = $1
                    and parent_id = $2
                )
                """, dummy[0]["variations"][2]["name"], parent_id
            )
        
        assert len(var_targets) == len(dummy[0]["variations"][2]["targets"].keys())
        assert var_targets[0]["ratio"] == 3

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercises(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_invalid_variations():
    with open("app/local/exercises.json", "r") as file:
        exercises = json.load(file) 

    name = str(uuid4())
    dummy = [
        {
            "name": "Pytest 1",
            "targets": {
                "arms/exterior forearm": 8,
                "arms/interior forearm": 8,
                "core/lower abs": 6,
                "core": 4,
                "core/upper abs": 5,
            },
            "is_body_weight": False,
            "description": "description1",
            "weight_type": "machine",
            "variations": [
                {
                    "name": name
                },
                {
                    "name": name
                }
            ]
        }
    ]

    combined = exercises + dummy

    try:
        conn = await setup_connection()

        with pytest.raises(Exception):
            await update(combined)

        dummy[0]["variations"][0]["name"] = str(uuid4())

        await update(combined)

        length = await conn.fetchval(
            """
            select count(*)
            from exercises
            where parent_id = (
                select id
                from exercises
                where name = $1
            )
            """, dummy[0]["name"]
        )
        assert length == len(dummy[0]["variations"])

        await update(exercises)

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        # assert original_rows == await fetch_exercises(conn)
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

async def fetch_target_ratio(conn, exercise_id, target_id):
    return await conn.fetchval(
        """
        select ratio
        from exercise_muscle_targets
        where exercise_id = $1
        and muscle_target_id = $2
        """, exercise_id, target_id
    )