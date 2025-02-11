import { Router } from "express";
import { generate } from "../controllers/auth";

const router = Router();

router.get("/generate", generate);

export default router;