# Gym Tracker API

## Beginning

### Start Server

Activate venv: `source venv/bin/activate && pip install -r requirements.txt`.

**Check/change** environment in `.env`.

Start fastapi server: `python app/main.py`.

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

## Assumptions