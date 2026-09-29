<script setup lang="ts">
import { ElAlert, ElCard } from 'element-plus';
import 'element-plus/es/components/alert/style/css';
import 'element-plus/es/components/card/style/css';
</script>

<template>
  <main class="shell">
    <header><strong>DTU 管理后台</strong><span>开发环境</span></header>
    <section class="content">
      <ElCard>
        <h1>平台骨架已就绪</h1>
        <p>后续将接入登录、租户管理、网关和设备归属。</p>
        <ElAlert title="当前仅提供界面骨架，尚未连接业务接口。" type="info" :closable="false" show-icon />
      </ElCard>
    </section>
  </main>
</template>
