import { Router } from "express";
import { register, verify } from "../controllers/users";

const router = Router();

router.post("/register", register);

router.get("/verify", verify);

export default router;