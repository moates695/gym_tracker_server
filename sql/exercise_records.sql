CREATE TABLE public.exercise_records (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    reps integer NOT NULL,
    weight real NOT NULL,
    age real,
    ped_status public.ped_status_type NOT NULL,
    height real,
    user_weight real
);

ALTER TABLE public.user_codes OWNER TO postgres;

ALTER TABLE public.exercise_records OWNER TO postgres;

ALTER TABLE ONLY public.exercise_records
    ADD CONSTRAINT exercise_records_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.exercise_records
    ADD CONSTRAINT exercise_records_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.exercise_records
    ADD CONSTRAINT exercise_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

GRANT ALL ON TABLE public.exercise_records TO PUBLIC;