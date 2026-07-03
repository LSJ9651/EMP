<template>
  <div ref="chartRef" class="chart-box"></div>
</template>

<script setup>
import { ref, onMounted, watch, onUnmounted } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: { type: Array, default: () => [] },
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
  if (!chart || !props.data.length) return

  // 按设备分组
  const deviceMap = {}
  const devices = []

  props.data.forEach((item, index) => {
    const name = item.device_name || `设备${item.device_id}`
    if (!deviceMap[name]) {
      deviceMap[name] = []
      devices.push(name)
    }
    deviceMap[name].push({ ...item, index })
  })

  const deviceData = devices.map((name, i) => ({
    name,
    itemStyle: { color: ['#67c23a', '#1890ff', '#e6a23c', '#f56c6c', '#909399'][i % 5] },
  }))

  const seriesData = devices.map((name) => {
    const items = deviceMap[name]
    return {
      name,
      type: 'custom',
      renderItem: (params, api) => {
        const categoryIndex = api.value(0)
        const start = api.coord([api.value(1), categoryIndex])
        const end = api.coord([api.value(2), categoryIndex])
        const height = api.size([0, 1])[1] * 0.6

        return {
          type: 'rect',
          shape: {
            x: start[0],
            y: start[1] - height / 2,
            width: Math.max(end[0] - start[0], 2),
            height: height,
          },
          style: api.style(),
        }
      },
      encode: {
        x: [1, 2],
        y: 0,
      },
      data: items.map((item) => {
        const startH = parseInt(item.start?.split(':')[0] || '0')
        const startM = parseInt(item.start?.split(':')[1] || '0')
        const endH = parseInt(item.end?.split(':')[0] || '0')
        const endM = parseInt(item.end?.split(':')[1] || '0')

        let startHour = startH + startM / 60
        let endHour = endH + endM / 60

        // 跨天处理
        if (endHour <= startHour) endHour += 24

        return {
          name: item.device_name || `设备${item.device_id}`,
          value: [devices.indexOf(item.device_name || `设备${item.device_id}`), startHour, endHour, item.action],
          itemStyle: {
            color: item.action === 'run' ? '#67c23a' : item.action === 'idle' ? '#e6a23c' : '#909399',
          },
        }
      }),
      itemStyle: { borderRadius: 4 },
    }
  })

  chart.setOption({
    tooltip: {
      formatter: (params) => {
        const data = params.data || {}
        const actionMap = { run: '运行', idle: '待机', off: '关机' }
        return `${params.seriesName}<br/>${params.value[1].toFixed(1)}h - ${params.value[2].toFixed(1)}h<br/>${actionMap[params.value[3]] || params.value[3]}`
      },
    },
    grid: { left: 120, right: 30, top: 20, bottom: 30 },
    xAxis: {
      type: 'value',
      min: 0,
      max: 24,
      interval: 2,
      axisLabel: { formatter: '{value}:00' },
      name: '时间(h)',
    },
    yAxis: {
      type: 'category',
      data: devices,
      axisLabel: { fontSize: 12 },
    },
    series: seriesData,
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
