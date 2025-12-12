from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Annotated, Optional
import json

from app.api.routes.auth import verify_token
from app.api.middleware.database import setup_connection
from app.api.middleware.misc import *

router = APIRouter()

# user friend workflow
# search for username (those that arent blocked)
# click add to request friend (if request not open)
# other user accepts, denies, blocks request
# blocking user unfriends if friends before

# from homepage, click through to friends page to, 
#   add new friends
#   remove friends
#   look at friends stats?

@router.get("/search")
async def users_search(username: str, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        rows = await conn.fetch(
            """
            select *
            from users
            where id != $1
            and username ilike $2 || '%'
            and id not in (
                select blocked_id
                from blocked_users
                where victim_id = $1
            )
            order by username
            limit 50
            """,
            credentials["user_id"],
            username.strip()
        )

        matches = []
        for row in rows:
            relation = "none"

            is_friend = await conn.fetchval(
                """
                select exists (
                    select 1
                    from friend_requests
                    where requestor_id = $1
                    and target_id = $2
                )    
                """, credentials["user_id"], row["id"]
            )
            if is_friend: relation = "requested"

            is_friend = await conn.fetchval(
                """
                select exists (
                    select 1
                    from friends
                    where (user1_id = $1 and user2_id = $2)
                    or (user1_id = $2 and user2_id = $1)
                )    
                """, credentials["user_id"], row["id"]
            )
            if is_friend: relation = "friend"

            matches.append({
                "id": row["id"],
                "username": row["username"],
                "relation": relation
            })

        return {
            "matches": matches
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

class RequestAdd(BaseModel):
    target_id: str

@router.post("/request/add")
async def users_request_add(req: RequestAdd, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from friend_requests
                where requestor_id = $1
                and target_id = $2
            )
            """,
            req.target_id,
            credentials["user_id"],
        )
        if exists: 
            print("EXISTS")
            return {
                "status": await add_friend(credentials["user_id"], req.target_id)
            }

        await conn.execute(
            """
            insert into friend_requests
            (requestor_id, target_id, request_state)
            values
            ($1, $2, $3)
            """, 
            credentials["user_id"], 
            req.target_id,
            "requested"
        )

        return {
            "status": "requested"
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

class RequestCancel(BaseModel):
    target_id: str

@router.post("/request/cancel")
async def users_request_add(req: RequestCancel, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        await conn.execute(
            """
            delete
            from friend_requests
            where requestor_id = $1
            and target_id = $2
            """, credentials["user_id"], req.target_id
        )

        return {
            "status": "cancelled"
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

class RequestDeny(BaseModel):
    requestor_id: str

@router.post("/request/deny")
async def users_request_add(req: RequestDeny, credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        await conn.execute(
            """
            update friend_requests
            set request_state = 'denied'
            where requestor_id = $1
            and target_id = $2
            """, 
            req.requestor_id,
            credentials["user_id"]
        )

        return {
            "status": "denied"
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()

class AddFriend(BaseModel):
    user1_id: str
    user2_id: str

@router.post("/friends/add")
async def users_friend_add(req: AddFriend, credentials: dict = Depends(verify_token)):
    return {
        "status": await add_friend(req.user1_id, req.user2_id)
    }

async def add_friend(user1_id, user2_id):
    try:
        conn = await setup_connection()
        tx = conn.transaction()
        await tx.start()

        blocked = await conn.fetchval(
            """
            select exists (
                select 1
                from blocked_users
                where  (
                    victim_id = $1 and blocked_id = $2
                ) or (
                    blocked_id = $2 and victim_id = $1
                )
            )
            """, user1_id, user2_id
        )
        if blocked: return "blocked" 

        exists = await conn.fetchval(
            """
            select exists (
                select 1
                from friends
                where (
                    user1_id = $1 and user2_id = $2
                ) or (
                    user1_id = $2 and user2_id = $1
                )
            )
            """, user1_id, user2_id
        )
        if exists: return "existing"
        
        await conn.execute(
            """
            insert into friends
            (user1_id, user2_id)
            values
            ($1, $2)
            """, user1_id, user2_id
        )

        await conn.execute(
            """
            delete
            from friend_requests
            where (
                requestor_id = $1 and target_id = $2
            ) or (
                requestor_id = $2 and target_id = $1
            )
            """, user1_id, user2_id
        )
        print(user1_id)
        print(user2_id)

        await tx.commit()

        return "added"

    except SafeError as e:
        if tx: await tx.rollback()
        raise e
    except Exception as e:
        print(str(e))
        if tx: await tx.rollback()
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()


@router.get("/friends/all")
async def users_friends_all(credentials: dict = Depends(verify_token)):
    try:
        conn = await setup_connection()

        friends = await conn.fetch(
            """
            select f.user1_id user_id, u.username
            from friends f
            inner join users u
            on u.id = f.user1_id
            where f.user2_id = $1
            union
            select f.user2_id user_id, u.username
            from friends f
            inner join users u
            on u.id = f.user2_id
            where f.user1_id = $1
            """, credentials["user_id"]
        )

        return {
            "friends": friends
        }

    except SafeError as e:
        raise e
    except Exception as e:
        print(str(e))
        raise Exception('uncaught error')
    finally:
        if conn: await conn.close()