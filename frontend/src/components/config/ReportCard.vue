<template>
  <div class="report-card">
    <div class="report-card-header">
      <el-tag :type="typeTag" size="small">{{ typeLabel }}</el-tag>
      <span class="report-card-time">{{ report.created_at }}</span>
    </div>
    <div class="report-card-body">
      <div class="report-card-summary">{{ report.input_summary }}</div>
      <div v-if="report.output_json?.summary" class="report-card-result">
        {{ report.output_json.summary }}
      </div>
      <div v-if="report.output_json?.estimated_cost_saved" class="report-card-cost">
        预计节省: ¥{{ report.output_json.estimated_cost_saved }}
      </div>
    </div>
    <div class="report-card-footer">
      <el-button type="primary" link size="small" @click="$emit('detail', report)">
        查看详情
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  report: { type: Object, required: true },
})

defineEmits(['detail'])

const typeLabel = computed(() => {
  return props.report.report_type === 'analysis' ? '能耗分析' : '调度优化'
})

const typeTag = computed(() => {
  return props.report.report_type === 'analysis' ? 'primary' : 'success'
})
</script>

<style scoped>
.report-card {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px;
  background: #fff;
  transition: box-shadow 0.2s;
}
.report-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}
.report-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.report-card-time {
  font-size: 12px;
  color: #8c8c8c;
}
.report-card-body {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
}
.report-card-summary {
  font-size: 12px;
  color: #a0a0a0;
  margin-bottom: 6px;
}
.report-card-result {
  padding: 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
}
.report-card-cost {
  color: #67c23a;
  font-weight: 600;
  font-size: 14px;
  margin-top: 6px;
}
.report-card-footer {
  border-top: 1px solid #ebeef5;
  padding-top: 8px;
}
</style>
