--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.0

-- Started on 2025-11-11 14:53:26

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 367 (class 1259 OID 241768)
-- Name: overall_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.overall_leaderboard (
    user_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    num_exercises integer NOT NULL,
    num_workouts integer NOT NULL,
    duration_mins integer NOT NULL,
    last_updated timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.overall_leaderboard OWNER TO postgres;

--
-- TOC entry 4972 (class 2606 OID 241772)
-- Name: overall_leaderboard overall_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.overall_leaderboard
    ADD CONSTRAINT overall_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5133 (class 0 OID 0)
-- Dependencies: 367
-- Name: TABLE overall_leaderboard; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.overall_leaderboard TO localuser;


-- Completed on 2025-11-11 14:53:26

--
-- PostgreSQL database dump complete
--

