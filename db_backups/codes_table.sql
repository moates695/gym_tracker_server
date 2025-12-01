--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.0

-- Started on 2025-11-30 09:12:59

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
-- TOC entry 359 (class 1259 OID 258221)
-- Name: user_codes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_codes (
    user_id uuid NOT NULL,
    code character(6) NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.user_codes OWNER TO postgres;

--
-- TOC entry 4949 (class 2606 OID 258226)
-- Name: user_codes user_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_codes
    ADD CONSTRAINT user_codes_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4950 (class 2606 OID 258227)
-- Name: user_codes user_codes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_codes
    ADD CONSTRAINT user_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5106 (class 0 OID 0)
-- Dependencies: 359
-- Name: TABLE user_codes; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_codes TO localuser;


-- Completed on 2025-11-30 09:12:59

--
-- PostgreSQL database dump complete
--

