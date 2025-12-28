from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone, timedelta
from fastapi.security import HTTPBearer
from copy import deepcopy
import math

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *
from app.api.routes.exercises.list_all import get_days_past
from app.api.routes.muscles import get_muscle_maps

router = APIRouter()
security = HTTPBearer()

@router.get("/muscles-history")
async def exercise_history(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select w.started_at, we.exercise_id, wsd.reps, wsd.weight, wsd.num_sets, mgt.group_name, mgt.target_name, emt.ratio
            from workouts w
            inner join workout_exercises we
            on we.workout_id = w.id
            inner join workout_set_data wsd
            on wsd.workout_exercise_id = we.id
            inner join exercise_muscle_targets emt
            on emt.exercise_id = we.exercise_id
            left join muscle_groups_targets mgt
            on mgt.target_id = emt.muscle_target_id
            where w.user_id = $1
            order by mgt.group_name, mgt.target_name
            """,
            credentials["user_id"],
        )
        print(f"Fetched {len(rows)} exercise history rows")

        empty = {
            "volume": 0,
            "sets": 0,
            "reps": 0,
        }

        timespans = {
            "week": timedelta(weeks=1),
            "month": timedelta(days=30),
            "3_months": timedelta(days=30) * 3,
            "6_months": timedelta(days=30) * 6,
            "year": timedelta(days=365),
        }
        utc_now = datetime.now(tz=timezone.utc)

        data = {}
        added_exercise_groups = {}
        all_spans = list(timespans.keys()) + ["all"]
        for span in all_spans:
            data[span] = {}
            added_exercise_groups[span] = {}

        for row in rows:
            spans = []
            for key, delta in timespans.items():
                spans.append(key)
                if row["started_at"] >= utc_now - delta: break
            else:
                spans.append("all")

            volume = row["reps"] * row["weight"] * row["num_sets"]

            for span in spans:
                group = row["group_name"]
                if group not in data[span]:
                    data[span][group] = deepcopy(empty) | {
                        "targets": {}
                    }

                exercise_id = row["exercise_id"]
                if exercise_id not in added_exercise_groups[span]:
                    added_exercise_groups[span][exercise_id] = []

                if group not in added_exercise_groups[span][exercise_id]:
                    data[span][group]["volume"] += volume
                    data[span][group]["sets"] += row["num_sets"]
                    data[span][group]["reps"] += row["reps"]
                    added_exercise_groups[span][exercise_id] = group

                target = row["target_name"]
                if target not in data[span][group]["targets"]:
                    data[span][group]["targets"][target] = deepcopy(empty)

                data[span][group]["targets"][target]["volume"] += volume
                data[span][group]["targets"][target]["sets"] += row["num_sets"]
                data[span][group]["targets"][target]["reps"] += row["reps"]
    
        # muscle_maps = await get_muscle_maps()
        # group_to_targets = muscle_maps["group_to_targets"]

        # for span, group_data in data.items():
        #     for group, targets in group_to_targets.items():
        #         if group not in group_data:
        #             group_data[group] = deepcopy(empty) | {
        #                 "targets": {}
        #             }
        #         for target in targets:
        #             if target in group_data[group]["targets"]: continue
        #             group_data[group]["targets"][target] = deepcopy(empty)


        return {
            "data": data
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

@router.get("/volume-frequency")
async def volume_frequency(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()
        
        rows = await conn.fetch(
            """
            select w.started_at, pws.volume
            from workouts w
            inner join previous_workout_stats pws
            on pws.workout_id = w.id
            where w.user_id = $1
            and w.started_at >= now() - interval '28 days'
            """, credentials["user_id"]
        )
        
        days_past_volume = {}
        for history_row in rows:
            days_past = get_days_past(history_row["started_at"])
            if days_past == 0 or days_past > 28: continue
            
            if days_past not in days_past_volume.keys():
                days_past_volume[days_past] = 0
            days_past_volume[days_past] += history_row["volume"]

        return {
            "frequency": days_past_volume
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

@router.get("/online-friends")
async def online_friends(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()
        
        has_friends = await conn.fetchval(
            """
            select exists (
                select 1
                from friends
                where user1_id = $1
                or user2_id = $1
            )
            """, credentials["user_id"]
        )
        if not has_friends:
            return {
                "data": {
                    "has_friends": False,
                    "online_friends": []
                }
            }

        rows = await conn.fetch(
            """
            select of.user_id
            from online_users of
            where of.is_online = true
            and user_id in (
                select user1_id
                from friends
                where user2_id = $1
                union
                select user2_id
                from friends
                where user1_id = $1
            )
            limit 10
            """, credentials["user_id"]
        )
        
        online_friends = []
        for row in rows:
            online_friends.append(str(row["user_id"]))

        return {
            "data": {
                "has_friends": True,
                "online_friends": online_friends
            }
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()