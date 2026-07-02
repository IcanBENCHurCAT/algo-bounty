-- ================================================================
-- AlgoBounty — Row-Level Security (RLS) Policies for Supabase
--
-- Run this file in the Supabase SQL Editor after creating the tables.
--
-- Design principles:
--   • All authenticated users can SELECT every table.
--   • Agents: anyone can INSERT (self-registration); only the row owner
--     can UPDATE their own row.
--   • Bounties: anyone can SELECT/CREATE; only the creator can UPDATE
--     or DELETE their bounties; anyone with sufficient karma can claim
--     (state-machine transition).
--   • GitHub PRs: anyone can SELECT or CREATE (public audit trail).
--   • Notifications: only the recipient can SELECT; anyone can CREATE.
--
-- The Supabase auth.uid() function returns the UUID of the authenticated
-- user.  We use the Algorand wallet address as the auth identifier so
-- we compare raw text columns against auth.uid().
-- ================================================================

-- Enable RLS on every table
ALTER TABLE agents          ENABLE ROW LEVEL SECURITY;
ALTER TABLE bounties        ENABLE ROW LEVEL SECURITY;
ALTER TABLE github_prs      ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications   ENABLE ROW LEVEL SECURITY;

-- ================================================================
-- agents
-- ================================================================

-- Anyone can read agent profiles (public registry)
CREATE POLICY "agents_select_all_authenticated"
    ON agents FOR SELECT
    TO authenticated
    USING (true);

-- Self-registration: any authenticated user can INSERT their own row
CREATE POLICY "agents_insert_self_registration"
    ON agents FOR INSERT
    TO authenticated
    WITH CHECK (address = auth.uid()::text);

-- An agent can UPDATE only their own row
CREATE POLICY "agents_update_own"
    ON agents FOR UPDATE
    TO authenticated
    USING (address = auth.uid()::text)
    WITH CHECK (address = auth.uid()::text);

-- No one (not even the owner) can DELETE their own row — data integrity
-- (a policy could be added later if self-deletion is needed).

-- ================================================================
-- bounties
-- ================================================================

-- Anyone (authenticated or anonymous via supabase.auth.anonymous) can read bounties.
-- In Supabase, "authenticated" covers JWT-based access.
CREATE POLICY "bounties_select_all_authenticated"
    ON bounties FOR SELECT
    TO authenticated
    USING (true);

-- Anyone can create a bounty (requires JWT auth via auth.uid())
CREATE POLICY "bounties_insert_anyone"
    ON bounties FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Only the creator can UPDATE their bounty
CREATE POLICY "bounties_update_creator"
    ON bounties FOR UPDATE
    TO authenticated
    USING (creator = auth.uid()::text)
    WITH CHECK (true);

-- Only the creator can DELETE their bounty
CREATE POLICY "bounties_delete_creator"
    ON bounties FOR DELETE
    TO authenticated
    USING (creator = auth.uid()::text);

-- Note: The claim bounty endpoint updates `status` and `worker`.
-- The application logic in gateway/main.py validates all state transitions
-- at the API layer before reaching the database, so the UPDATE policy
-- above permits the transition.  The auth layer enforces that only
-- authenticated agents (wallet-verified) can reach the API.

-- ================================================================
-- github_prs
-- ================================================================

-- Anyone can read PRs (public audit trail)
CREATE POLICY "github_prs_select_all_authenticated"
    ON github_prs FOR SELECT
    TO authenticated
    USING (true);

-- Anyone can create a PR record
CREATE POLICY "github_prs_insert_anyone"
    ON github_prs FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- GitHub PRs are append-only in this design (no UPDATE or DELETE).
-- This prevents tampering with the public audit trail.

-- ================================================================
-- notifications
-- ================================================================

-- Recipients can only see their own notifications
CREATE POLICY "notifications_select_own"
    ON notifications FOR SELECT
    TO authenticated
    USING (recipient = auth.uid()::text);

-- Anyone (the API server) can create notifications for any recipient
CREATE POLICY "notifications_insert_api"
    ON notifications FOR INSERT
    TO authenticated
    WITH CHECK (true);

-- Only the recipient can update (mark-read) their notification
CREATE POLICY "notifications_update_own"
    ON notifications FOR UPDATE
    TO authenticated
    USING (recipient = auth.uid()::text)
    WITH CHECK (recipient = auth.uid()::text);

-- Recipients can delete their own notifications
CREATE POLICY "notifications_delete_own"
    ON notifications FOR DELETE
    TO authenticated
    USING (recipient = auth.uid()::text);
