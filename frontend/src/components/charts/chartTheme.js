// ============================================================
// Unified ECharts Color Palette & Theme Configuration
// Aligned with brand tokens from style.scss
// ============================================================

export const COLORS = [
  '#4f8cf7', '#52c41a', '#faad14', '#f5222d', '#8c8c8c', '#722ed1',
]

export const BASE_OPTIONS = {
  backgroundColor: 'transparent',
  textStyle: {
    fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
  },
  tooltip: {
    backgroundColor: 'rgba(255, 255, 255, 0.96)',
    borderColor: '#e4e7ed',
    borderWidth: 1,
    textStyle: { color: '#303133', fontSize: 13 },
    shadowColor: 'rgba(0, 0, 0, 0.08)',
    shadowBlur: 12,
  },
  legend: {
    textStyle: { color: '#606266', fontSize: 12 },
  },
  grid: {
    left: 60,
    right: 20,
    top: 20,
    bottom: 40,
  },
}
