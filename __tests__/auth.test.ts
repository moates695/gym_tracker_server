import request from 'supertest'
import app from '../src/server'
import pool from '../src/db'
import jwt from 'jsonwebtoken'

// todo maybe beforeAll, afterAll instead?

const clear_users = async () => {
  await pool.query(`delete
    from users
    where email ilike '%@jest.com'`
  );
};

beforeEach(async () => {
  await clear_users();
});

afterEach(async () => {
  await clear_users();
});

const user_data = {
  email: "test@jest.com", 
  password: "password", 
  username: "jest",
  first_name: "first1", 
  last_name: "last1", 
  gender: "male", 
  height: 180, 
  weight: 90, 
  goal_status: "bulking",
  send_email: false
}

describe("Authorisation tests", () => {
  it("Correct flow", async () => {
    await request(app)
      .post("/users/register")
      .send(user_data)
      .expect(200) 

    await pool.query(`update users
      set is_verified = true
      where email = $1`, [user_data.email])

    const response1 = await request(app)
      .get("/token/generate")
      .send({
        email: user_data.email,
        password: user_data.password
      })
      .expect(200)
    
    const decoded = jwt.verify(response1.body.token, process.env.SECRET_KEY!) as { email: string };
    expect(decoded.email === user_data.email);
  })
})