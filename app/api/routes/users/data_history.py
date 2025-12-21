from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *
from app.api.routes.exercises.history import timestamp_ms_to_date_str

router = APIRouter()

@router.get("/data/get/history")
async def users_data_get_history(credentials: dict = Depends(verify_token)):
    return {
        "data_history": await data_history(credentials["user_id"])
    }

async def data_history(user_id: str):
    try:
        conn = await setup_connection()

        history = {}
        for key, data_map in user_data_tables_map.items():
            if data_map["table"] == "users": continue

            rows = await conn.fetch(
                f"""
                select *
                from {data_map["table"]}
                where user_id = $1
                order by created_at desc
                """, user_id
            )

            history[key] = {
                "graph": [],
                "table": {
                    "headers": [
                        get_table_header(key),
                        "date"
                    ],
                    "rows": []
                }
            }
            for row in rows:
                value = row[data_map["column"]]
                timestamp_ms = datetime_to_timestamp_ms(row["created_at"])
                history[key]["table"]["rows"].append({
                    get_table_header(key): value,
                    "date": timestamp_ms_to_date_str(timestamp_ms)
                })
                if key not in ["bodyfat", "weight", "height"]: continue
                history[key]["graph"].append({
                    "x": timestamp_ms,
                    "y": value
                })

        return history

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

def get_table_header(key: str) -> str:
    match key:
        case 'height':
            return 'height'
        case 'weight':
            return 'weight'
        case 'goal_status':
            return 'Phase'
        case 'ped_status':
            return 'Natty Status'
        case 'bodyfat':
            return 'Bodyfat %'