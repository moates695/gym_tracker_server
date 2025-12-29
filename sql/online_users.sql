
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
-- TOC entry 4966 (class 2606 OID 241772)
-- Name: overall_leaderboard overall_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.overall_leaderboard
    ADD CONSTRAINT overall_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;
