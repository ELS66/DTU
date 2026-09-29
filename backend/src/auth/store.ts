export type TenantRole = 'TENANT_ADMIN' | 'USER';

export interface UserRecord {
  id: string;
  loginName: string;
  passwordHash: string;
  enabled: boolean;
}

export interface AuthenticatedUser {
  id: string;
  loginName: string;
}

export interface Membership {
  tenantId: string;
  tenantName: string;
  role: TenantRole;
}

export interface ProjectSummary {
  id: string;
  name: string;
}

export interface AuthStore {
  findUserByLogin(loginName: string): Promise<UserRecord | null>;
  createSession(tokenHash: string, userId: string, expiresAt: Date): Promise<void>;
  findActiveSession(tokenHash: string, now: Date): Promise<AuthenticatedUser | null>;
  revokeSession(tokenHash: string): Promise<void>;
  listMemberships(userId: string): Promise<Membership[]>;
  findTenantRole(userId: string, tenantId: string): Promise<TenantRole | null>;
  listProjects(tenantId: string, userId: string, role: TenantRole): Promise<ProjectSummary[]>;
}
