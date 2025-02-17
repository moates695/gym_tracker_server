import request from 'supertest'
import app from '../src/server'
import pool from '../src/db'
import jwt from 'jsonwebtoken'

// todo maybe beforeAll, afterAll instead?

const clear_users = async () => {
  await pool.query(`delete from users;`
  );
};

beforeEach(async () => {
  await clear_users();
});

afterEach(async () => {
  await clear_users();
});

const user_data = {
  email: "test22@jest.com", 
  password: "Password1!", 
  username: "jest22",
  first_name: "first1", 
  last_name: "last1", 
  gender: "male", 
  height: 180, 
  weight: 90, 
  goal_status: "bulking",
  send_email: false
}

describe("Authorisation tests", () => {
  it("valid token request", async () => {
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200) 

    await pool.query(`update users
      set is_verified = true
      where email = $1`, [user_data.email])

    await request(app)
      .get("/token/generate")
      .send({
        email: user_data.email,
        password: user_data.password
      })
      .expect(res => {
        expect(res.status).toBe(200)
        const decoded = jwt.verify(res.body.token, process.env.SECRET_KEY!) as { email: string };
        expect(decoded.email).toBe(user_data.email)
      })
  })

  it("incorrect verified user info", async () => {
    await request(app)
      .post("/register/new")
      .send(user_data)
      .expect(200)
    
    await pool.query(`update users
      set is_verified = true
      where email = $1`, [user_data.email])

    await request(app)
      .get("/token/generate")
      .send({
        email: "none@jest.com",
        password: user_data.password
      })
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("email does not exist")
      })

    await request(app)
      .get("/token/generate")
      .send({
        email: user_data.email,
        password: "invalid"
      })
      .expect(res => {
        expect(res.status).toBe(400)
        expect(res.text).toBe("password is invalid")
      })
  })

})