import { Router } from "express";
import { generate } from "../controllers/token";

const router = Router();

router.get("/generate", generate);

export default router;