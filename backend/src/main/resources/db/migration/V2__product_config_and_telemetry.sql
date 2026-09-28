CREATE TABLE data_point (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    product_version_id uuid NOT NULL,
    identifier varchar(120) NOT NULL,
    point_code integer NOT NULL CHECK (point_code BETWEEN 1 AND 65535),
    name varchar(160) NOT NULL,
    data_type varchar(16) NOT NULL CHECK (data_type IN ('NUMBER', 'BOOLEAN', 'ENUM')),
    access_mode varchar(2) NOT NULL CHECK (access_mode IN ('R', 'W', 'RW')),
    unit varchar(32),
    min_value numeric,
    max_value numeric,
    step numeric,
    history_enabled boolean NOT NULL DEFAULT true,
    UNIQUE (product_version_id, identifier),
    UNIQUE (product_version_id, point_code),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, product_version_id) REFERENCES product_version(tenant_id, id),
    CHECK (min_value IS NULL OR max_value IS NULL OR min_value <= max_value),
    CHECK (step IS NULL OR step > 0)
);

CREATE TABLE protocol_mapping (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    data_point_id uuid NOT NULL,
    read_function smallint CHECK (read_function IN (1, 2, 3, 4)),
    read_address integer CHECK (read_address BETWEEN 0 AND 65535),
    write_function smallint CHECK (write_function IN (5, 6, 15, 16)),
    write_address integer CHECK (write_address BETWEEN 0 AND 65535),
    register_count smallint NOT NULL CHECK (register_count BETWEEN 1 AND 125),
    raw_data_type varchar(16) NOT NULL CHECK (raw_data_type IN
        ('UINT16', 'INT16', 'UINT32', 'INT32', 'FLOAT32', 'BOOL', 'BIT')),
    byte_order varchar(8) NOT NULL DEFAULT 'AB',
    bit_offset smallint CHECK (bit_offset BETWEEN 0 AND 15),
    scale numeric NOT NULL DEFAULT 1 CHECK (scale <> 0),
    value_offset numeric NOT NULL DEFAULT 0,
    scan_interval_ms integer CHECK (scan_interval_ms BETWEEN 100 AND 3600000),
    enabled boolean NOT NULL DEFAULT true,
    UNIQUE (data_point_id),
    FOREIGN KEY (tenant_id, data_point_id) REFERENCES data_point(tenant_id, id),
    CHECK ((read_function IS NULL AND read_address IS NULL AND scan_interval_ms IS NULL)
        OR (read_function IS NOT NULL AND read_address IS NOT NULL AND scan_interval_ms IS NOT NULL)),
    CHECK ((write_function IS NULL AND write_address IS NULL)
        OR (write_function IS NOT NULL AND write_address IS NOT NULL))
);

CREATE TABLE config_release (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    gateway_id uuid NOT NULL,
    revision bigint NOT NULL CHECK (revision > 0),
    product_version_id uuid NOT NULL,
    config_json jsonb NOT NULL,
    content_hash char(64) NOT NULL,
    status varchar(20) NOT NULL CHECK (status IN
        ('PENDING', 'SENT', 'APPLIED', 'FAILED', 'SUPERSEDED')),
    created_at timestamptz NOT NULL DEFAULT now(),
    applied_at timestamptz,
    UNIQUE (gateway_id, revision),
    UNIQUE (tenant_id, gateway_id, revision),
    FOREIGN KEY (tenant_id, gateway_id) REFERENCES gateway(tenant_id, id),
    FOREIGN KEY (tenant_id, product_version_id) REFERENCES product_version(tenant_id, id)
);

CREATE TABLE telemetry_inbox (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    gateway_id uuid NOT NULL,
    config_revision bigint NOT NULL,
    boot_id uuid NOT NULL,
    sequence bigint NOT NULL CHECK (sequence > 0),
    payload bytea NOT NULL,
    processing_status varchar(16) NOT NULL CHECK (processing_status IN
        ('RECEIVED', 'PROCESSED', 'REJECTED')),
    received_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (gateway_id, boot_id, sequence),
    FOREIGN KEY (tenant_id, gateway_id, config_revision)
        REFERENCES config_release(tenant_id, gateway_id, revision)
);

CREATE TABLE telemetry (
    id uuid NOT NULL,
    tenant_id uuid NOT NULL,
    device_id uuid NOT NULL,
    point_id uuid NOT NULL,
    inbox_id uuid NOT NULL REFERENCES telemetry_inbox(id),
    config_revision bigint NOT NULL,
    sampled_at timestamptz,
    received_at timestamptz NOT NULL,
    quality smallint NOT NULL CHECK (quality BETWEEN 0 AND 3),
    value_number numeric,
    value_boolean boolean,
    PRIMARY KEY (id, received_at),
    UNIQUE (inbox_id, point_id, received_at),
    FOREIGN KEY (tenant_id, device_id) REFERENCES device(tenant_id, id),
    FOREIGN KEY (tenant_id, point_id) REFERENCES data_point(tenant_id, id),
    CHECK ((quality <> 0 AND value_number IS NULL AND value_boolean IS NULL)
        OR (quality = 0 AND ((value_number IS NOT NULL)::integer +
                             (value_boolean IS NOT NULL)::integer = 1)))
) PARTITION BY RANGE (received_at);

-- 开发环境的初始分区；生产环境通过定时任务预建下一月并清理过期分区。
CREATE TABLE telemetry_default PARTITION OF telemetry DEFAULT;
CREATE INDEX idx_telemetry_device_point_time
    ON telemetry_default (device_id, point_id, received_at DESC);

CREATE TABLE shadow_snapshot (
    tenant_id uuid NOT NULL,
    device_id uuid NOT NULL,
    point_id uuid NOT NULL,
    config_revision bigint NOT NULL,
    sampled_at timestamptz,
    received_at timestamptz NOT NULL,
    quality smallint NOT NULL CHECK (quality BETWEEN 0 AND 3),
    value_number numeric,
    value_boolean boolean,
    source_inbox_id uuid NOT NULL REFERENCES telemetry_inbox(id),
    PRIMARY KEY (device_id, point_id),
    FOREIGN KEY (tenant_id, device_id) REFERENCES device(tenant_id, id),
    FOREIGN KEY (tenant_id, point_id) REFERENCES data_point(tenant_id, id)
);
