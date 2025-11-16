from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from fastapi.security import HTTPBearer
from copy import deepcopy
import math

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token
from app.api.middleware.misc import *

router = APIRouter()
security = HTTPBearer()

@router.get("/history")
async def exercise_history(exercise_id: str, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select w.id workout_id, wsd.reps, wsd.weight, wsd.num_sets, wsd.order_index set_order_index, w.started_at
            from workout_set_data wsd
            inner join workout_exercises we
            on wsd.workout_exercise_id = we.id
            inner join workouts w
            on we.workout_id = w.id
            where w.user_id = $1
            and we.exercise_id = $2
            order by w.started_at desc, we.order_index, wsd.order_index
            """, credentials["user_id"], exercise_id 
        )

        n_rep_max_all_time = build_n_rep_max_all_time(rows)
        n_rep_max_history = build_n_rep_max_history(rows)
        volume_workout = build_volume_workout(rows)
        volume_timespan = build_volume_timespan(rows)
        history = build_history(rows)
        reps_sets_weight = build_reps_sets_weight(rows)

    except HTTPException as e:
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Uncaught exception")
    finally:
        if conn: await conn.close()

    return {
        "n_rep_max": {
            "all_time": n_rep_max_all_time,
            "history": n_rep_max_history
        },
        "volume": {
            "workout": volume_workout,
            "timespan": volume_timespan
        },
        "history": history,
        "reps_sets_weight": reps_sets_weight
    }

emptyBaseData = {
    "graph": [],
    "table": {
        "headers": [],
        "rows": []
    }
}

def build_n_rep_max_all_time(rows):
    n_rep_max_all_time_data = {}
    for row in rows:
        curr_max = n_rep_max_all_time_data.get(row["reps"], {"weight": -math.inf})["weight"]
        if row["weight"] <= curr_max: continue
        n_rep_max_all_time_data[row["reps"]] = {
            "weight": row["weight"],
            "timestamp": datetime_to_timestamp_ms(row["started_at"])
        }

    n_rep_max_all_time_data = dict(sorted(n_rep_max_all_time_data.items()))

    n_rep_max_all_time = deepcopy(emptyBaseData)
    n_rep_max_all_time["table"]["headers"] = ["rep", "weight", "date"]
    for rep, data in n_rep_max_all_time_data.items():
        n_rep_max_all_time["graph"].append({
            "x": rep,
            "y": data["weight"]
        })
        n_rep_max_all_time["table"]["rows"].append({
            "rep": rep,
            "weight": data["weight"],
            "date": timestamp_ms_to_date_str(data["timestamp"])
        })

    return n_rep_max_all_time 

def build_n_rep_max_history(rows):
    n_rep_max_history_data = {}
    for row in rows:
        if row["reps"] not in n_rep_max_history_data.keys():
            n_rep_max_history_data[row["reps"]] = {}
        timestamp = datetime_to_timestamp_ms(row["started_at"])
        curr_weight = n_rep_max_history_data[row["reps"]].get(timestamp, -math.inf)
        if curr_weight >= row["weight"]: continue
        n_rep_max_history_data[row["reps"]][timestamp] = row["weight"]

    n_rep_max_history_data = dict(sorted(n_rep_max_history_data.items()))

    n_rep_max_history = {}
    for rep, data in n_rep_max_history_data.items():
        temp_history = deepcopy(emptyBaseData)
        temp_history["table"]["headers"] = ["weight", "date"]

        for timestamp, weight in data.items():
            temp_history["graph"].append({
                "x": timestamp,
                "y": weight
            })
            temp_history["table"]["rows"].append({
                "weight": weight,
                "date": timestamp
            })

        temp_history["graph"] = sort_timeseries(temp_history["graph"], "x")
        temp_history["table"]["rows"] = sort_timeseries(temp_history["table"]["rows"], "date", True)

        n_rep_max_history[rep] = temp_history

    return n_rep_max_history

def build_volume_workout(rows):
    volume_data = volume_per_workout(rows)

    volume = deepcopy(emptyBaseData)
    volume["table"]["headers"] = ["volume", "date"]
    for data in volume_data.values():
        volume["graph"].append({
            "x": data["timestamp"],
            "y": data["volume"]
        })
        volume["table"]["rows"].append({
            "volume": data["volume"],
            "date": data["timestamp"]
        })

    volume["graph"] = sort_timeseries(volume["graph"], "x")
    volume["table"]["rows"] = sort_timeseries(volume["table"]["rows"], "date", True)

    return volume

def build_volume_timespan(rows):
    volume_data = volume_per_workout(rows)

    timespan_data = {}    
    now_ms = datetime.now(tz=timezone.utc).timestamp() * 1000
    for timespan in ["week","month","3_months","6_months","year"]:  
        timespan_ms = timespan_to_ms(timespan)
        bucket_data = {}
        for workout_data in volume_data.values():
            bucket = int((now_ms - workout_data["timestamp"]) / timespan_ms)
            if bucket not in bucket_data:
                bucket_data[bucket] = 0
            bucket_data[bucket] += workout_data["volume"]
        timespan_data[timespan] = dict(sorted(bucket_data.items()))

    volume_timespan = {}
    for timespan, bucket_data in timespan_data.items():
        timespan_ms = timespan_to_ms(timespan)
        temp_data = deepcopy(emptyBaseData)
        temp_data["table"]["headers"] = ["volume", "dates"]
        for bucket, volume in bucket_data.items():
            upper_timestamp = now_ms - bucket * timespan_ms
            lower_timestamp = now_ms - (bucket + 1) * timespan_ms

            temp_data["graph"].append({
                "x": upper_timestamp,
                "y": volume
            })
            temp_data["table"]["rows"].append({
                "volume": volume,
                "dates": f"{timestamp_ms_to_date_str(lower_timestamp)}-{timestamp_ms_to_date_str(upper_timestamp)}"
            })

        volume_timespan[timespan] = temp_data

    return volume_timespan

def volume_per_workout(rows):
    volume_data = {}
    for row in rows:
        if row["workout_id"] not in volume_data:
            volume_data[row["workout_id"]] = {
                "volume": 0,
                "timestamp": datetime_to_timestamp_ms(row["started_at"])
            }
        volume_data[row["workout_id"]]["volume"] += row["reps"] * row["weight"] * row["num_sets"]
    return volume_data

def timespan_to_ms(timespan):
    day_ms = 24 * 60 * 60 * 1000
    week_ms = 7 * day_ms
    month_ms = 30.43 * day_ms
    month_3_ms = 3 * month_ms
    month_6_ms = 2 * month_3_ms
    year_ms = 365.25 * day_ms

    match timespan:
        case 'week':
            return week_ms
        case 'month':
            return month_ms
        case '3_months':
            return month_3_ms
        case '6_months':
            return month_6_ms
        case 'year':
            return year_ms
        case _:
            raise Exception(f"unknown timespan '{timespan}'")

def build_history(rows):
    history_data = {}
    for row in rows:
        if row["workout_id"] not in history_data:
            history_data[row["workout_id"]] = {
                "graph": {
                    "weight_per_set": [],
                    "volume_per_set": [],
                    "weight_per_rep": [],
                },
                "table": {
                    "headers": ["reps", "weight", "sets"],
                    "rows": []
                },
                "started_at": date_to_timestamp_ms(row["started_at"]),
            }

        graph = history_data[row["workout_id"]]["graph"]
        prev_set_idx = 0 if len(graph["weight_per_set"]) == 0 else graph["weight_per_set"][-1]["x"]
        for i in range(row["num_sets"]):
            graph["weight_per_set"].append({
                "x": prev_set_idx + i + 1,
                "y": row["weight"]
            })

            graph["volume_per_set"].append({
                "x": prev_set_idx + i + 1,
                "y": row["reps"] * row["weight"] * row["num_sets"]
            })

            prev_rep_idx = 0 if len(graph["weight_per_rep"]) == 0 else graph["weight_per_rep"][-1]["x"]
            for j in range(row["reps"]):
                graph["weight_per_rep"].append({
                    "x": prev_rep_idx + j + 1,
                    "y": row["weight"]
                })
        
        history_data[row["workout_id"]]["table"]["rows"].append({
            "reps": row["reps"],
            "weight": row["weight"],
            "sets": row["num_sets"]
        })
    
    return sorted(history_data.values(), key=lambda e: e["started_at"], reverse=True)

def build_reps_sets_weight(rows):
    points = []
    for row in rows:
        points.append({
            "x": row["reps"],
            "y": row["weight"],
            "z": row["num_sets"]
        })
    return points

def sort_timeseries(data, key, convert_timestamp=False):
    series = sorted(data, key=lambda e: e[key], reverse=True)
    if not convert_timestamp: return series
    for elem in series:
        elem[key] = timestamp_ms_to_date_str(elem[key])
    return series

def timestamp_ms_to_date_str(timestamp_ms):
    return datetime.fromtimestamp(timestamp_ms / 1000).strftime("%d/%m/%Y")


