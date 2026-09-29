<script setup lang="ts">
import { computed, ref } from 'vue';
import { ElAlert, ElCard } from 'element-plus';
import 'element-plus/es/components/alert/style/css';
import 'element-plus/es/components/card/style/css';

type Tenant = { tenantId: string; tenantName: string; role: 'TENANT_ADMIN' | 'USER' };
type Project = { id: string; name: string };
type Member = { id: string; loginName: string; role: 'TENANT_ADMIN' | 'USER' };
type ProjectRole = 'PROJECT_ADMIN' | 'OPERATOR' | 'VIEWER';

const loginName = ref('');
const password = ref('');
const token = ref('');
const tenants = ref<Tenant[]>([]);
const projects = ref<Project[]>([]);
const members = ref<Member[]>([]);
const selectedTenant = ref('');
const newProjectName = ref('');
const selectedProject = ref('');
const selectedMember = ref('');
const selectedRole = ref<ProjectRole>('VIEWER');
const busy = ref(false);
const error = ref('');
const notice = ref('');
const currentTenant = computed(() => tenants.value.find((item) => item.tenantId === selectedTenant.value));
const isAdmin = computed(() => currentTenant.value?.role === 'TENANT_ADMIN');

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    headers: {
      ...(init.body ? { 'Content-Type': 'application/json' } : {}),
      ...(token.value ? { Authorization: `Bearer ${token.value}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    if (response.status === 401 && token.value) token.value = '';
    throw new Error(response.status === 401 ? path === '/auth/login'
      ? '账号或密码不正确。' : '登录已失效，请重新登录。'
      : response.status === 404 ? '无权访问或目标不存在。' : '操作未完成，请稍后重试。');
  }
  return response.status === 204 ? undefined as T : await response.json() as T;
}

async function login() {
  busy.value = true;
  error.value = '';
  notice.value = '';
  try {
    const session = await api<{ accessToken: string }>('/auth/login', {
      method: 'POST', body: JSON.stringify({ loginName: loginName.value, password: password.value }),
    });
    token.value = session.accessToken;
    password.value = '';
    const me = await api<{ tenants: Tenant[] }>('/me');
    tenants.value = me.tenants;
    selectedTenant.value = me.tenants[0]?.tenantId ?? '';
    if (selectedTenant.value) await loadTenantData();
  } catch (cause) {
    token.value = '';
    tenants.value = [];
    error.value = cause instanceof Error ? cause.message : '登录失败。';
  } finally {
    busy.value = false;
  }
}

async function loadTenantData() {
  const tenantId = selectedTenant.value;
  if (!tenantId) return;
  error.value = '';
  try {
    const projectResult = await api<{ items: Project[] }>(`/tenants/${tenantId}/projects`);
    if (selectedTenant.value !== tenantId) return;
    const memberResult = isAdmin.value
      ? (await api<{ items: Member[] }>(`/tenants/${tenantId}/members`)).items : [];
    if (selectedTenant.value !== tenantId) return;
    projects.value = projectResult.items;
    selectedProject.value = projects.value[0]?.id ?? '';
    members.value = memberResult;
    selectedMember.value = members.value[0]?.id ?? '';
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '加载失败。';
  }
}

async function createProject() {
  if (!selectedTenant.value || !newProjectName.value.trim()) return;
  busy.value = true;
  error.value = '';
  notice.value = '';
  try {
    const project = await api<Project>(`/tenants/${selectedTenant.value}/projects`, {
      method: 'POST', body: JSON.stringify({ name: newProjectName.value.trim() }),
    });
    newProjectName.value = '';
    await loadTenantData();
    selectedProject.value = project.id;
    notice.value = '项目已创建。';
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '创建失败。';
  } finally {
    busy.value = false;
  }
}

async function assignMember() {
  if (!selectedTenant.value || !selectedProject.value || !selectedMember.value) return;
  busy.value = true;
  error.value = '';
  notice.value = '';
  try {
    await api<void>(`/tenants/${selectedTenant.value}/projects/${selectedProject.value}/members/${selectedMember.value}`, {
      method: 'PUT', body: JSON.stringify({ role: selectedRole.value }),
    });
    notice.value = '项目成员权限已保存。';
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '保存失败。';
  } finally {
    busy.value = false;
  }
}

async function logout() {
  try { await api<void>('/auth/logout', { method: 'POST' }); } catch { /* clear local session anyway */ }
  token.value = '';
  tenants.value = [];
  projects.value = [];
  members.value = [];
  selectedTenant.value = '';
  notice.value = '';
  error.value = '';
}
</script>

<template>
  <main class="shell">
    <header><strong>DTU 管理后台</strong><button v-if="token" class="text-button" @click="logout">退出登录</button></header>
    <section class="content">
      <ElAlert v-if="error" class="message" :title="error" type="error" :closable="false" show-icon />
      <ElAlert v-if="notice" class="message" :title="notice" type="success" :closable="false" show-icon />
      <ElCard v-if="!token" class="login-card">
        <h1>登录平台</h1>
        <form @submit.prevent="login">
          <label for="login-name">账号</label>
          <input id="login-name" v-model="loginName" autocomplete="username" required />
          <label for="login-password">密码</label>
          <input id="login-password" v-model="password" type="password" autocomplete="current-password" required />
          <button type="submit" :disabled="busy">{{ busy ? '登录中…' : '登录' }}</button>
        </form>
      </ElCard>
      <template v-else>
        <div class="page-title"><div><h1>项目管理</h1><p>查看当前租户的项目与成员授权。</p></div>
          <label class="tenant-picker">租户 <select v-model="selectedTenant" @change="loadTenantData">
            <option v-for="tenant in tenants" :key="tenant.tenantId" :value="tenant.tenantId">{{ tenant.tenantName }}</option>
          </select></label>
        </div>
        <ElCard v-if="!selectedTenant"><p>当前账号尚未加入租户。</p></ElCard>
        <template v-else>
          <ElCard class="section-card"><h2>项目</h2>
            <p v-if="projects.length === 0">暂无项目。</p>
            <ul v-else class="project-list"><li v-for="project in projects" :key="project.id">{{ project.name }}</li></ul>
          </ElCard>
          <div v-if="isAdmin" class="admin-grid">
            <ElCard><h2>创建项目</h2><form @submit.prevent="createProject">
              <label for="project-name">项目名称</label>
              <input id="project-name" v-model="newProjectName" maxlength="160" required />
              <button type="submit" :disabled="busy">创建</button>
            </form></ElCard>
            <ElCard><h2>设置项目成员</h2><form @submit.prevent="assignMember">
              <label for="member-project">项目</label><select id="member-project" v-model="selectedProject" required>
                <option v-for="project in projects" :key="project.id" :value="project.id">{{ project.name }}</option>
              </select>
              <label for="member-user">成员</label><select id="member-user" v-model="selectedMember" required>
                <option v-for="member in members" :key="member.id" :value="member.id">{{ member.loginName }}</option>
              </select>
              <label for="member-role">项目角色</label><select id="member-role" v-model="selectedRole">
                <option value="VIEWER">查看者</option><option value="OPERATOR">操作员</option><option value="PROJECT_ADMIN">项目管理员</option>
              </select>
              <button type="submit" :disabled="busy || !selectedProject || !selectedMember">保存权限</button>
            </form></ElCard>
          </div>
        </template>
      </template>
    </section>
  </main>
</template>
