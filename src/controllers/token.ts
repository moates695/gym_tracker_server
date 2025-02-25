import { Request, Response } from "express";
import pool from "../db";
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';

export const generate = async (req: Request, res: Response) => {
  const {
    email,
    password
  } = req.body;

  let hashed_password;
  try {
    const response1 = await pool.query(`select password
      from users
      where email = $1`, [email]
    );

    if (response1.rows.length === 0) {
      res.status(400).send("email does not exist");
      return;
    }

    hashed_password = response1.rows[0].password;

  } catch (error) {
    res.status(500).send();
    return; 
  }

  if (!await bcrypt.compare(password, hashed_password)) {
    res.status(400).send("password is invalid");
    return;
  }

  const token = jwt.sign({ email }, process.env.SECRET_KEY!, { expiresIn: '30m' });
  res.status(200).send({ token });

};