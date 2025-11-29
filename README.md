# Gym Tracker API

## Beginning

### Start Server

Activate venv: `source venv/bin/activate && pip install -r requirements.txt`.

**Check/change** environment in `.env`.

Start fastapi server: `python -m app.main`.

Start ngrok: `ngrok http --url=subtly-ample-bluebird.ngrok-free.app 8000`.

Get wsl2 db connection: `cat /etc/resolv.conf | grep nameserver`.

## Design

#### Users

Fields
- email:
    - must match email regex
    - cannot be ilike another registered email
- password
    - 8 <= length <= 36
    - at least 
        - 1 upper case
        - 1 number
        - 1 special char
- username
    - 1 <= length <= 20
- first_name
    - 1 <= length <= 255
- last_name
    - 1 <= length <= 255
- gender
    - male, female, other
- is_verified
    - has the users email been verified yet?

Weight, user goals, ped status and height are all timeseries values.

#### Variations

Variations are like small changes made to an exercise, but not enough to warrant a whole new exercise (visually from FE). For instance 'tricep cable extension' and 'single arm cable tricep extension' are two **different** exercises, but 'tricep cable extension' would have variations of 'wide grip, flat bar', 'medium grip, flat bar', 'close grip, angled bar', 'underhand' etc.

Handling variations:
- name
    - is the varation description e.g. 'wide grip'
    - on FE appears under the exercise name
- is_body_weight
    - same as parent exercise
- user_id
    - allow users to create variations of default exercises
- description
    - FE auto fill with parent description, allow edits
    - BE treat as different field
- weight_type
    - same as parent exercise
- parent_id
    - id of parent exercise
- muscle_targets
    - if empty/undefined in config json, use parents
    - else use defined

On FE, show variations with the parent exercise, most likely an expand option next to exercises that have variations, from there, the only difference in appearance/function will be that a variation has a secondary name attached to it.

#### Body Weight

Body weight exercises are designated a ratio of body weight that they use. We use the following ratios to determine it:
- upper:lower body weight ratio
    - men: 60:40
    - women: 50:50
- center of mass:
    - men: 56.5% height
    - women: 54.5% height
- arm socket: 82% height

## TODO

- Add global leaderboards
    - total volume
    - total sets
    - total reps
    - volume, reps, sets per exercise
    - rep max comparisons
    - filter by gender, age, weight
- Ability to compare exercises to global and friends (details laters)
- Able to compare directly to another friend (details later)
- Settings page
    - profile visiblity
    - colour mode
    - units
    - notifications
- visual weight calculator (plates + bar)
- weight tracker via entries (graph)
- body fat tracker via entries (graph)
- weight + body weight goals
- show user goals as timeline of switching between
- if user declares unnatural, should this be unable to switch back from?
- lifting goals
    - weight
    - number of workouts
    - time, etc
- workout planner (whole new shite)
- exercise comparisons (volume, sets, reps, number of workouts with them)
- muscle group octagon thing for different measures
- verified users
    - just use other apps that have them verified (insta etc)
- determine ordering for events from frontend to backend
- determine where volume ratio is applied for incoming / outgoing
- determine how to calculate body weight exercises
    - on save should reflect the body weight lifted by user at that time
- add legend to graphs
- add current bar or points to graph
- allow 1 point on graph?
- determine what happens if more than 1 workout on a given day (or similar for graph)
- calculater history points on server (just sort on browser?)
- for body weight, if offset weight makes < 0, just count as zero weight total?
- how to handle >1 of things on the same day, like exercises returned in history (data and graph options).
- check useEffects for bad object comparisons (objects, lists always false comparison)
- add calesthenics weight type
- where possible look to store info on save, instead of on request (e.g. workout overview stats can be stored on workout save and then retrieved later)
- create script to populate workouts for a test user (moates695@gmail.com)
- on log out, clear data from store (FE)
- CHECK key={i} being used correctly, switch to identifier for components
- variations need ratios as well (for bodyweight exercises) [+write tests]
- on FE use a helper function for bodyweights?
- make local script to update database totals based on saved workout data?
- add bar graph to ExerciseData.tsx
- CHECK FOR fetches/functions with potential errors that dont have try catch
- consolidate functions in register, workout_save and existing_users_db for inserting starting values into tables that track overall progress
- show large numbers concisely on frontend
- create a database purely for testing, that can be torn down at will (pytest db), include read only tests for other environments
- in leaderboards page, highlight friends in leaderboard (if visible)
- in leaderboards, show friends ranks and maybe also on graph (if many friends may select some to view?)
- leaderboard ranks (based on top percentage, do this per leaderboard per metric or use a weighting)
- do a heatmap based on muscle ranking, maybe volume total, or volume per week?
- on favourite workouts page, use colour highlight on each row to show comparitive difference between exercise and chosen metric
- use traceback on all exceptions
- use transactions for async pg, and auto rollback on exception
```python
tx = conn.transaction()
await tx.start()
try:
    await conn.execute("INSERT INTO ...")
    raise Exception("error")
    await tx.commit()
except:
    await tx.rollback()
```
- alter search filter to return exact first, then divideder line, then partial matches
- check if <StatusBar style='dark'/>, works on each page?
- ERROR, cannot save workout (maybe out of date build)
- error getting /stats/history, `'NoneType' object is not subscriptable`
- when shown start screen options, ask for confirmation before starting new workout
- add API for users, they sign on with email password or 1 time code. Create routes for them to export data (will be GET only, no adding/updating/deleting data directly)
- REDIS: update on workout save, then timer trigger sync with postgres (external lambda?)
- asynpg, use named paramaters instead of $1, $2, ... where apprporiate
- on FE, load in fonts before putting user on main screen
- BE to FE, probably shouldn't return a temp token to the FE, as then users can bypass email verification by sending the temp token straight to the API. Temp token should be sent to the email only?
- FE, dont allow sign in next button if errors in email, password or username. Also check for email like username if in use.

## Assumptions

### AWS sheninigans

#### Lambda Containers

When building set `--provenance=false`, otherwise image is "source image... is not supported"