drop table friends;

CREATE TABLE public.blocked_users (
    victim_id uuid NOT NULL,
    blocked_id uuid NOT NULL
);


ALTER TABLE public.blocked_users OWNER TO postgres;

grant all on table public.blocked_users to public;

CREATE TABLE public.friend_requests (
    requestor_id uuid NOT NULL,
    target_id uuid NOT NULL,
    request_state text NOT NULL,
    last_updated timestamp without time zone DEFAULT (now() AT TIME ZONE 'utc'::text) NOT NULL
);


ALTER TABLE public.friend_requests OWNER TO postgres;

grant all on table public.friend_requests to public;

CREATE TABLE public.friends (
    user1_id uuid NOT NULL,
    user2_id uuid NOT NULL
);


ALTER TABLE public.friends OWNER TO postgres;

grant all on table public.friends to public;

CREATE TABLE public.user_permissions (
    user_id uuid NOT NULL,
    permission_key text NOT NULL,
    permission_value text NOT NULL
);


ALTER TABLE public.user_permissions OWNER TO postgres;

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_pkey PRIMARY KEY (victim_id, blocked_id);

ALTER TABLE ONLY public.friend_requests
    ADD CONSTRAINT friend_requests_pkey PRIMARY KEY (requestor_id, target_id);

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_pkey PRIMARY KEY (user1_id, user2_id);

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_pkey PRIMARY KEY (user_id, permission_key);

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_blocked_id_fkey FOREIGN KEY (blocked_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.blocked_users
    ADD CONSTRAINT blocked_users_victim_id_fkey FOREIGN KEY (victim_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.friend_requests
    ADD CONSTRAINT friend_requests_requestor_id_fkey FOREIGN KEY (requestor_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.friend_requests
    ADD CONSTRAINT friend_requests_target_id_fkey FOREIGN KEY (target_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_user1_id_fkey FOREIGN KEY (user1_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.friends
    ADD CONSTRAINT friends_user2_id_fkey FOREIGN KEY (user2_id) REFERENCES public.users(id) ON DELETE CASCADE;

ALTER TABLE ONLY public.user_permissions
    ADD CONSTRAINT user_permissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

grant all on table public.user_permissions to public;