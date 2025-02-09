import { Request, Response } from 'express';
import pool from '../db';

export const register = async (req: Request, res: Response) => {
  const {
    email, 
    password,
    username,
    first_name, 
    last_name, 
    gender,
    height,
    weight,
    goal_status 
  } = req.body;
  
  if (height <= 0 || height >= 300) {
    res.status(500).send('invalid height');
    return;
  }
  
  if (weight <= 0 || weight >= 500) {
    res.status(500).send('invalid weight');
    return;
  }

  try {
    const response = await pool.query(`insert into users
(email, password, username, first_name, last_name, gender, height, weight, goal_status)
values
($1, $2, $3, $4, $5, $6, $7, $8, $9)
returning id;`,
      [email, password, username, first_name, last_name, gender, height, weight, goal_status]
    );

    res.json({"id": response.rows[0].id})
    
  } catch (error) {
    console.log(error)
    res.status(500).send('error registering user');
  }
};
