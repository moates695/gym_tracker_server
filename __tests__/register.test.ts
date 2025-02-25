import request from 'supertest'
import app from '../src/server'
import pool from '../src/db'
import jwt from 'jsonwebtoken';

const clear_users = async () => {
  await pool.query(`delete from users`);
};

beforeEach(async () => {
  await clear_users();
});

afterEach(async () => {
  await clear_users();
});

const user_data = {
  email: "test@jest.com", 
  password: "Password!", 
  username: "jest",
  first_name: "first1", 
  last_name: "last1", 
  gender: "male", 
  height: 180, 
  weight: 90, 
  goal_status: "bulking",
  send_email: false
}

describe('User registration', () => {
  it('register a new user', async () => {
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200)
  })

  it('register with invalid email', async () => {
    const user_data_copy =  {...user_data};
    user_data_copy.email = "invalid@gmail"

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid email")
      })
  })

  it('register the same email', async () => {
    const user_data_copy =  {...user_data};
    
    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(200)

    user_data_copy.username = "jest2";
    user_data_copy.email = user_data_copy.email.toUpperCase();

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("email already in use")
      })
  });

  it('register the same username', async () => {
    const user_data_copy =  {...user_data};
      
    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(200)

    user_data_copy.email = "test2@jest.com"
    user_data_copy.username = user_data_copy.username.toUpperCase();

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("username already in use")
      })
  });

  it('different passwords', async () => {
    const user_data_copy = {...user_data};
    user_data_copy.password = "";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("password does not meet complexity requirements")
      })

    user_data_copy.password = "aaaaaaa";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("password does not meet complexity requirements")
      })

    user_data_copy.password = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("password does not meet complexity requirements")
      })

    user_data_copy.password = "Password1";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("password does not meet complexity requirements")
      })

    user_data_copy.password = "Aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa1!";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(200)
  })

  it('register with invalid gender', async () => {
    const user_data_copy = {...user_data};
    user_data_copy.gender = "none";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid gender")
      })
  })

  it('register with invalid height', async () => {
    const user_data_copy = {...user_data};
    user_data_copy.height = 0;

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid height")
      })

    user_data_copy.height = 300;

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid height")
      })
  })

  it('register with invalid weight', async () => {
    const user_data_copy = {...user_data};
    user_data_copy.weight = 0;

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid weight")
      })

    user_data_copy.weight = 500;

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid weight")
      })
  })

  it('register with invalid goal_status', async () => {
    const user_data_copy = {...user_data};
    user_data_copy.goal_status = "none";

    await request(app)
      .post("/register/new")
      .send(user_data_copy)
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("invalid goal_status")
      })
  })

})

describe('User verification', () => {
  it('correct verification', async () => {
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200);

    const email = user_data.email;


    const response1 = await pool.query(`select is_verified
      from users
      where email = $1;`, [email]);
      
    expect(!response1.rows[0].is_verified)

    const token = jwt.sign({ email }, process.env.SECRET_KEY!, { expiresIn: '1m' });
    await request(app)
      .get("/register/verify")
      .query({
        token: token
      })
      .expect(200)

    const response2 = await pool.query(`select is_verified
      from users
      where email = $1;`, [email]);

    expect(response2.rows[0].is_verified)

  })

  it('expired verification', async () => {
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200);

    const email = user_data.email;

    const response1 = await pool.query(`select is_verified
      from users
      where email = $1;`, [email]);
      
    expect(!response1.rows[0].is_verified)

    const token = jwt.sign({ email }, process.env.SECRET_KEY!, { expiresIn: '0m' });
    await request(app)
      .get("/register/verify")
      .query({
        token: token
      })
      .expect(400)

    const response2 = await pool.query(`select is_verified
      from users
      where email = $1;`, [email]);

    expect(!response2.rows[0].is_verified)

  })

  it("incorrect token", async () => {
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200)

    const email = user_data.email;
    
    const response1 = await pool.query(`select is_verified
      from users
      where email = $1;`, [email]);
            
    expect(!response1.rows[0].is_verified);
    
    const token = jwt.sign({ email: "not-email" }, process.env.SECRET_KEY!, { expiresIn: '1m' });
    await request(app)
      .get("/register/verify")
      .query({
        token: token
      })
      .expect(400)

    const response2 = await pool.query(`select is_verified
      from users
      where email = $1;`, [email]);

    expect(!response2.rows[0].is_verified)

  })

})

describe("Email in use", () => {
  it("valid requests", async () => {
    await request(app)
      .get("/register/email_in_use")
      .query({
        "email": user_data.email
      })
      .expect(res => {
        expect(res.status).toBe(200);
        expect(res.body.in_use).toBe(false);
      })
    
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200)

    await request(app)
      .get("/register/email_in_use")
      .query({
        "email": user_data.email
      })
      .expect(res => {
        expect(res.status).toBe(200)
        expect(res.body.in_use).toBe(true)
      })
  })

  it("incorrect params", async () => {
    await request(app)
      .get("/register/email_in_use")
      .query({
        "key": "value" 
      })
      .expect(500)

    await request(app)
      .get("/register/email_in_use")
      .query({
        "email": "" 
      })
      .expect(500)
  })
})

describe("Username in use", () => {
  it("valid requests", async () => {
    await request(app)
      .get("/register/username_in_use")
      .query({
        "username": user_data.username
      })
      .expect(res => {
        expect(res.status).toBe(200)
        expect(res.body.in_use).toBe(false)
      })

    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200)

    await request(app)
      .get("/register/username_in_use")
      .query({
        "username": user_data.username
      })
      .expect(res => {
        expect(res.status).toBe(200)
        expect(res.body.in_use).toBe(true)
      })
  })

  it("incorrect params", async () => {
    await request(app)
      .get("/register/username_in_use")
      .query({
        "key": "value" 
      })
      .expect(500)

    await request(app)
      .get("/register/username_in_use")
      .query({
        "username": "" 
      })
      .expect(500)
  })
})
