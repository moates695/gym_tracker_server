
CREATE TABLE public.online_users (
    user_id uuid NOT NULL,
    is_online boolean NOT NULL
);


ALTER TABLE public.online_users OWNER TO postgres;

--
-- TOC entry 4966 (class 2606 OID 315579)
-- Name: online_users online_users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.online_users
    ADD CONSTRAINT online_users_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4967 (class 2606 OID 315580)
-- Name: online_users online_users_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.online_users
    ADD CONSTRAINT online_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;