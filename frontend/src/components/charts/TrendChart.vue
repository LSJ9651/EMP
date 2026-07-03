<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  series: { type: Array, default: () => [] },
})

const chartRef = ref(null)
let chart = null

const COLORS = ['#1890ff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#722ed1']

function initChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  updateChart()
}

function updateChart() {
  if (!chart) return

  const echartsSeries = (props.series || []).map((s, i) => ({
    name: s.name,
    type: 'line',
    smooth: true,
    showSymbol: false,
    lineStyle: { width: 2 },
    color: COLORS[i % COLORS.length],
    data: (s.data || []).map(d => [d.timestamp, d.power]),
  }))

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = ''
        params.forEach(p => {
          if (p.value[1] !== undefined) {
            html += `<div style="display:flex;align-items:center;gap:6px;margin:2px 0">
              <span style="width:10px;height:10px;border-radius:50%;background:${p.color};display:inline-block"></span>
              ${p.seriesName}: <strong>${p.value[1].toFixed(2)} kW</strong>
            </div>`
          }
        })
        return html
      },
    },
    legend: {
      bottom: 0,
      data: (props.series || []).map(s => s.name),
    },
    grid: { left: 60, right: 20, top: 20, bottom: 40 },
    xAxis: {
      type: 'time',
      axisLabel: {
        formatter: '{HH}:{mm}:{ss}',
        fontSize: 10,
      },
    },
    yAxis: {
      type: 'value',
      name: 'kW',
      axisLabel: { fontSize: 11 },
    },
    series: echartsSeries,
  }, true)
}

watch(() => props.series, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
})
</script>
