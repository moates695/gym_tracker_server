# Gym Tracker API

## Users

### POST `/users/register`

```javascript
req.json = {
    email,
    password, // already hashed
    username, // unique, case insensitive
    first_name,
    last_name,
    gender, // male, female, other
    height: number, // cm: 0 < height < 300
    weight: number, // kg: 0 < weight < 500
    goal_status // bulking, cutting, maintaining
}

res = {}
```

Assumptions, 
- `[email, username, first_name, last_name]` are `length > 0`
- `password` is already hashed by `bycrypt`
- `gender` & `goal_status` are values of db enum
