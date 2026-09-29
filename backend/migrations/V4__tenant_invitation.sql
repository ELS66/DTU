CREATE TABLE tenant_invitation (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    login_name varchar(120) NOT NULL,
    role varchar(32) NOT NULL CHECK (role IN ('TENANT_ADMIN', 'USER')),
    token_hash char(64) NOT NULL UNIQUE,
    invited_by uuid NOT NULL REFERENCES app_user(id),
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX idx_tenant_invitation_expiry ON tenant_invitation(expires_at);
