--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.0

-- Started on 2025-12-21 13:13:58

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
-- TOC entry 364 (class 1259 OID 307426)
-- Name: user_bodyfats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_bodyfats (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    bodyfat real NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.user_bodyfats OWNER TO postgres;

--
-- TOC entry 4965 (class 2606 OID 307432)
-- Name: user_bodyfats user_bodyfats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_bodyfats
    ADD CONSTRAINT user_bodyfats_pkey PRIMARY KEY (id);


--
-- TOC entry 4966 (class 2606 OID 307433)
-- Name: user_bodyfats user_bodyfats_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_bodyfats
    ADD CONSTRAINT user_bodyfats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5122 (class 0 OID 0)
-- Dependencies: 364
-- Name: TABLE user_bodyfats; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_bodyfats TO localuser;
GRANT ALL ON TABLE public.user_bodyfats TO PUBLIC;


-- Completed on 2025-12-21 13:13:58

--
-- PostgreSQL database dump complete
--