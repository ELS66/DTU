<script setup lang="ts">
import { NavBar, Empty, NoticeBar } from 'vant';
import 'vant/es/nav-bar/style/index';
import 'vant/es/empty/style/index';
import 'vant/es/notice-bar/style/index';
</script>

<template>
  <div class="page">
    <NavBar title="我的设备" />
    <NoticeBar text="当前为开发预览，设备数据接入正在建设中。" />
    <Empty description="暂无设备" />
  </div>
</template>
