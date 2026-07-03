<template>
  <div
    class="stat-card"
    :class="{ 'stat-card-hover': hoverable }"
    :style="accentStyle"
  >
    <div class="stat-card-header">
      <el-icon v-if="icon" :size="20" class="stat-card-icon" :style="iconColor">
        <component :is="icon" />
      </el-icon>
      <span class="stat-card-label">{{ title }}</span>
      <el-icon v-if="trend" :size="14" class="stat-card-trend" :class="trendClass">
        <component :is="trend === 'up' ? 'ArrowUp' : trend === 'down' ? 'ArrowDown' : 'Minus'" />
      </el-icon>
    </div>
    <div class="stat-card-value">
      <span :style="valueColor">{{ value }}</span>
      <span v-if="unit" class="stat-card-unit">{{ unit }}</span>
    </div>
    <div v-if="trendValue" class="stat-card-trend-value">
      <span :class="trendValuePositive ? 'trend-up' : 'trend-down'">
        {{ trendValuePositive ? '+' : '' }}{{ trendValue }}
      </span>
      <span class="trend-label">较上期</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowUp, ArrowDown, Minus } from '@element-plus/icons-vue'

const props = defineProps({
  title: { type: String, required: true },
  value: { type: [String, Number], required: true },
  unit: { type: String, default: '' },
  icon: { type: String, default: null },
  color: { type: String, default: '' },
  trend: { type: String, default: null }, // 'up' | 'down' | 'stable'
  trendValue: { type: String, default: '' },
  hoverable: { type: Boolean, default: true },
})

const accentStyle = computed(() => {
  const styles = {}
  if (props.color) {
    styles['--card-accent'] = props.color
    styles['--icon-color'] = props.color
  }
  return styles
})

const iconColor = computed(() => {
  if (props.color) return { color: props.color }
  return {}
})

const trendClass = computed(() => {
  if (!props.trend) return ''
  return `stat-card-trend--${props.trend}`
})

const trendValuePositive = computed(() => {
  if (!props.trendValue) return true
  return !String(props.trendValue).startsWith('-')
})
</script>

<style scoped>
.stat-card {
  background: var(--card-bg, #fff);
  border-radius: var(--radius-md, 8px);
  padding: 20px 24px;
  box-shadow: var(--shadow-sm, 0 1px 4px rgba(0, 0, 0, 0.06));
  border-left: 3px solid var(--card-accent, var(--brand-primary, #4f8cf7));
  transition: box-shadow var(--transition-base, 0.2s ease),
              transform var(--transition-base, 0.2s ease);
}

.stat-card-hover:hover {
  box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.08));
  transform: translateY(-2px);
}

.stat-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.stat-card-icon {
  opacity: 0.7;
}

.stat-card-label {
  font-size: 13px;
  color: var(--text-tertiary, #909399);
  font-weight: 500;
}

.stat-card-trend {
  margin-left: auto;
}

.stat-card-trend--up {
  color: var(--brand-success, #52c41a);
}

.stat-card-trend--down {
  color: var(--brand-danger, #f5222d);
}

.stat-card-trend--stable {
  color: var(--text-tertiary, #909399);
}

.stat-card-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary, #1a1a1a);
  line-height: 1.2;
}

.stat-card-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-tertiary, #909399);
  margin-left: 4px;
}

.stat-card-trend-value {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 6px;
  font-size: 12px;
}

.trend-up {
  color: var(--brand-danger, #f5222d);
  font-weight: 600;
}

.trend-down {
  color: var(--brand-success, #52c41a);
  font-weight: 600;
}

.trend-label {
  color: var(--text-tertiary, #909399);
}
</style>
