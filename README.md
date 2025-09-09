# Gym Tracker API

## Beginning

### Start Server

Activate venv: `source venv/bin/activate && pip install -r requirements.txt`.

**Check/change** environment in `.env`.

Start fastapi server: `python app/main.py`.

Start ngrok: `ngrok http --url=subtly-ample-bluebird.ngrok-free.app 8000`.

Get wsl2 db connection: `cat /etc/resolv.conf | grep nameserver`.

## Design

#### Variations

Variations are like small changes made to an exercise, but not enough to warrant a whole new exercise (visually from FE). For instance 'tricep cable extension' and 'single arm cable tricep extension' are two **different** exercises, but 'tricep cable extension' would have variations of 'wide grip, flat bar', 'medium grip, flat bar', 'close grip, angled bar', 'underhand' etc.

Handling variations:
 - name
    - is the varation description e.g. 'wide grip'
    - on FE appears under the exercise name

## TODO

- Add global leaderboards
- Ability to compare exercises to global and friends (details laters)
- Able to compare directly to another friend (details later)
- Settings page
    - profile visiblity
    - colour mode
    - units
    - notifications

## Assumptions