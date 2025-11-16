from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
import re
import json
import smtplib
from email.message import EmailMessage
import os
from datetime import date
import bcrypt
import traceback

from app.api.middleware.database import setup_connection
from app.api.middleware.auth_token import *
from app.api.routes.auth import verify_token, verify_temp_token
from app.api.routes.register.validate import send_validation_email
from app.api.routes.users.get_data import fetch_user_data
from app.api.middleware.misc import *

router = APIRouter()

class Register(BaseModel):
    email: str = email_field
    password: str = password_field
    username: str = Field(min_length=1, max_length=20)
    first_name: str = name_field
    last_name: str = name_field
    gender: gender_literal
    height: float = height_field
    weight: float = weight_field
    goal_status: goal_status_literal
    ped_status: ped_status_literal
    date_of_birth: str
    send_email: bool = True

    @field_validator('password')
    def password_complexity(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter.')
        if not re.search(r'[1-9]', v):
            raise ValueError('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character.')
        return v

# todo: add to workout_totals, workout_muscle_group/target_totals
@router.post("/new")
async def register(req: Register):
    req_json = json.loads(req.model_dump_json())
    
    conn = tx = None
    try:
        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        error_result = {
            "status": "error",
            "fields": []
        }

        for col in ["email", "username"]:
            exists = await conn.fetchval(
                f"""
                select exists (
                    select 1
                    from users
                    where lower({col}) = lower($1)
                )""", req_json[col]
            )
            if not exists: continue
            error_result["fields"].append(col)

        if error_result["fields"] != []:
            return error_result

        hashed_pwd = bcrypt.hashpw(req.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        row = await conn.fetchrow(
            """
            insert into users
            (email, password, username, first_name, last_name, gender, date_of_birth)
            values
            ($1, $2, $3, $4, $5, $6, $7)
            returning id
            """, req.email, hashed_pwd, req.username, req.first_name, req.last_name, req.gender, date.fromisoformat(req.date_of_birth)
        )
        user_id = row["id"]

        for key, data_map in user_data_tables_map.items():
            if data_map["table"] == "users": continue
            await conn.execute(
                f"""
                insert into {data_map["table"]}
                (user_id, {data_map["column"]})
                values
                ($1, $2);
                """, user_id, req_json[key]
            )

        await new_workout_totals(conn, user_id)
        await new_muscle_totals(conn, user_id)
        await new_exercise_totals(conn, user_id)
        
        if req.send_email:
            await send_validation_email(req.email, user_id)

        await tx.commit()

        # todo: dont return temp_token, can be used to sign in without access to email
        return {
            "status": "success",
            "temp_token": generate_token(
                req.email,
                user_id,
                minutes=15,
                is_temp=True
            ),
            "user_id": user_id
        }

    except HTTPException as e:
        if tx: await tx.rollback()
        return JSONResponse(status_code=e.status_code, content={"detail": e.detail})
    except Exception as e:
        print(e)
        traceback.print_exc()
        if tx: await tx.rollback()
        raise HTTPException(status_code=500)
    finally:
        if conn: await conn.close()

async def new_workout_totals(conn, user_id):
    return await conn.fetchrow(
        """
        insert into workout_totals
        (user_id, volume, num_sets, reps, duration, num_workouts, num_exercises)
        values
        ($1, 0.0, 0, 0, 0.0, 0, 0)
        returning *
        """, user_id
    )

async def new_muscle_totals(conn, user_id):
    for key in ["group", "target"]:
        id_rows = await conn.fetch(
            f"""
            select id
            from muscle_{key}s
            """
        )
        for id_row in id_rows:
            await conn.execute(
                f"""
                insert into workout_muscle_{key}_totals
                (user_id, muscle_{key}_id, volume, num_sets, reps, counter)
                values
                ($1, $2, 0.0, 0, 0, 0)
                """, user_id, id_row["id"]
            )

async def new_exercise_totals(conn, user_id):
    exercise_id_rows = await conn.fetch(
        """
        select id
        from exercises
        """
    )
    for exercise_id_row in exercise_id_rows:
        await conn.execute(
            """
            insert into exercise_totals
            (user_id, exercise_id, volume, num_sets, reps, counter)
            values
            ($1, $2, 0.0, 0, 0, 0)
            """, user_id, exercise_id_row["id"]
        )