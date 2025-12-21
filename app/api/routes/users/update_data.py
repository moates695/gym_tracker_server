from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json
from datetime import datetime, timezone

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *
from app.api.routes.users.data_history import data_history

router = APIRouter()

class Update(BaseModel):
    # first_name: Optional[Annotated[str, name_field]] = None
    # last_name: Optional[Annotated[str, name_field]] = None
    # gender: Optional[gender_literal] = None
    height: Optional[Annotated[float, height_field]] = None
    weight: Optional[Annotated[float, weight_field]] = None
    goal_status: Optional[goal_status_literal] = None
    ped_status: Optional[ped_status_literal] = None
    bodyfat: Optional[Annotated[float, bodyfat_field]] = None

@router.post("/data/update")
async def users_weight(req: Update, credentials: dict = Depends(verify_token)):
    req_json = json.loads(req.model_dump_json())

    try:
        conn = await setup_connection()

        for key, value in req_json.items():
            if value is None: continue
            data_map = user_data_tables_map[key]
            await conn.execute(
                f"""
                insert into {data_map["table"]}
                (user_id, {data_map["column"]})
                values
                ($1, $2);
                """, credentials["user_id"], value
            )

        return {
            "status": "good",
            "data_history": await data_history(credentials["user_id"])
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()