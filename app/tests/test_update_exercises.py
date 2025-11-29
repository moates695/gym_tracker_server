import pytest
import json
from uuid import uuid4
import math
import os

from ..api.middleware.database import setup_connection
from ..local.update_exercises import update
from ..tests.test_register import valid_user

@pytest.mark.asyncio
async def test_base_case():
    print(os.getcwd())
    with open("local/exercises.json", "r") as file:
        exercises = json.load(file)

    try:
        conn = await setup_connection()
        original_rows = await fetch_exercise_data(conn)
        await update(exercises)
        original_rows2 = await fetch_exercise_data(conn)

        # assert len(original_rows) == len(original_rows2)
        # for e1, e2 in zip(original_rows, original_rows2):
        #     try:
        #         assert e1 == e2
        #     except Exception as e:
        #         print(e1)
        #         print(e2)
        #         raise e
        assert original_rows == original_rows2

    except Exception as e:
        raise e
    finally:
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises():
    with open("local/exercises.json", "r") as file:
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
            "is_body_weight": True,
            "ratio": 0.2,
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
            "is_body_weight": False,
            "description": "description1",
            "weight_type": "free"
        },
    ]

    combined = exercises + dummy1

    try:
        conn = await setup_connection()

        original_rows = await fetch_exercise_data(conn)
        original_exercises = await fetch_exercises(conn)

        await update(combined)
        rows1 = await fetch_exercise_data(conn)
        await update(combined)
        rows2 = await fetch_exercise_data(conn)

        new_exercises = await fetch_exercises(conn)
        assert len(new_exercises) == len(original_exercises) + len(dummy1)

        assert rows1 == rows2

        dummy1_exercise1_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            and user_id is null;
            """, "Pytest 1"
        )

        await compare_target_ratios(conn, dummy1[0]["name"], dummy1[0]["targets"])
        await compare_target_ratios(conn, dummy1[1]["name"], dummy1[1]["targets"])

        dummy1_target_id_1 = await fetch_target_id(conn, dummy1_exercise1_id, 'arms', 'exterior forearm')
        dummy1_target_id_2 = await fetch_target_id(conn, dummy1_exercise1_id, 'back', 'traps')

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
                "ratio": 0.4,
                "description": "description1NEW",
                "weight_type": "cable"
            }
        ]

        combined = exercises + dummy2

        await update(combined)

        new_exercises = await fetch_exercises(conn)
        assert len(new_exercises) == len(original_exercises) + len(dummy2)

        await compare_target_ratios(conn, dummy2[0]["name"], dummy2[0]["targets"])

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

        dummy2_target_id_1 = await fetch_target_id(conn, dummy1_exercise1_id, 'arms', 'exterior forearm')
        dummy2_target_id_2 = await fetch_target_id(conn, dummy1_exercise1_id, 'back', 'traps')

        assert dummy1_target_id_1 == dummy2_target_id_1
        assert dummy1_target_id_2 == dummy2_target_id_2

        assert back_traps_ratio == await fetch_target_ratio(conn, dummy1_exercise1_id, dummy2_target_id_2)

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_bodyweight():
    with open("local/exercises.json", "r") as file:
        exercises = json.load(file)

    dummy = [
        {
            "name": "Pytest 1",
            "targets": {
                "arms/exterior forearm": 8,
                "arms/interior forearm": 8,
                "back/traps": 6,
                "core": 4
            },
            "is_body_weight": True,
            "ratio": 0.2,
            "description": "description1",
            "weight_type": "machine"
        },
        {
            "name": "Pytest 2",
            "targets": {
                "arms/exterior forearm": 8,
                "arms/interior forearm": 8,
                "back/traps": 6,
                "core": 4
            },
            "is_body_weight": True,
            "ratio": {
                "male": 0.3,
                "female": 0.5
            },
            "description": "description1",
            "weight_type": "machine"
        },
    ]

    try:
        conn = await setup_connection()

        original_rows = await fetch_exercise_data(conn)

        combined = exercises + dummy
        await update(combined)

        exercise1_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            and user_id is null;
            """, "Pytest 1"
        )

        assert math.isclose(0.2, await conn.fetchval(
            """
            select ratio
            from bodyweight_exercise_ratios
            where exercise_id = $1
            and gender = 'male'
            """, exercise1_id
        ), abs_tol=0.001)
        assert math.isclose(0.2, await conn.fetchval(
            """
            select ratio
            from bodyweight_exercise_ratios
            where exercise_id = $1
            and gender = 'female'
            """, exercise1_id
        ), abs_tol=0.001)

        exercise2_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            and user_id is null;
            """, "Pytest 2"
        )
        assert math.isclose(0.3, await conn.fetchval(
            """
            select ratio
            from bodyweight_exercise_ratios
            where exercise_id = $1
            and gender = 'male'
            """, exercise2_id
        ), abs_tol=0.001)
        assert math.isclose(0.5, await conn.fetchval(
            """
            select ratio
            from bodyweight_exercise_ratios
            where exercise_id = $1
            and gender = 'female'
            """, exercise2_id
        ), abs_tol=0.001)

        await update(exercises)

        assert not await conn.fetchval(
            """
            select exists (
                select 1
                from bodyweight_exercise_ratios
                where exercise_id = $1
            )
            """, exercise1_id
        )

        assert not await conn.fetchval(
            """
            select exists (
                select 1
                from bodyweight_exercise_ratios
                where exercise_id = $1
            )
            """, exercise2_id
        )

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_override():
    with open("local/exercises.json", "r") as file:
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

        original_rows = await fetch_exercise_data(conn)

        await update(combined)

        await compare_target_ratios(conn, dummy1[0]["name"], dummy1[0]["targets"])

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
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_variations():
    with open("local/exercises.json", "r") as file:
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
        original_rows = await fetch_exercise_data(conn)
        # original_exercises = await fetch_exercises(conn)

        combined = exercises + dummy

        await update(combined)

        await compare_target_ratios(conn, dummy[0]["name"], dummy[0]["targets"])

        parent_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            """, dummy[0]["name"]
        )

        await compare_target_ratios(conn, dummy[0]["variations"][0]["name"], dummy[0]["targets"], parent_id)
        await compare_target_ratios(conn, dummy[0]["variations"][2]["name"], dummy[0]["variations"][2]["targets"], parent_id)

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
                        "name": "narrow grip",
                        "targets": {
                            "arms/exterior forearm": 4,
                        }
                    }
                ]
            }
        ]

        combined = exercises + dummy

        await update(combined)

        assert parent_id == await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            """, dummy[0]["name"]
        )

        await compare_target_ratios(conn, dummy[0]["variations"][0]["name"], dummy[0]["variations"][0]["targets"], parent_id)

        length = await conn.fetchval(
            """
            select count(*)
            from exercises
            where parent_id = $1
            """, parent_id
        )
        assert length == len(dummy[0]["variations"])

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
            """, dummy[0]["variations"][0]["name"], parent_id
        )
        
        assert len(var_targets) == len(dummy[0]["variations"][0]["targets"].keys())
        assert var_targets[0]["ratio"] == 4

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_update_exercises_invalid_variations():
    with open("local/exercises.json", "r") as file:
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
        original_rows = await fetch_exercise_data(conn)

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
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_invalid_inserts_exercises(delete_users, create_user):
    with open("local/exercises.json", "r") as file:
        exercises = json.load(file)

    try:
        conn = await setup_connection()
        original_rows = await fetch_exercise_data(conn)

        name = "Pytest 1"

        await conn.execute(
            """
            insert into exercises
            (name, is_body_weight, weight_type)
            values
            ($1, false, 'free');
            """, name
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into exercises
                (name, is_body_weight, weight_type)
                values
                ($1, false, 'free');
                """, name.upper()
            )

        user_id = await conn.fetchval(
            """
            select id
            from users
            where email = $1
            """, valid_user["email"]
        )

        await conn.execute(
            """
            insert into exercises
            (name, is_body_weight, weight_type, user_id)
            values
            ($1, false, 'free', $2);
            """, name.upper(), user_id
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into exercises
                (name, is_body_weight, weight_type, user_id)
                values
                ($1, false, 'free', $2);
                """, name.upper(), user_id
            )

        parent_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = $1
            and user_id is null
            and parent_id is null;
            """, name
        )

        await conn.execute(
            """
            insert into exercises
            (name, is_body_weight, weight_type, parent_id)
            values
            ($1, false, 'free', $2);
            """, name.upper(), parent_id
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into exercises
                (name, is_body_weight, weight_type, parent_id)
                values
                ($1, false, 'free', $2);
                """, name.upper(), parent_id
            )

        await conn.execute(
            """
            insert into exercises
            (name, is_body_weight, weight_type, user_id, parent_id)
            values
            ($1, false, 'free', $2, $3);
            """, name, user_id, parent_id
        )

        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into exercises
                (name, is_body_weight, weight_type, user_id, parent_id)
                values
                ($1, false, 'free', $2, $3);
                """, name, user_id, parent_id
            )

        await conn.execute(
            """
            delete
            from exercises
            where name = $1
            and user_id is null
            and parent_id is null;
            """, name
        )

        await conn.execute(
            """
            delete
            from exercises
            where name = $1
            and user_id = $2
            and parent_id is null;
            """, name, user_id
        )

        await conn.execute(
            """
            delete
            from exercises
            where name = $1
            and user_id is null
            and parent_id = $2;
            """, name, parent_id
        )

        await conn.execute(
            """
            delete
            from exercises
            where name = $1
            and user_id = $2
            and parent_id = $3;
            """, name, user_id, parent_id
        )


    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

@pytest.mark.asyncio
async def test_invalid_insert_exercises2():
    with open("local/exercises.json", "r") as file:
        exercises = json.load(file)

    try:
        conn = await setup_connection()
        original_rows = await fetch_exercise_data(conn)

        muscle_group_id = await conn.fetchval(
            """
            select id
            from muscle_groups
            where name = 'arms';
            """
        )

        muscle_target_id = await conn.fetchval(
            """
            select id
            from muscle_targets
            where name = 'bicep'
            and muscle_group_id = $1
            """, muscle_group_id
        )

        exercise_id = await conn.fetchval(
            """
            select id
            from exercises
            where name = 'Push Up'
            and user_id is null
            and parent_id is null;
            """
        )
        
        with pytest.raises(Exception):
            await conn.execute(
                """
                insert into exercise_muscle_targets
                (muscle_target_id, exercise_id, ratio)
                values
                ($1, $2, 0);
                """, muscle_target_id, exercise_id
            )

            await conn.execute(
                """
                insert into exercise_muscle_targets
                (muscle_target_id, exercise_id, ratio)
                values
                ($1, $2, 11);
                """, muscle_target_id, exercise_id, ratio
            )

        for ratio in [1, 5, 10]:
            temp_id = await conn.fetchval(
                """
                insert into exercise_muscle_targets
                (muscle_target_id, exercise_id, ratio)
                values
                ($1, $2, $3)
                returning id;
                """, muscle_target_id, exercise_id, ratio
            )

            with pytest.raises(Exception):
                await conn.execute(
                    """
                    insert into exercise_muscle_targets
                    (muscle_target_id, exercise_id, ratio)
                    values
                    ($1, $2, $3);
                    """, muscle_target_id, exercise_id, ratio
                )

            await conn.execute(
                """
                delete
                from exercise_muscle_targets
                where id = $1;
                """, temp_id
            )

    except Exception as e:
        raise e
    finally:
        await update(exercises)
        assert original_rows == await fetch_exercise_data(conn)
        if conn: await conn.close()

async def fetch_exercises(conn):
    return await conn.fetch(
        """
        select *
        from exercises
        where user_id is null;
        """
    )

async def fetch_exercise_data(conn, include_custom=False):
    return await conn.fetch(
        f"""
        select e.*, emt.*
        from exercises e
        inner join exercise_muscle_targets emt
        on emt.exercise_id = e.id
        {"" if include_custom else "where e.user_id is null"}
        order by e.id, emt.id
        """
    )

###################################

def get_target_ratios(targets):
    with open("local/muscles.json", "r") as file:
        muscles = json.load(file)

    ratios = {}
    for target_str, ratio in targets.items():
        if "/" in target_str: continue
        for target in muscles[target_str]:
            ratios[f"{target_str}/{target}"] = ratio

    for target_str, ratio in targets.items():
        if "/" not in target_str: continue
        ratios[target_str] = ratio

    return ratios

async def compare_target_ratios(conn, exercise_name, targets, parent_id=None):
    if parent_id is None:
        db_target_data = await conn.fetch(
            """
            select emd.*
            from exercise_muscle_data emd
            inner join exercises e
            on emd.exercise_id = e.id
            where e.name = $1
            and e.user_id is null
            and e.parent_id is null;
            """, exercise_name
        )
    else:
        db_target_data = await conn.fetch(
            """
            select emd.*
            from exercise_muscle_data emd
            inner join exercises e
            on emd.exercise_id = e.id
            where e.name = $1
            and e.user_id is null
            and e.parent_id = $2;
            """, exercise_name, parent_id
        )

    target_ratios = get_target_ratios(targets)

    assert len(db_target_data) == len(target_ratios.keys())
    for row in db_target_data:
        assert target_ratios[f"{row['group_name']}/{row['target_name']}"] == row["ratio"]

def test_get_target_ratios():
    assert get_target_ratios({}) == {}
    
    targets = {
        "arms/bicep": 5,
        "chest/upper": 10,
        "arms": 3,
        "arms/interior forearm": 6,
        "shoulders": 7
    }

    assert get_target_ratios(targets) == {
        "arms/bicep": 5,
        "arms/tricep": 3,
        "arms/exterior forearm": 3,
        "arms/interior forearm": 6,
        "shoulders/front": 7,
        "shoulders/middle": 7,
        "shoulders/rear": 7,
        "chest/upper": 10,
    }

###################################

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