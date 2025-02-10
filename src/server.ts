import express from "express";
import usersRoutes from "./routes/users"

const app = express();

app.use(express.json());

app.use("/users", usersRoutes);

app.get("/health", (req, res) => {
  res.status(200).json({ status: "ok" });
});

export default app;