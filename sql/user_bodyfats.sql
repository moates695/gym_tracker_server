
CREATE TABLE public.user_bodyfats (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id uuid NOT NULL,
    bodyfat real NOT NULL,
    created_at timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);

ALTER TABLE public.user_bodyfats OWNER TO postgres;

ALTER TABLE ONLY public.user_bodyfats
    ADD CONSTRAINT user_bodyfats_pkey PRIMARY KEY (id);

ALTER TABLE ONLY public.user_bodyfats
    ADD CONSTRAINT user_bodyfats_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

GRANT ALL ON TABLE public.user_bodyfats TO PUBLIC;