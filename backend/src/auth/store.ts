export type TenantRole = 'TENANT_ADMIN' | 'USER';
export type ProjectRole = 'PROJECT_ADMIN' | 'OPERATOR' | 'VIEWER';

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

export interface TenantMemberSummary {
  id: string;
  loginName: string;
  role: TenantRole;
}

export interface AuthStore {
  findUserByLogin(loginName: string): Promise<UserRecord | null>;
  createSession(tokenHash: string, userId: string, expiresAt: Date): Promise<void>;
  findActiveSession(tokenHash: string, now: Date): Promise<AuthenticatedUser | null>;
  revokeSession(tokenHash: string): Promise<void>;
  listMemberships(userId: string): Promise<Membership[]>;
  findTenantRole(userId: string, tenantId: string): Promise<TenantRole | null>;
  listProjects(tenantId: string, userId: string): Promise<ProjectSummary[] | null>;
  createProject(tenantId: string, actorId: string, projectId: string, name: string): Promise<ProjectSummary | null>;
  setProjectMember(tenantId: string, projectId: string, actorId: string,
    memberId: string, role: ProjectRole): Promise<boolean>;
  listTenantMembers(tenantId: string, actorId: string): Promise<TenantMemberSummary[] | null>;
}
