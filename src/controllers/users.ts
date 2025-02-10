import { Request, Response } from 'express';
import pool from '../db';
import validator from 'email-validator';
import { transporter } from '../server';
import jwt from 'jsonwebtoken';

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
    goal_status,
    send_email = true
  } = req.body;

  if (!validator.validate(email)) {
    res.status(400).send('invalid email');
    return;
  } else if (height <= 0 || height >= 300) {
    res.status(400).send('invalid height');
    return;
  } else if (weight <= 0 || weight >= 500) {
    res.status(400).send('invalid weight');
    return;
  }

  try {
    await pool.query(`insert into users
(email, password, username, first_name, last_name, gender, height, weight, goal_status)
values
($1, $2, $3, $4, $5, $6, $7, $8, $9);`,
      [email, password, username, first_name, last_name, gender, height, weight, goal_status]
    );

    if (send_email) {
      const token = jwt.sign({ email }, process.env.SECRET_KEY!, { expiresIn: '15m' });
      const verificationLink = `${process.env.SERVER_ADDRESS}:${process.env.SERVER_PORT}/users/verify?token=${token}`;

      const mailOptions = {
        to: email,
        subject: 'Email Verification: Gym Tracker',
        text: `Please verify your email by clicking on the link: ${verificationLink}`,
      };

      transporter.sendMail(mailOptions, (error, info) => {
        if (error) {
          console.log(error);
          return res.status(500).send('Error sending email.');
        }
        console.log('Email sent: ' + info.response);
      });
    }

    res.status(200).send();
    
  } catch (error) {
    console.log(error)
    res.status(500).send('error registering user');
  }
};

export const verify = async (req: Request, res: Response) => {
  const token = req.query.token as string;

  let decoded;
  try {
    decoded = jwt.verify(token, process.env.SECRET_KEY!) as { email: string };
  } catch (error) {
    res.status(400).send('Invalid or expired token.');
  }

  try {
    await pool.query(`update users
set is_verified = true
where email = $1;`, [decoded!.email]);
    
  } catch (error) {
    res.status(500).send('User data not updated.')
  }

  res.send(`Email ${decoded!.email} verified successfully!`);

};