<template>
  <div ref="chartRef" class="sankey-chart"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { COLORS } from './chartTheme.js'

const props = defineProps({
  data: { type: Object, default: () => ({ nodes: [], links: [] }) },
})

const chartRef = ref(null)
let chart = null

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
    name: n.name,
    itemStyle: {
      color: COLORS[n.category] || '#8c8c8c',
    },
  }))

  const links = (props.data.links || []).map(l => ({
    source: l.source,
    target: l.target,
    value: l.value,
  }))

  chart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        if (params.dataType === 'node') {
          return `${params.name}`
        }
        return `${params.data.source} → ${params.data.target}<br/>功率: ${params.data.value} kW`
      },
    },
    series: [
      {
        type: 'sankey',
        layout: 'none',
        layoutIterations: 0,
        emphasis: {
          focus: 'adjacency',
        },
        nodeAlign: 'left',
        data: nodes,
        links: links,
        label: {
          show: true,
          fontSize: 12,
          position: 'right',
        },
        lineStyle: {
          color: 'gradient',
          curveness: 0.5,
        },
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

<style scoped>
.sankey-chart {
  width: 100%;
  height: 500px;
}
</style>
