from fastapi import APIRouter

# from app.api.routes.exercises import history

router = APIRouter(prefix="/plan")

# router.include_router(list_all.router)

### PLANNING

# allow user to have active plan + inactive (1 at a time)

# different types of workout
#   muscle groups/targets 
#   upper/lower/full
#   push/pull/legs
#   any/freestyle

# either
#   checklist (unordered checklist of plan items to tick off)
#   list (ordered list to work through)
#   specified days (period = week)
#   target count per rotation (reach a certain threshold per rotation)

# custom rotation
#   basic would be a week
#   OR choose any number of days to rotate through

# custom targets for a plan (optional)
#   number of
#               workouts
#               exercises
#               sets
#               reps
#   volume
#       over period
#       per workout/day
#       per muscle group/target

### Examples

# workout on certain days
# workout X times per week
# workout X times per rotation period
# Mon = push, Wed = pull, Fri = legs
# push, pull, legs, rest (rotation) [4 day period]
# Mon = chest, Tue = les, Wed = all, 

### Building a plan

# choose between workout period (week or custom) or queue type
# assign a workout plan to each day

### 

plan_type = ["day", "checklist", "checklist_constrained", "list", "list_constrained"]

plan = {
    "id": "",
    "user_id": "",
    "name": "",
    "active": True,
    "": ""
}
