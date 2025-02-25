import { Router } from "express";
import { email_in_use, register, username_in_use, verify } from "../controllers/register";

const router = Router();

router.post("/new", register);
router.get("/verify", verify);
router.get("/email_in_use", email_in_use);
router.get("/username_in_use", username_in_use);

export default router;