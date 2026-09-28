CREATE TABLE tenant (
    id uuid PRIMARY KEY,
    name varchar(160) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_user (
    id uuid PRIMARY KEY,
    login_name varchar(120) NOT NULL UNIQUE,
    password_hash varchar(255) NOT NULL,
    enabled boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE tenant_member (
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    user_id uuid NOT NULL REFERENCES app_user(id),
    role varchar(32) NOT NULL CHECK (role IN ('TENANT_ADMIN', 'USER')),
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id)
);

CREATE TABLE project (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    name varchar(160) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id)
);

CREATE TABLE project_member (
    tenant_id uuid NOT NULL,
    project_id uuid NOT NULL,
    user_id uuid NOT NULL,
    role varchar(32) NOT NULL CHECK (role IN ('PROJECT_ADMIN', 'OPERATOR', 'VIEWER')),
    PRIMARY KEY (project_id, user_id),
    FOREIGN KEY (tenant_id, project_id) REFERENCES project(tenant_id, id),
    FOREIGN KEY (tenant_id, user_id) REFERENCES tenant_member(tenant_id, user_id)
);

CREATE TABLE device_identity (
    id uuid PRIMARY KEY,
    hardware_code varchar(120) NOT NULL UNIQUE,
    model varchar(120) NOT NULL,
    credential_hash varchar(255),
    credential_revoked_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE gateway (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    identity_id uuid NOT NULL UNIQUE REFERENCES device_identity(id),
    name varchar(160) NOT NULL,
    firmware_version varchar(80),
    desired_config_revision bigint NOT NULL DEFAULT 0 CHECK (desired_config_revision >= 0),
    applied_config_revision bigint NOT NULL DEFAULT 0 CHECK (applied_config_revision >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id)
);

CREATE TABLE product (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL REFERENCES tenant(id),
    product_key varchar(120) NOT NULL,
    name varchar(160) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, product_key),
    UNIQUE (tenant_id, id)
);

CREATE TABLE product_version (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    product_id uuid NOT NULL,
    version integer NOT NULL CHECK (version > 0),
    status varchar(16) NOT NULL CHECK (status IN ('DRAFT', 'PUBLISHED', 'ARCHIVED')),
    content_hash char(64),
    created_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    UNIQUE (product_id, version),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, product_id) REFERENCES product(tenant_id, id),
    CHECK ((status = 'DRAFT' AND published_at IS NULL)
        OR (status <> 'DRAFT' AND published_at IS NOT NULL))
);

CREATE TABLE device (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    project_id uuid NOT NULL,
    product_version_id uuid NOT NULL,
    name varchar(160) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, project_id) REFERENCES project(tenant_id, id),
    FOREIGN KEY (tenant_id, product_version_id) REFERENCES product_version(tenant_id, id)
);

CREATE TABLE device_binding (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    gateway_id uuid NOT NULL,
    device_id uuid NOT NULL,
    port varchar(16) NOT NULL CHECK (port IN ('RS485', 'RS232', 'TTL')),
    slave_id integer NOT NULL CHECK (slave_id BETWEEN 1 AND 247),
    created_at timestamptz NOT NULL DEFAULT now(),
    ended_at timestamptz,
    FOREIGN KEY (tenant_id, gateway_id) REFERENCES gateway(tenant_id, id),
    FOREIGN KEY (tenant_id, device_id) REFERENCES device(tenant_id, id)
);

CREATE UNIQUE INDEX uq_gateway_active_binding ON device_binding(gateway_id) WHERE ended_at IS NULL;
CREATE UNIQUE INDEX uq_device_active_binding ON device_binding(device_id) WHERE ended_at IS NULL;

CREATE TABLE claim_token (
    id uuid PRIMARY KEY,
    identity_id uuid NOT NULL REFERENCES device_identity(id),
    token_hash varchar(255) NOT NULL UNIQUE,
    expires_at timestamptz NOT NULL,
    consumed_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE ownership_event (
    id uuid PRIMARY KEY,
    identity_id uuid NOT NULL REFERENCES device_identity(id),
    from_tenant_id uuid REFERENCES tenant(id),
    to_tenant_id uuid REFERENCES tenant(id),
    actor_user_id uuid REFERENCES app_user(id),
    event_type varchar(32) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
