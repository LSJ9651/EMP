<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Object, default: () => ({ nodes: [], links: [] }) },
})

const chartRef = ref(null)
let chart = null

const CATEGORIES = [
  { name: '变压器' },
  { name: '车间' },
  { name: '设备' },
]

function initChart() {
  if (!chartRef.value) return
  if (!chart) {
    chart = echarts.init(chartRef.value)
  }
  updateChart()
}

function updateChart() {
  if (!chart || !props.data?.nodes?.length) return

  const nodes = props.data.nodes.map(n => ({
    ...n,
    symbolSize: Math.max(20, Math.min(n.value / 2, 60)),
    label: {
      show: true,
      fontSize: 11,
      position: 'bottom',
    },
    itemStyle: {
      color: ['#1890ff', '#67c23a', '#e6a23c'][n.category] || '#909399',
    },
  }))

  const links = (props.data.links || []).map(l => ({
    ...l,
    lineStyle: {
      width: Math.max(1, l.value / 10),
      curveness: 0.2,
      color: '#c0c4cc',
    },
    label: {
      show: l.value > 30,
      formatter: `${l.value} kW`,
      fontSize: 10,
    },
  }))

  chart.setOption({
    tooltip: {
      formatter: (params) => {
        if (params.dataType === 'node') {
          return `${params.name}<br/>功率: ${params.value} kW`
        }
        return `${params.data.source} → ${params.data.target}<br/>${params.data.value} kW`
      },
    },
    legend: {
      bottom: 0,
      data: CATEGORIES.map(c => c.name),
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        force: { repulsion: 300, edgeLength: [100, 200] },
        roam: true,
        draggable: true,
        categories: CATEGORIES,
        data: nodes,
        links: links,
        label: { show: true, position: 'bottom', fontSize: 11 },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: 8,
      },
    ],
  }, true)
}

watch(() => props.data, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chart?.resize())
})

onUnmounted(() => {
  chart?.dispose()
})
</script>
