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