import { Request, Response } from 'express';
import pool from '../db';
// import isEmail from 'validator/lib/isEmail';
import validator from 'validator';
import { transporter } from '../server';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcrypt';

export const register = async (req: Request, res: Response) => {
  const required_fields = [
    "email", 
    "password",
    "username",
    "first_name", 
    "last_name", 
    "gender",
    "height",
    "weight",
    "goal_status",
  ]

  const is_valid = required_fields.filter(field => !(field in req.body));
  if (is_valid.length > 0) {
    res.status(400).send(`required fields are missing`);
    return;
  }

  const send_email = req.body["send_email"] ? req.body["send_email"] : false;

  if (!validator.isEmail(req.body["email"])) {
    res.status(400).send('invalid email');
    return;
  } else if (req.body["height"] <= 0 || req.body["height"] >= 300) {
    res.status(400).send('invalid height');
    return;
  } else if (req.body["weight"] <= 0 || req.body["weight"] >= 500) {
    res.status(400).send('invalid weight');
    return;
  } else if (!["male", "female", "other"].includes(req.body["gender"])) {
    res.status(400).send('invalid gender');
    return;
  } else if (!["bulking", "cutting", "maintaining"].includes(req.body["goal_status"])) {
    res.status(400).send('invalid goal_status');
    return;
  }

  if (
    !validator.isLength(req.body["password"], { min: 8, max: 36 }) ||
    !/[A-Z]/.test(req.body["password"]) ||
    !/[^a-zA-Z0-9]/.test(req.body["password"])
  ) {
    res.status(400).send('password does not meet complexity requirements');
    return;
  }

  // const passwordSchema = z.string()
  //   .min(8, "Password must be at least 8 characters")
  //   .max(37, "Password must not exceed 36 characters")
  //   .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
  //   .regex(/[^a-zA-Z0-9]/, "Password must contain at least one special character");

  // if (passwordSchema.safeParse(req.body["password"]).success) {
  //   res.status(400).send('password does not meet complexity requirements');
  //   return;
  // }



  if (await is_email_in_use(req.body["email"])) {
    res.status(400).send('email already in use');
    return;
  }

  if (await is_username_in_use(req.body["username"])) {
    res.status(400).send('username already in use');
    return;
  }

  const hashed_password = await bcrypt.hash(req.body["password"], 10);

  try {
    await pool.query(`insert into users
(email, password, username, first_name, last_name, gender, height, weight, goal_status)
values
($1, $2, $3, $4, $5, $6, $7, $8, $9);`,
      [req.body["email"], hashed_password, req.body["username"], req.body["first_name"], req.body["last_name"], req.body["gender"], req.body["height"], req.body["weight"], req.body["goal_status"]]
    );

    if (send_email) {
      const token = jwt.sign({ "email": req.body["email"] }, process.env.SECRET_KEY!, { expiresIn: '15m' });
      const link = `${process.env.SERVER_ADDRESS}:${process.env.SERVER_PORT}/users/verify?token=${token}`;

      const mailOptions = {
        to: req.body["email"],
        subject: 'Email Verification: Gym Tracker',
        text: `Please verify your email by clicking on the link: ${link}`,
      };

      transporter.sendMail(mailOptions, (error, info) => {
        if (error) {
          console.log(error);
          res.status(500).send('error sending email');
          return;
        }
        console.log('email sent: ' + info.response);
      });
    }

    res.status(200).send();
    return;

  } catch (error) {
    console.log(error);
    res.status(500).send('error registering user');
    return;
  }
};

export const verify = async (req: Request, res: Response) => {
  const token = req.query.token as string;

  let decoded;
  try {
    decoded = jwt.verify(token, process.env.SECRET_KEY!) as { email: string };
  } catch (error) {
    res.status(400).send('Invalid or expired token.');
    return;
  }
    
  try {
    const response1 = await pool.query(`select exists (
select 1
from users
where email = $1
and is_verified = false
);`, [decoded.email]);

    if (!response1.rows[0].exists) {
      res.status(400).send("Email not found.");
      return;
    }

  } catch (error) {
    console.log(error)
    res.status(500).send();
    return;
  }

  try {
    await pool.query(`update users
set is_verified = true
where email = $1;`, [decoded!.email]);
    
  } catch (error) {
    res.status(500).send('User data not updated.');
    return;
  }

  res.send(`Email ${decoded!.email} verified successfully!`);
  return;

};

export const email_in_use = async (req: Request, res: Response) => {
  if (!req.query.email) {
    res.sendStatus(500);
    return;
  }
  const email = decodeURIComponent(req.query.email as string);

  try {
    res.send({
      "in_use": await is_email_in_use(email)
    })
  } catch (error) {
    console.log(error);
    res.status(500).send("error querying existing emails");
  } 
};

const is_email_in_use = async (email: string): Promise<boolean> => {
  const response1 = await pool.query(`
    select exists (
      select 1
      from users
      where lower(email) = lower($1)
    );`, [email]
  );
  
  return response1.rows[0].exists;
}

export const username_in_use = async (req: Request, res: Response) => {
  if (!req.query.username) {
    res.sendStatus(500);
    return;
  }
  const username = decodeURIComponent(req.query.username as string);

  try {
    res.send({
      "in_use": await is_username_in_use(username)
    })
  } catch (error) {
    console.log(error);
    res.status(500).send("error querying existing usernames")
  }
};

const is_username_in_use = async (username: string) => {
  const response1 = await pool.query(`
    select exists (
      select 1
      from users
      where lower(username) = lower($1)
    );`, [username]
  );
  
  return response1.rows[0].exists;
}