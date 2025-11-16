--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.0

-- Started on 2025-10-04 12:36:59

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
-- TOC entry 241 (class 1259 OID 163897)
-- Name: bodyweight_exercise_ratios; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.bodyweight_exercise_ratios (
    exercise_id uuid NOT NULL,
    ratio real NOT NULL,
    gender public.user_gender NOT NULL
);


ALTER TABLE public.bodyweight_exercise_ratios OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 41031)
-- Name: exercises; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exercises (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL,
    is_body_weight boolean NOT NULL,
    user_id uuid,
    description text,
    weight_type public.weight_type NOT NULL,
    parent_id uuid
);


ALTER TABLE public.exercises OWNER TO postgres;

--
-- TOC entry 243 (class 1259 OID 163961)
-- Name: exercise_base_variants; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.exercise_base_variants AS
 SELECT e1.id AS base_id,
    e1.name AS base_name,
    e2.id AS variant_id,
    e2.name AS variant_name
   FROM (public.exercises e1
     LEFT JOIN public.exercises e2 ON ((e2.parent_id = e1.id)))
  WHERE (e1.parent_id IS NULL);


ALTER VIEW public.exercise_base_variants OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 24724)
-- Name: users; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.users (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    email text NOT NULL,
    password character varying(255) NOT NULL,
    username text NOT NULL,
    first_name character varying(255) NOT NULL,
    last_name character varying(255) NOT NULL,
    gender public.user_gender NOT NULL,
    is_verified boolean DEFAULT false NOT NULL,
    created_at timestamp with time zone DEFAULT timezone('UTC'::text, now())
);


ALTER TABLE public.users OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 49196)
-- Name: workout_exercises; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workout_exercises (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    workout_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    order_index integer NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.workout_exercises OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 49215)
-- Name: workout_set_data; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workout_set_data (
    workout_exercise_id uuid NOT NULL,
    order_index integer NOT NULL,
    reps integer NOT NULL,
    weight real NOT NULL,
    num_sets integer NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    set_class public.set_class_type DEFAULT 'working'::public.set_class_type NOT NULL
);


ALTER TABLE public.workout_set_data OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 49184)
-- Name: workouts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workouts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    started_at timestamp with time zone NOT NULL,
    duration_secs integer NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.workouts OWNER TO postgres;

--
-- TOC entry 228 (class 1259 OID 65574)
-- Name: exercise_history; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.exercise_history AS
 SELECT w.user_id,
    w.id AS workout_id,
    we.exercise_id,
    wsd.reps,
    wsd.weight,
    wsd.num_sets,
    w.started_at
   FROM (((public.workouts w
     JOIN public.users u ON ((u.id = w.user_id)))
     JOIN public.workout_exercises we ON ((we.workout_id = w.id)))
     JOIN public.workout_set_data wsd ON ((wsd.workout_exercise_id = we.id)));


ALTER VIEW public.exercise_history OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 49348)
-- Name: exercise_muscle_targets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exercise_muscle_targets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    muscle_target_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    ratio integer NOT NULL,
    CONSTRAINT exercise_muscle_targets_ratio_check CHECK (((ratio >= 1) AND (ratio <= 10)))
);


ALTER TABLE public.exercise_muscle_targets OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 49326)
-- Name: muscle_groups; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.muscle_groups (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.muscle_groups OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 49334)
-- Name: muscle_targets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.muscle_targets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    muscle_group_id uuid NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.muscle_targets OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 49365)
-- Name: exercise_muscle_data; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.exercise_muscle_data AS
 SELECT mg.id AS group_id,
    mg.name AS group_name,
    mt.id AS target_id,
    mt.name AS target_name,
    emt.exercise_id,
    emt.ratio
   FROM ((public.muscle_groups mg
     JOIN public.muscle_targets mt ON ((mg.id = mt.muscle_group_id)))
     JOIN public.exercise_muscle_targets emt ON ((mt.id = emt.muscle_target_id)));


ALTER VIEW public.exercise_muscle_data OWNER TO postgres;

--
-- TOC entry 242 (class 1259 OID 163935)
-- Name: exercise_totals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exercise_totals (
    user_id uuid NOT NULL,
    exercise_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    counter integer NOT NULL
);


ALTER TABLE public.exercise_totals OWNER TO postgres;

--
-- TOC entry 253 (class 1259 OID 164065)
-- Name: exercises_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.exercises_leaderboard (
    user_id uuid NOT NULL,
    num_exercises integer NOT NULL,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.exercises_leaderboard OWNER TO postgres;

--
-- TOC entry 244 (class 1259 OID 163973)
-- Name: friends; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.friends (
    user_id1 uuid NOT NULL,
    user_id2 uuid NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    CONSTRAINT ids_not_same CHECK ((user_id1 <> user_id2))
);


ALTER TABLE public.friends OWNER TO postgres;

--
-- TOC entry 234 (class 1259 OID 98389)
-- Name: muscle_groups_targets; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.muscle_groups_targets AS
 SELECT mg.id AS group_id,
    mg.name AS group_name,
    mt.id AS target_id,
    mt.name AS target_name
   FROM (public.muscle_groups mg
     JOIN public.muscle_targets mt ON ((mt.muscle_group_id = mg.id)));


ALTER VIEW public.muscle_groups_targets OWNER TO postgres;

--
-- TOC entry 240 (class 1259 OID 155685)
-- Name: previous_workout_muscle_group_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.previous_workout_muscle_group_stats (
    workout_id uuid NOT NULL,
    muscle_group_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.previous_workout_muscle_group_stats OWNER TO postgres;

--
-- TOC entry 239 (class 1259 OID 147501)
-- Name: previous_workout_muscle_target_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.previous_workout_muscle_target_stats (
    workout_id uuid NOT NULL,
    muscle_target_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.previous_workout_muscle_target_stats OWNER TO postgres;

--
-- TOC entry 238 (class 1259 OID 147493)
-- Name: previous_workout_stats; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.previous_workout_stats (
    workout_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL,
    num_exercises integer NOT NULL
);


ALTER TABLE public.previous_workout_stats OWNER TO postgres;

--
-- TOC entry 249 (class 1259 OID 164034)
-- Name: reps_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.reps_leaderboard (
    user_id uuid NOT NULL,
    reps integer NOT NULL,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.reps_leaderboard OWNER TO postgres;

--
-- TOC entry 247 (class 1259 OID 164018)
-- Name: sets_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.sets_leaderboard (
    user_id uuid NOT NULL,
    num_sets integer NOT NULL,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.sets_leaderboard OWNER TO postgres;

--
-- TOC entry 231 (class 1259 OID 98360)
-- Name: user_goals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_goals (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    goal_status public.user_goal_status NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.user_goals OWNER TO postgres;

--
-- TOC entry 232 (class 1259 OID 98372)
-- Name: user_heights; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_heights (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    height real NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.user_heights OWNER TO postgres;

--
-- TOC entry 230 (class 1259 OID 98348)
-- Name: user_ped_status; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_ped_status (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    ped_status public.ped_status_type NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.user_ped_status OWNER TO postgres;

--
-- TOC entry 229 (class 1259 OID 98336)
-- Name: user_weights; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.user_weights (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    weight real NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.user_weights OWNER TO postgres;

--
-- TOC entry 233 (class 1259 OID 98384)
-- Name: user_data; Type: VIEW; Schema: public; Owner: postgres
--

CREATE VIEW public.user_data AS
 SELECT DISTINCT ON (u.id) u.id,
    u.email,
    u.password,
    u.username,
    u.first_name,
    u.last_name,
    u.gender,
    u.is_verified,
    u.created_at,
    g.goal_status,
    h.height,
    p.ped_status,
    w.weight
   FROM ((((public.users u
     JOIN public.user_goals g ON ((g.user_id = u.id)))
     JOIN public.user_heights h ON ((h.user_id = u.id)))
     JOIN public.user_ped_status p ON ((p.user_id = u.id)))
     JOIN public.user_weights w ON ((w.user_id = u.id)))
  ORDER BY u.id, g.created_at DESC, h.created_at DESC, p.created_at DESC, w.created_at DESC;


ALTER VIEW public.user_data OWNER TO postgres;

--
-- TOC entry 245 (class 1259 OID 163999)
-- Name: volume_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.volume_leaderboard (
    user_id uuid NOT NULL,
    volume real NOT NULL,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.volume_leaderboard OWNER TO postgres;

--
-- TOC entry 235 (class 1259 OID 139311)
-- Name: workout_muscle_group_totals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workout_muscle_group_totals (
    user_id uuid NOT NULL,
    muscle_group_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    counter integer NOT NULL
);


ALTER TABLE public.workout_muscle_group_totals OWNER TO postgres;

--
-- TOC entry 236 (class 1259 OID 139326)
-- Name: workout_muscle_target_totals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workout_muscle_target_totals (
    user_id uuid NOT NULL,
    muscle_target_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    counter integer NOT NULL
);


ALTER TABLE public.workout_muscle_target_totals OWNER TO postgres;

--
-- TOC entry 237 (class 1259 OID 139341)
-- Name: workout_totals; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workout_totals (
    user_id uuid NOT NULL,
    volume real NOT NULL,
    num_sets integer NOT NULL,
    reps integer NOT NULL,
    duration real NOT NULL,
    num_workouts integer NOT NULL,
    num_exercises integer NOT NULL
);


ALTER TABLE public.workout_totals OWNER TO postgres;

--
-- TOC entry 251 (class 1259 OID 164050)
-- Name: workouts_leaderboard; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.workouts_leaderboard (
    user_id uuid NOT NULL,
    num_workouts integer NOT NULL,
    last_updated timestamp without time zone NOT NULL
);


ALTER TABLE public.workouts_leaderboard OWNER TO postgres;

--
-- TOC entry 4936 (class 2606 OID 163901)
-- Name: bodyweight_exercise_ratios bodyweight_exercise_ratios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bodyweight_exercise_ratios
    ADD CONSTRAINT bodyweight_exercise_ratios_pkey PRIMARY KEY (exercise_id, gender);


--
-- TOC entry 4885 (class 2606 OID 32804)
-- Name: users email_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT email_unique UNIQUE (email);


--
-- TOC entry 4912 (class 2606 OID 49354)
-- Name: exercise_muscle_targets exercise_muscle_targets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercise_muscle_targets
    ADD CONSTRAINT exercise_muscle_targets_pkey PRIMARY KEY (id);


--
-- TOC entry 4894 (class 2606 OID 41038)
-- Name: exercises exercises_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT exercises_pkey PRIMARY KEY (id);


--
-- TOC entry 4938 (class 2606 OID 163979)
-- Name: friends friends_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_pkey PRIMARY KEY (user_id1, user_id2);


--
-- TOC entry 4907 (class 2606 OID 49333)
-- Name: muscle_groups muscle_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.muscle_groups
    ADD CONSTRAINT muscle_groups_pkey PRIMARY KEY (id);


--
-- TOC entry 4910 (class 2606 OID 49341)
-- Name: muscle_targets muscle_targets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.muscle_targets
    ADD CONSTRAINT muscle_targets_pkey PRIMARY KEY (id);


--
-- TOC entry 4934 (class 2606 OID 155690)
-- Name: previous_workout_muscle_group_stats previous_workout_muscle_group_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_muscle_group_stats
    ADD CONSTRAINT previous_workout_muscle_group_stats_pkey PRIMARY KEY (workout_id, muscle_group_id);


--
-- TOC entry 4932 (class 2606 OID 147517)
-- Name: previous_workout_muscle_target_stats previous_workout_muscle_target_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_muscle_target_stats
    ADD CONSTRAINT previous_workout_muscle_target_stats_pkey PRIMARY KEY (workout_id, muscle_target_id);


--
-- TOC entry 4930 (class 2606 OID 147515)
-- Name: previous_workout_stats previous_workout_stats_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_stats
    ADD CONSTRAINT previous_workout_stats_pkey PRIMARY KEY (workout_id);


--
-- TOC entry 4914 (class 2606 OID 106531)
-- Name: exercise_muscle_targets unique_exercise_id_muscle_target_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercise_muscle_targets
    ADD CONSTRAINT unique_exercise_id_muscle_target_id UNIQUE (exercise_id, muscle_target_id);


--
-- TOC entry 4896 (class 2606 OID 131110)
-- Name: exercises unique_name; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT unique_name UNIQUE (name, parent_id);


--
-- TOC entry 4900 (class 2606 OID 49214)
-- Name: workout_exercises unique_order_index; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_exercises
    ADD CONSTRAINT unique_order_index UNIQUE (workout_id, order_index);


--
-- TOC entry 4920 (class 2606 OID 98366)
-- Name: user_goals user_goals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_goals
    ADD CONSTRAINT user_goals_pkey PRIMARY KEY (id);


--
-- TOC entry 4922 (class 2606 OID 98378)
-- Name: user_heights user_heights_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_heights
    ADD CONSTRAINT user_heights_pkey PRIMARY KEY (id);


--
-- TOC entry 4918 (class 2606 OID 98354)
-- Name: user_ped_status user_ped_status_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_ped_status
    ADD CONSTRAINT user_ped_status_pkey PRIMARY KEY (id);


--
-- TOC entry 4916 (class 2606 OID 98342)
-- Name: user_weights user_weights_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_weights
    ADD CONSTRAINT user_weights_pkey PRIMARY KEY (id);


--
-- TOC entry 4888 (class 2606 OID 32801)
-- Name: users username_unique; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT username_unique UNIQUE (username);


--
-- TOC entry 4890 (class 2606 OID 24731)
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- TOC entry 4941 (class 2606 OID 164088)
-- Name: volume_leaderboard volume_leaderboard_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.volume_leaderboard
    ADD CONSTRAINT volume_leaderboard_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4902 (class 2606 OID 49202)
-- Name: workout_exercises workout_exercises_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_exercises
    ADD CONSTRAINT workout_exercises_pkey PRIMARY KEY (id);


--
-- TOC entry 4924 (class 2606 OID 139315)
-- Name: workout_muscle_group_totals workout_muscle_group_totals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_muscle_group_totals
    ADD CONSTRAINT workout_muscle_group_totals_pkey PRIMARY KEY (user_id, muscle_group_id);


--
-- TOC entry 4926 (class 2606 OID 139330)
-- Name: workout_muscle_target_totals workout_muscle_target_totals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_muscle_target_totals
    ADD CONSTRAINT workout_muscle_target_totals_pkey PRIMARY KEY (user_id, muscle_target_id);


--
-- TOC entry 4904 (class 2606 OID 49220)
-- Name: workout_set_data workout_set_data_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_set_data
    ADD CONSTRAINT workout_set_data_pkey PRIMARY KEY (workout_exercise_id, order_index);


--
-- TOC entry 4928 (class 2606 OID 139345)
-- Name: workout_totals workout_totals_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_totals
    ADD CONSTRAINT workout_totals_pkey PRIMARY KEY (user_id);


--
-- TOC entry 4898 (class 2606 OID 49190)
-- Name: workouts workouts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workouts
    ADD CONSTRAINT workouts_pkey PRIMARY KEY (id);


--
-- TOC entry 4883 (class 1259 OID 32805)
-- Name: email; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX email ON public.users USING btree (lower(email));


--
-- TOC entry 4891 (class 1259 OID 122926)
-- Name: exercises_name_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX exercises_name_unique ON public.exercises USING btree (lower(name), COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid));


--
-- TOC entry 4892 (class 1259 OID 122923)
-- Name: exercises_name_user_parent_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX exercises_name_user_parent_unique ON public.exercises USING btree (name, COALESCE(user_id, '00000000-0000-0000-0000-000000000000'::uuid), COALESCE(parent_id, '00000000-0000-0000-0000-000000000000'::uuid));


--
-- TOC entry 4944 (class 1259 OID 164073)
-- Name: idx_leaderboard_exercises_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_leaderboard_exercises_desc ON public.exercises_leaderboard USING btree (num_exercises DESC);


--
-- TOC entry 4943 (class 1259 OID 164042)
-- Name: idx_leaderboard_reps_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_leaderboard_reps_desc ON public.reps_leaderboard USING btree (reps DESC);


--
-- TOC entry 4942 (class 1259 OID 164026)
-- Name: idx_leaderboard_sets_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_leaderboard_sets_desc ON public.sets_leaderboard USING btree (num_sets DESC);


--
-- TOC entry 4939 (class 1259 OID 164007)
-- Name: idx_leaderboard_volume_desc; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_leaderboard_volume_desc ON public.volume_leaderboard USING btree (volume DESC);


--
-- TOC entry 4905 (class 1259 OID 122924)
-- Name: muscle_group_name_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX muscle_group_name_unique ON public.muscle_groups USING btree (lower(name));


--
-- TOC entry 4908 (class 1259 OID 122925)
-- Name: muscle_target_name_unique; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX muscle_target_name_unique ON public.muscle_targets USING btree (lower(name), muscle_group_id);


--
-- TOC entry 4886 (class 1259 OID 32802)
-- Name: username; Type: INDEX; Schema: public; Owner: postgres
--

CREATE UNIQUE INDEX username ON public.users USING btree (lower(username));


--
-- TOC entry 4968 (class 2606 OID 163902)
-- Name: bodyweight_exercise_ratios bodyweight_exercise_ratios_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.bodyweight_exercise_ratios
    ADD CONSTRAINT bodyweight_exercise_ratios_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE CASCADE;


--
-- TOC entry 4952 (class 2606 OID 49360)
-- Name: exercise_muscle_targets exercise_muscle_targets_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercise_muscle_targets
    ADD CONSTRAINT exercise_muscle_targets_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE CASCADE;


--
-- TOC entry 4953 (class 2606 OID 49355)
-- Name: exercise_muscle_targets exercise_muscle_targets_muscle_target_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercise_muscle_targets
    ADD CONSTRAINT exercise_muscle_targets_muscle_target_id_fkey FOREIGN KEY (muscle_target_id) REFERENCES public.muscle_targets(id) ON DELETE CASCADE;


--
-- TOC entry 4969 (class 2606 OID 163943)
-- Name: exercise_totals exercise_totals_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercise_totals
    ADD CONSTRAINT exercise_totals_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE CASCADE;


--
-- TOC entry 4970 (class 2606 OID 163938)
-- Name: exercise_totals exercise_totals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercise_totals
    ADD CONSTRAINT exercise_totals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4977 (class 2606 OID 164068)
-- Name: exercises_leaderboard exercises_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercises_leaderboard
    ADD CONSTRAINT exercises_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4945 (class 2606 OID 114720)
-- Name: exercises exercises_parent_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT exercises_parent_id_fkey FOREIGN KEY (parent_id) REFERENCES public.exercises(id) ON DELETE CASCADE;


--
-- TOC entry 4946 (class 2606 OID 41084)
-- Name: exercises exercises_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.exercises
    ADD CONSTRAINT exercises_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4971 (class 2606 OID 163980)
-- Name: friends friends_user_id1_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_user_id1_fkey FOREIGN KEY (user_id1) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4972 (class 2606 OID 163985)
-- Name: friends friends_user_id2_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_user_id2_fkey FOREIGN KEY (user_id2) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4951 (class 2606 OID 49342)
-- Name: muscle_targets muscle_targets_muscle_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.muscle_targets
    ADD CONSTRAINT muscle_targets_muscle_group_id_fkey FOREIGN KEY (muscle_group_id) REFERENCES public.muscle_groups(id) ON DELETE CASCADE;


--
-- TOC entry 4966 (class 2606 OID 155696)
-- Name: previous_workout_muscle_group_stats previous_workout_muscle_group_stats_muscle_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_muscle_group_stats
    ADD CONSTRAINT previous_workout_muscle_group_stats_muscle_group_id_fkey FOREIGN KEY (muscle_group_id) REFERENCES public.muscle_groups(id) ON DELETE CASCADE;


--
-- TOC entry 4967 (class 2606 OID 155691)
-- Name: previous_workout_muscle_group_stats previous_workout_muscle_group_stats_workout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_muscle_group_stats
    ADD CONSTRAINT previous_workout_muscle_group_stats_workout_id_fkey FOREIGN KEY (workout_id) REFERENCES public.workouts(id) ON DELETE CASCADE;


--
-- TOC entry 4964 (class 2606 OID 147509)
-- Name: previous_workout_muscle_target_stats previous_workout_muscle_target_stats_muscle_target_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_muscle_target_stats
    ADD CONSTRAINT previous_workout_muscle_target_stats_muscle_target_id_fkey FOREIGN KEY (muscle_target_id) REFERENCES public.muscle_targets(id) ON DELETE CASCADE;


--
-- TOC entry 4965 (class 2606 OID 147504)
-- Name: previous_workout_muscle_target_stats previous_workout_muscle_target_stats_workout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_muscle_target_stats
    ADD CONSTRAINT previous_workout_muscle_target_stats_workout_id_fkey FOREIGN KEY (workout_id) REFERENCES public.workouts(id) ON DELETE CASCADE;


--
-- TOC entry 4963 (class 2606 OID 147496)
-- Name: previous_workout_stats previous_workout_stats_workout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.previous_workout_stats
    ADD CONSTRAINT previous_workout_stats_workout_id_fkey FOREIGN KEY (workout_id) REFERENCES public.workouts(id) ON DELETE CASCADE;


--
-- TOC entry 4975 (class 2606 OID 164037)
-- Name: reps_leaderboard reps_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.reps_leaderboard
    ADD CONSTRAINT reps_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4974 (class 2606 OID 164021)
-- Name: sets_leaderboard sets_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.sets_leaderboard
    ADD CONSTRAINT sets_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4956 (class 2606 OID 98367)
-- Name: user_goals user_goals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_goals
    ADD CONSTRAINT user_goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4957 (class 2606 OID 98379)
-- Name: user_heights user_heights_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_heights
    ADD CONSTRAINT user_heights_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4955 (class 2606 OID 98355)
-- Name: user_ped_status user_ped_status_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_ped_status
    ADD CONSTRAINT user_ped_status_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4954 (class 2606 OID 98343)
-- Name: user_weights user_weights_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.user_weights
    ADD CONSTRAINT user_weights_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4973 (class 2606 OID 164002)
-- Name: volume_leaderboard volume_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.volume_leaderboard
    ADD CONSTRAINT volume_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4948 (class 2606 OID 49208)
-- Name: workout_exercises workout_exercises_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_exercises
    ADD CONSTRAINT workout_exercises_exercise_id_fkey FOREIGN KEY (exercise_id) REFERENCES public.exercises(id) ON DELETE CASCADE;


--
-- TOC entry 4949 (class 2606 OID 49203)
-- Name: workout_exercises workout_exercises_workout_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_exercises
    ADD CONSTRAINT workout_exercises_workout_id_fkey FOREIGN KEY (workout_id) REFERENCES public.workouts(id) ON DELETE CASCADE;


--
-- TOC entry 4958 (class 2606 OID 139321)
-- Name: workout_muscle_group_totals workout_muscle_group_totals_muscle_group_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_muscle_group_totals
    ADD CONSTRAINT workout_muscle_group_totals_muscle_group_id_fkey FOREIGN KEY (muscle_group_id) REFERENCES public.muscle_groups(id) ON DELETE CASCADE;


--
-- TOC entry 4959 (class 2606 OID 139316)
-- Name: workout_muscle_group_totals workout_muscle_group_totals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_muscle_group_totals
    ADD CONSTRAINT workout_muscle_group_totals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4960 (class 2606 OID 139336)
-- Name: workout_muscle_target_totals workout_muscle_target_totals_muscle_target_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_muscle_target_totals
    ADD CONSTRAINT workout_muscle_target_totals_muscle_target_id_fkey FOREIGN KEY (muscle_target_id) REFERENCES public.muscle_targets(id) ON DELETE CASCADE;


--
-- TOC entry 4961 (class 2606 OID 139331)
-- Name: workout_muscle_target_totals workout_muscle_target_totals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_muscle_target_totals
    ADD CONSTRAINT workout_muscle_target_totals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4950 (class 2606 OID 49221)
-- Name: workout_set_data workout_set_data_workout_exercise_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_set_data
    ADD CONSTRAINT workout_set_data_workout_exercise_id_fkey FOREIGN KEY (workout_exercise_id) REFERENCES public.workout_exercises(id) ON DELETE CASCADE;


--
-- TOC entry 4962 (class 2606 OID 139346)
-- Name: workout_totals workout_totals_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workout_totals
    ADD CONSTRAINT workout_totals_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4976 (class 2606 OID 164053)
-- Name: workouts_leaderboard workouts_leaderboard_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workouts_leaderboard
    ADD CONSTRAINT workouts_leaderboard_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 4947 (class 2606 OID 49191)
-- Name: workouts workouts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.workouts
    ADD CONSTRAINT workouts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- TOC entry 5138 (class 0 OID 0)
-- Dependencies: 241
-- Name: TABLE bodyweight_exercise_ratios; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.bodyweight_exercise_ratios TO localuser;


--
-- TOC entry 5139 (class 0 OID 0)
-- Dependencies: 220
-- Name: TABLE exercises; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercises TO localuser;


--
-- TOC entry 5140 (class 0 OID 0)
-- Dependencies: 243
-- Name: TABLE exercise_base_variants; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercise_base_variants TO localuser;


--
-- TOC entry 5141 (class 0 OID 0)
-- Dependencies: 219
-- Name: TABLE users; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.users TO localuser;


--
-- TOC entry 5142 (class 0 OID 0)
-- Dependencies: 222
-- Name: TABLE workout_exercises; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workout_exercises TO localuser;


--
-- TOC entry 5143 (class 0 OID 0)
-- Dependencies: 223
-- Name: TABLE workout_set_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workout_set_data TO localuser;


--
-- TOC entry 5144 (class 0 OID 0)
-- Dependencies: 221
-- Name: TABLE workouts; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workouts TO localuser;


--
-- TOC entry 5145 (class 0 OID 0)
-- Dependencies: 228
-- Name: TABLE exercise_history; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercise_history TO localuser;


--
-- TOC entry 5146 (class 0 OID 0)
-- Dependencies: 226
-- Name: TABLE exercise_muscle_targets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercise_muscle_targets TO localuser;


--
-- TOC entry 5147 (class 0 OID 0)
-- Dependencies: 224
-- Name: TABLE muscle_groups; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.muscle_groups TO localuser;


--
-- TOC entry 5148 (class 0 OID 0)
-- Dependencies: 225
-- Name: TABLE muscle_targets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.muscle_targets TO localuser;


--
-- TOC entry 5149 (class 0 OID 0)
-- Dependencies: 227
-- Name: TABLE exercise_muscle_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercise_muscle_data TO localuser;


--
-- TOC entry 5150 (class 0 OID 0)
-- Dependencies: 242
-- Name: TABLE exercise_totals; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercise_totals TO localuser;


--
-- TOC entry 5151 (class 0 OID 0)
-- Dependencies: 253
-- Name: TABLE exercises_leaderboard; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.exercises_leaderboard TO localuser;


--
-- TOC entry 5152 (class 0 OID 0)
-- Dependencies: 244
-- Name: TABLE friends; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.friends TO localuser;


--
-- TOC entry 5153 (class 0 OID 0)
-- Dependencies: 234
-- Name: TABLE muscle_groups_targets; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.muscle_groups_targets TO localuser;


--
-- TOC entry 5154 (class 0 OID 0)
-- Dependencies: 240
-- Name: TABLE previous_workout_muscle_group_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.previous_workout_muscle_group_stats TO localuser;


--
-- TOC entry 5155 (class 0 OID 0)
-- Dependencies: 239
-- Name: TABLE previous_workout_muscle_target_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.previous_workout_muscle_target_stats TO localuser;


--
-- TOC entry 5156 (class 0 OID 0)
-- Dependencies: 238
-- Name: TABLE previous_workout_stats; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.previous_workout_stats TO localuser;


--
-- TOC entry 5157 (class 0 OID 0)
-- Dependencies: 249
-- Name: TABLE reps_leaderboard; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.reps_leaderboard TO localuser;


--
-- TOC entry 5158 (class 0 OID 0)
-- Dependencies: 247
-- Name: TABLE sets_leaderboard; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.sets_leaderboard TO localuser;


--
-- TOC entry 5159 (class 0 OID 0)
-- Dependencies: 231
-- Name: TABLE user_goals; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_goals TO localuser;


--
-- TOC entry 5160 (class 0 OID 0)
-- Dependencies: 232
-- Name: TABLE user_heights; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_heights TO localuser;


--
-- TOC entry 5161 (class 0 OID 0)
-- Dependencies: 230
-- Name: TABLE user_ped_status; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_ped_status TO localuser;


--
-- TOC entry 5162 (class 0 OID 0)
-- Dependencies: 229
-- Name: TABLE user_weights; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_weights TO localuser;


--
-- TOC entry 5163 (class 0 OID 0)
-- Dependencies: 233
-- Name: TABLE user_data; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.user_data TO localuser;


--
-- TOC entry 5164 (class 0 OID 0)
-- Dependencies: 245
-- Name: TABLE volume_leaderboard; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.volume_leaderboard TO localuser;


--
-- TOC entry 5165 (class 0 OID 0)
-- Dependencies: 235
-- Name: TABLE workout_muscle_group_totals; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workout_muscle_group_totals TO localuser;


--
-- TOC entry 5166 (class 0 OID 0)
-- Dependencies: 236
-- Name: TABLE workout_muscle_target_totals; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workout_muscle_target_totals TO localuser;


--
-- TOC entry 5167 (class 0 OID 0)
-- Dependencies: 237
-- Name: TABLE workout_totals; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workout_totals TO localuser;


--
-- TOC entry 5168 (class 0 OID 0)
-- Dependencies: 251
-- Name: TABLE workouts_leaderboard; Type: ACL; Schema: public; Owner: postgres
--

GRANT ALL ON TABLE public.workouts_leaderboard TO localuser;


-- Completed on 2025-10-04 12:36:59

--
-- PostgreSQL database dump complete
--

