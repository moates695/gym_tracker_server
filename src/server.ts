import express from "express";
// import pool from './db';
import usersRoutes from "./routes/users"

const app = express();

app.use(express.json());

// app.post("/users/register", async (req, res) => {
// });

app.use("/users", usersRoutes);

app.get("/health", (req, res) => {
  res.status(200).json({ status: "ok" });
});

export default app;