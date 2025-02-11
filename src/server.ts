import express from "express";
import usersRoutes from "./routes/users"
import authRoutes from "./routes/auth"
import nodemailer from 'nodemailer';

const app = express();

app.use(express.json());

app.use("/users", usersRoutes);
app.use("/token", authRoutes);

app.get("/health", (req, res) => {
  res.status(200).json({ status: "ok" });
});

export const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.EMAIL,
    pass: process.env.EMAIL_PWD,
  },
});

export default app;