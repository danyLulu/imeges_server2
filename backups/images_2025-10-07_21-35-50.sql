--
-- PostgreSQL database dump
--

\restrict eApufwtOPn05AIPgTSmb2rljknpgIV9kDKNrjYFRtyXBgUZuozxIANokkQ14jeh

-- Dumped from database version 16.10 (Debian 16.10-1.pgdg13+1)
-- Dumped by pg_dump version 16.10 (Debian 16.10-1.pgdg13+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
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
-- Name: images; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.images (
    id integer NOT NULL,
    filename text NOT NULL,
    original_name text NOT NULL,
    size integer NOT NULL,
    upload_time timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    file_type text NOT NULL
);


ALTER TABLE public.images OWNER TO postgres;

--
-- Name: images_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.images_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.images_id_seq OWNER TO postgres;

--
-- Name: images_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.images_id_seq OWNED BY public.images.id;


--
-- Name: images id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images ALTER COLUMN id SET DEFAULT nextval('public.images_id_seq'::regclass);


--
-- Data for Name: images; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.images (id, filename, original_name, size, upload_time, file_type) FROM stdin;
1	70510744f84949cfbd87a740869be7eb.jpg	2025-09-11 18.29.50.jpg	149547	2025-10-03 16:16:37.893515	jpg
34	e54f2a10002348cbac8e23581467bd61.jpg	2025-09-14 14.43.03.jpg	138453	2025-10-03 17:57:03.404896	jpg
67	807e2b3a064740e88027e850a5ad1256.jpg	2025-09-14 14.43.07.jpg	75215	2025-10-04 11:03:31.411617	jpg
\.


--
-- Name: images_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.images_id_seq', 99, true);


--
-- Name: images images_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.images
    ADD CONSTRAINT images_pkey PRIMARY KEY (id);


--
-- PostgreSQL database dump complete
--

\unrestrict eApufwtOPn05AIPgTSmb2rljknpgIV9kDKNrjYFRtyXBgUZuozxIANokkQ14jeh

