import express from "express";
import registerRoutes from "./routes/register"
import tokenRoutes from "./routes/token"
import nodemailer from 'nodemailer';

const app = express();

app.use(express.json());

app.use("/register", registerRoutes);
app.use("/token", tokenRoutes);

export const transporter = nodemailer.createTransport({
  service: 'gmail',
  auth: {
    user: process.env.EMAIL,
    pass: process.env.EMAIL_PWD,
  },
});

export default app;