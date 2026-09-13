--
-- PostgreSQL database dump
--

\restrict P0QkwXNhqnjp2fZwHLjDftgvzDEGE1OPnLXkkZsthkc0t8iPxtyGflMyhpFOipy

-- Dumped from database version 16.14 (Debian 16.14-1.pgdg12+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg12+1)

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

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: aircraft; Type: TABLE; Schema: public; Owner: poseidon
--

CREATE TABLE public.aircraft (
    n_number text NOT NULL,
    owner_name text,
    owner_uei text,
    make_model text,
    year_mfr integer
);


ALTER TABLE public.aircraft OWNER TO poseidon;

--
-- Name: award; Type: TABLE; Schema: public; Owner: poseidon
--

CREATE TABLE public.award (
    award_id text NOT NULL,
    recipient_name text,
    amount numeric,
    awarding_agency text,
    awarding_sub_agency text,
    naics_code text,
    ingested_at timestamp with time zone DEFAULT now(),
    pop_end date
);


ALTER TABLE public.award OWNER TO poseidon;

--
-- Name: entity; Type: TABLE; Schema: public; Owner: poseidon
--

CREATE TABLE public.entity (
    uei text NOT NULL,
    name text NOT NULL,
    naics_primary text,
    state text,
    first_seen date,
    last_seen date
);


ALTER TABLE public.entity OWNER TO poseidon;

--
-- Name: opportunity; Type: TABLE; Schema: public; Owner: poseidon
--

CREATE TABLE public.opportunity (
    notice_id text NOT NULL,
    title text,
    agency text,
    naics_code text,
    posted_date date,
    response_deadline date,
    description text,
    embedding public.vector(1536)
);


ALTER TABLE public.opportunity OWNER TO poseidon;

--
-- Name: risk_score; Type: TABLE; Schema: public; Owner: poseidon
--

CREATE TABLE public.risk_score (
    as_of date NOT NULL,
    hhi_agency numeric,
    top_customer_pct numeric,
    recompete_risk numeric,
    anomaly_flag boolean,
    recipient_name text NOT NULL
);


ALTER TABLE public.risk_score OWNER TO poseidon;

--
-- Name: aircraft aircraft_pkey; Type: CONSTRAINT; Schema: public; Owner: poseidon
--

ALTER TABLE ONLY public.aircraft
    ADD CONSTRAINT aircraft_pkey PRIMARY KEY (n_number);


--
-- Name: award award_pkey; Type: CONSTRAINT; Schema: public; Owner: poseidon
--

ALTER TABLE ONLY public.award
    ADD CONSTRAINT award_pkey PRIMARY KEY (award_id);


--
-- Name: entity entity_pkey; Type: CONSTRAINT; Schema: public; Owner: poseidon
--

ALTER TABLE ONLY public.entity
    ADD CONSTRAINT entity_pkey PRIMARY KEY (uei);


--
-- Name: opportunity opportunity_pkey; Type: CONSTRAINT; Schema: public; Owner: poseidon
--

ALTER TABLE ONLY public.opportunity
    ADD CONSTRAINT opportunity_pkey PRIMARY KEY (notice_id);


--
-- Name: risk_score risk_score_pkey; Type: CONSTRAINT; Schema: public; Owner: poseidon
--

ALTER TABLE ONLY public.risk_score
    ADD CONSTRAINT risk_score_pkey PRIMARY KEY (recipient_name, as_of);


--
-- Name: aircraft aircraft_owner_uei_fkey; Type: FK CONSTRAINT; Schema: public; Owner: poseidon
--

ALTER TABLE ONLY public.aircraft
    ADD CONSTRAINT aircraft_owner_uei_fkey FOREIGN KEY (owner_uei) REFERENCES public.entity(uei);


--
-- PostgreSQL database dump complete
--

\unrestrict P0QkwXNhqnjp2fZwHLjDftgvzDEGE1OPnLXkkZsthkc0t8iPxtyGflMyhpFOipy

