<template>
  <div class="page-title-wrapper">
    <h2 class="page-title">
      <el-icon v-if="icon" :size="20" class="title-icon">
        <component :is="icon" />
      </el-icon>
      <span>{{ title }}</span>
    </h2>
    <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  icon: { type: String, default: null },
  subtitle: { type: String, default: '' },
})
</script>

<style scoped>
.page-title-wrapper {
  margin-bottom: 20px;
}

.page-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #1a1a1a);
  margin: 0;
  padding-left: 12px;
  border-left: 4px solid var(--brand-primary, #4f8cf7);
  line-height: 1.3;
}

.title-icon {
  color: var(--brand-primary, #4f8cf7);
  opacity: 0.8;
}

.page-subtitle {
  font-size: 13px;
  color: var(--text-tertiary, #909399);
  margin: 4px 0 0 16px;
}
</style>
