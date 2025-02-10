import request from 'supertest'
import app from '../src/server'
import pool from '../src/db'

const clear_users = async () => {
    await pool.query("delete from users");
};

beforeEach(async () => {
    await clear_users();
});

afterEach(async () => {
    await clear_users();
});

describe('Express API Tests', () => {
    it('GET /health should return 200 and status ok', async () => {
        const res = await request(app).get('/health');
        expect(res.status).toBe(200);
        expect(res.body).toEqual({ status: 'ok' });
    });
});

describe('User registration', () => {
    const user_data = {
        email: "test@gmail.com", 
        password: "password", 
        username: "username",
        first_name: "first1", 
        last_name: "last1", 
        gender: "male", 
        height: 180, 
        weight: 90, 
        goal_status: "bulking"
    }

    it('register a new user', async () => {
        await request(app)
            .post("/users/register")
            .send(user_data)
            .expect(200)
    })

    it('register with invalid email', async () => {
        const user_data_copy =  {...user_data};
        user_data_copy.email = "invalid"

        await request(app)
            .post("/users/register")
            .send(user_data)
            .expect(200)
    })

    it('register the same email', async () => {
        const user_data_copy =  {...user_data};
        
        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(200)

        user_data_copy.email = "username2";

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500)
    });

    it('register the same username', async () => {
        const user_data_copy =  {...user_data};
        
        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(200)

        user_data_copy.email = "test2@gmail.com"
        user_data_copy.username = user_data_copy.email.toUpperCase();

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500)
    });

    it('register with invalid gender', async () => {
        const user_data_copy = {...user_data};
        user_data_copy.gender = "none";

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500);
    })

    it('register with invalid gender', async () => {
        const user_data_copy = {...user_data};
        user_data_copy.gender = "none";

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500);
    })

    it('register with invalid height', async () => {
        const user_data_copy = {...user_data};
        user_data_copy.height = 0;

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500);


        user_data_copy.height = 300;

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500);
    })

    it('register with invalid weight', async () => {
        const user_data_copy = {...user_data};
        user_data_copy.weight = 0;

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500);

        user_data_copy.weight = 500;

        await request(app)
            .post("/users/register")
            .send(user_data_copy)
            .expect(500);
    })

})
