import random
from datetime import datetime, timezone

def random_weight():
    return random.randint(1, 200) + random.choice([0, .25, .5, .75])

def random_timestamp():
    now = datetime.now(timezone.utc).timestamp() * 1000
    delta = 1000 * 60 * 60 * 24 * random.randint(1, 400)
    return now - delta