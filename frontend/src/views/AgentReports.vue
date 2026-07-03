<template>
  <div class="reports-page">
    <PageTitle title="智能报告" icon="Document" />

    <el-tabs v-model="activeTab" type="border-card">
      <!-- ========== Tab 1: 能耗分析 ========== -->
      <el-tab-pane label="能耗分析" name="analysis">
        <el-row :gutter="16">
          <el-col :span="14">
            <el-card header="能耗分析" style="margin-bottom: 16px">
              <el-form :inline="true">
                <el-form-item label="目标设备">
                  <el-select v-model="analyzeForm.device_id" placeholder="全部设备" clearable style="width: 180px">
                    <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="runAnalysis" :loading="analyzing">
                    <el-icon><Search /></el-icon>开始分析
                  </el-button>
                </el-form-item>
              </el-form>

              <div v-if="analysisResult" style="margin-top: 16px">
                <el-alert :title="analysisResult.summary" type="info" :closable="false" style="margin-bottom: 16px" />

                <h4 style="margin-bottom: 8px">异常检测</h4>
                <div v-if="analysisResult.anomalies?.length === 0" style="color: #52c41a; padding: 8px 0">未检测到异常</div>
                <div v-for="a in analysisResult.anomalies" :key="a.device_id" style="margin-bottom: 8px">
                  <el-tag :type="a.severity === 'high' ? 'danger' : 'warning'" size="small" round style="margin-right: 8px">
                    {{ a.severity === 'high' ? '严重' : '中等' }}
                  </el-tag>
                  {{ a.message }}
                </div>

                <div v-if="analysisResult.period_comparison?.devices?.length > 0" style="margin: 16px 0">
                  <h4 style="margin-bottom: 8px">同环比分析</h4>
                  <el-table :data="analysisResult.period_comparison.devices" border size="small" style="width: 100%">
                    <el-table-column prop="device_name" label="设备" />
                    <el-table-column prop="current_energy_kwh" label="当前能耗(kWh)" />
                    <el-table-column prop="previous_energy_kwh" label="上期能耗(kWh)" />
                    <el-table-column label="变化率">
                      <template #default="{ row }">
                        <span :style="{ color: row.ratio_pct >= 100 ? '#f5222d' : '#52c41a', fontWeight: 'bold' }">
                          {{ row.ratio_pct }}%
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column label="趋势">
                      <template #default="{ row }">
                        <el-tag v-if="row.trend === 'up'" type="danger" size="small" round>↑ 上升</el-tag>
                        <el-tag v-else-if="row.trend === 'down'" type="success" size="small" round>↓ 下降</el-tag>
                        <el-tag v-else type="info" size="small" round>→ 持平</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="delta_kwh" label="差值(kWh)" />
                  </el-table>
                </div>

                <h4 style="margin: 16px 0 8px">节能建议</h4>
                <div v-if="analysisResult.suggestions?.length > 0">
                  <el-tag v-for="(s, i) in analysisResult.suggestions" :key="i" effect="plain" style="margin: 0 8px 8px 0">
                    {{ s }}
                  </el-tag>
                </div>
                <div v-else style="color: var(--text-tertiary); padding: 8px 0">暂无建议</div>
              </div>
            </el-card>
          </el-col>

          <el-col :span="10">
            <el-card>
              <template #header>
                <div class="report-filter-header">
                  <span>历史报告</span>
                  <el-button
                    v-if="reportType || selectedDeviceId || deviceNameFilter"
                    link type="danger" size="small" @click="resetReportFilters"
                  >
                    清除筛选
                  </el-button>
                </div>
              </template>

              <div class="report-filter-bar">
                <el-select v-model="selectedDeviceId" placeholder="按设备筛选" clearable style="width: 100%; margin-bottom: 8px" @change="onDeviceFilterChange">
                  <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
                </el-select>
                <el-input
                  v-model="deviceNameFilter"
                  placeholder="设备名称模糊搜索"
                  clearable
                  style="margin-bottom: 8px"
                  @clear="onDeviceNameFilterClear"
                  @keyup.enter="fetchReports()"
                >
                  <template #suffix>
                    <el-icon style="cursor: pointer" @click="fetchReports()"><Search /></el-icon>
                  </template>
                </el-input>
                <el-date-picker
                  v-model="reportDateRange"
                  type="daterange"
                  range-separator="至"
                  start-placeholder="起始日期"
                  end-placeholder="结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYY-MM-DD"
                  style="width: 100%; margin-bottom: 8px"
                  @change="onDateRangeChange"
                />
                <el-select v-model="reportType" placeholder="报告类型" clearable style="width: 100%" @change="fetchReports">
                  <el-option label="全部" value="" />
                  <el-option label="能耗分析" value="analysis" />
                  <el-option label="调度优化" value="schedule" />
                </el-select>
              </div>

              <div v-if="reportType || selectedDeviceId || deviceNameFilter || reportDateRange" class="active-filters">
                <el-tag v-if="reportDateRange" closable size="small" type="danger" round @close="reportDateRange = null; fetchReports()">
                  时间: {{ reportDateRange[0] }} ~ {{ reportDateRange[1] }}
                </el-tag>
                <el-tag v-if="selectedDeviceId" closable size="small" type="primary" round @close="selectedDeviceId = null; fetchReports()">
                  设备: {{ getDeviceNameById(selectedDeviceId) }}
                </el-tag>
                <el-tag v-if="deviceNameFilter" closable size="small" type="warning" round @close="deviceNameFilter = ''; fetchReports()">
                  名称: {{ deviceNameFilter }}
                </el-tag>
                <el-tag v-if="reportType" closable size="small" type="success" round @close="reportType = ''; fetchReports()">
                  类型: {{ reportType === 'analysis' ? '能耗分析' : '调度优化' }}
                </el-tag>
              </div>

              <div v-loading="reportLoading" class="report-list-container">
                <div v-if="reports.length === 0" class="report-empty">
                  <el-icon :size="32" color="var(--text-placeholder)"><Document /></el-icon>
                  <p>{{ activeFiltersCount > 0 ? '未找到匹配的报告' : '暂无报告' }}</p>
                </div>
                <div v-for="r in reports" :key="r.id" class="report-item" @click="selectReport(r)">
                  <div class="report-header">
                    <el-tag :type="r.report_type === 'analysis' ? 'primary' : 'success'" size="small" round>
                      {{ r.report_type === 'analysis' ? '能耗分析' : '调度优化' }}
                    </el-tag>
                    <span class="report-time">{{ r.created_at }}</span>
                  </div>
                  <div class="report-summary">{{ r.input_summary }}</div>
                </div>
              </div>

              <div v-if="reportTotalPages > 1" class="report-pagination">
                <el-pagination
                  v-model:current-page="reportPage"
                  :page-size="reportPageSize"
                  :total="reportTotal"
                  layout="prev, pager, next, total"
                  small
                  @current-change="fetchReports"
                />
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- ========== Tab 2: 订阅管理 ========== -->
      <el-tab-pane label="订阅管理" name="subscription">
        <Toolbar>
          <template #left>
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon>新建订阅
            </el-button>
          </template>
        </Toolbar>

        <transition name="status-fade">
          <div v-if="executingRows.size > 0" class="execution-status-bar" role="status" aria-live="polite">
            <el-icon class="is-loading" :size="16"><Loading /></el-icon>
            <span>
              正在执行：<strong>{{ executingRows.size }}</strong> 个订阅任务，
              当前阶段：{{ currentExecutionStage }}
            </span>
          </div>
        </transition>

        <el-table :data="subscriptions" border style="width: 100%">
          <el-table-column prop="name" label="名称" min-width="100" />
          <el-table-column label="报告类型" width="100">
            <template #default="{ row }">
              <el-tag v-if="row.report_type === 'daily'" type="primary" size="small" round>日报</el-tag>
              <el-tag v-else-if="row.report_type === 'weekly'" type="warning" size="small" round>周报</el-tag>
              <el-tag v-else type="info" size="small" round>分析报告</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="cron_time" label="执行时间" width="100" />
          <el-table-column label="通知方式" width="140">
            <template #default="{ row }">
              <span style="font-size: 13px">
                {{ row.notify_method === 'system' ? '系统通知' : row.notify_method === 'email' ? '邮件' : '钉钉' }}
              </span>
              <el-tag v-if="row.notify_method !== 'system' && row.notify_config" size="small" type="success" round style="margin-left: 4px">已配置</el-tag>
              <el-tag v-else-if="row.notify_method !== 'system' && !row.notify_config" size="small" type="warning" round style="margin-left: 4px">未配置</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="订阅状态" width="90">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small" round>
                {{ row.is_active ? '启用' : '禁用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="上次执行" width="150">
            <template #default="{ row }">
              {{ row.last_run_at || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="执行状态" width="130">
            <template #default="{ row }">
              <template v-if="executingRows.has(row.id)">
                <el-progress :percentage="executionProgress.get(row.id) || 30" :stroke-width="4" :show-text="false" style="width: 80px; display: inline-block; vertical-align: middle" />
                <span style="font-size: 12px; color: var(--brand-primary); margin-left: 4px">执行中</span>
              </template>
              <template v-else-if="executionResults.has(row.id)">
                <span v-if="executionResults.get(row.id).success">
                  <el-icon color="#52c41a"><CircleCheck /></el-icon>
                  <a href="javascript:void(0)" @click="viewExecutionResult(row.id)" style="font-size: 12px; margin-left: 2px; color: var(--brand-primary)">查看结果</a>
                </span>
                <span v-else>
                  <el-icon color="#f5222d"><CircleClose /></el-icon>
                  <el-tooltip :content="executionResults.get(row.id).error" placement="top">
                    <span style="font-size: 12px; color: #f5222d; margin-left: 2px; cursor: help">失败</span>
                  </el-tooltip>
                </span>
              </template>
              <template v-else>
                <span style="color: var(--text-placeholder); font-size: 12px">—</span>
              </template>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="300" fixed="right">
            <template #default="{ row }">
              <el-button type="success" link size="small" @click="viewSubReports(row)">查看报告</el-button>
              <el-button type="primary" link size="small" @click="openEditDialog(row)" :disabled="executingRows.has(row.id)">编辑</el-button>
              <el-button
                type="warning"
                link
                size="small"
                @click="handleRun(row)"
                :loading="executingRows.has(row.id)"
                :disabled="executingRows.has(row.id)"
              >
                {{ executingRows.has(row.id) ? '执行中...' : '立即执行' }}
              </el-button>
              <el-popconfirm title="确定要删除此订阅吗？" @confirm="handleDelete(row.id)">
                <template #reference>
                  <el-button type="danger" link size="small" :disabled="executingRows.has(row.id)">删除</el-button>
                </template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>

        <!-- 新建/编辑订阅对话框 -->
        <el-dialog v-model="subDialogVisible" :title="isEditing ? '编辑订阅' : '新建订阅'" width="500px" top="5vh">
          <el-form :model="subForm" label-width="100px">
            <el-form-item label="名称">
              <el-input v-model="subForm.name" placeholder="请输入订阅名称" />
            </el-form-item>
            <el-form-item label="报告类型">
              <el-select v-model="subForm.report_type" style="width: 100%">
                <el-option label="日报" value="daily" />
                <el-option label="周报" value="weekly" />
                <el-option label="分析报告" value="analysis" />
              </el-select>
            </el-form-item>
            <el-form-item label="执行时间">
              <el-time-picker v-model="subForm.cron_time_obj" format="HH:mm" value-format="HH:mm" placeholder="选择时间" style="width: 100%" />
            </el-form-item>
            <el-form-item label="通知方式">
              <el-select v-model="subForm.notify_method" style="width: 100%" @change="onNotifyMethodChange">
                <el-option label="系统通知" value="system" />
                <el-option label="邮件" value="email" />
                <el-option label="钉钉" value="dingtalk" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="subForm.notify_method === 'email'" label="邮件配置">
              <EmailNotifyConfig ref="emailConfigRef" v-model="subForm.notify_config" />
            </el-form-item>
            <el-form-item v-if="subForm.notify_method === 'dingtalk'" label="钉钉配置">
              <DingtalkNotifyConfig ref="dingtalkConfigRef" v-model="subForm.notify_config" />
            </el-form-item>
            <el-form-item label="目标设备">
              <el-select v-model="subForm.device_ids_list" multiple placeholder="全部设备" style="width: 100%">
                <el-option v-for="d in devices" :key="d.id" :label="d.name" :value="d.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="启用状态">
              <el-switch v-model="subForm.is_active" />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="subDialogVisible = false">取消</el-button>
            <el-button type="primary" @click="handleSaveSub" :loading="subSaving">保存</el-button>
          </template>
        </el-dialog>

        <!-- 订阅报告查看对话框 -->
        <el-dialog v-model="subReportDialogVisible" width="800px" :close-on-click-modal="false" top="5vh">
          <template #header>
            <div style="display: flex; align-items: center; gap: 12px">
              <h3 style="margin: 0">📊 订阅报告：{{ selectedSubscription?.name }}</h3>
              <el-tag :type="selectedSubscription?.is_active ? 'success' : 'info'" size="small" round>
                {{ selectedSubscription?.is_active ? '启用中' : '已禁用' }}
              </el-tag>
            </div>
          </template>
          <div class="sub-report-filter">
            <el-date-picker
              v-model="subReportDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="起始日期"
              end-placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              size="small"
              style="width: 260px"
              @change="fetchSubReports"
            />
            <span style="margin-left: 12px; font-size: 13px; color: var(--text-tertiary)">
              共 {{ subReportTotal }} 条报告
            </span>
          </div>
          <div v-loading="subReportLoading" style="min-height: 200px; max-height: 460px; overflow-y: auto">
            <div v-if="subReports.length === 0" style="text-align: center; padding: 48px; color: var(--text-placeholder)">
              <el-icon :size="32"><Document /></el-icon>
              <p style="margin-top: 8px">该订阅暂无生成的报告</p>
            </div>
            <div v-for="r in subReports" :key="r.id" class="sub-report-item" @click="selectSubReport(r)">
              <div class="sub-report-header">
                <el-tag :type="r.report_type === 'analysis' ? 'primary' : 'success'" size="small" round>
                  {{ r.report_type === 'analysis' ? '能耗分析' : '调度优化' }}
                </el-tag>
                <span style="font-size: 12px; color: var(--text-tertiary)">{{ r.created_at }}</span>
              </div>
              <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px">{{ r.input_summary }}</div>
            </div>
          </div>
          <div v-if="subReportTotalPages > 1" style="display: flex; justify-content: center; margin-top: 12px">
            <el-pagination
              v-model:current-page="subReportPage"
              :page-size="subReportPageSize"
              :total="subReportTotal"
              layout="prev, pager, next"
              small
              @current-change="fetchSubReports"
            />
          </div>
        </el-dialog>
      </el-tab-pane>
    </el-tabs>

    <!-- ════════ 报告详情对话框 ════════ -->
    <el-dialog v-model="detailVisible" width="920px" top="2vh" class="report-detail-dialog" :close-on-click-modal="false">
      <template #header>
        <div class="rd-header">
          <div>
            <h2 class="rd-title">
              <el-tag :type="selectedReport?.report_type === 'analysis' ? 'primary' : 'success'" size="large" style="margin-right: 10px" round>
                {{ selectedReport?.report_type === 'analysis' ? '能耗分析报告' : '调度优化报告' }}
              </el-tag>
            </h2>
          </div>
          <div class="rd-actions">
            <el-button link type="primary" @click="printReport">
              <el-icon><Printer /></el-icon>打印
            </el-button>
            <el-button link type="primary" @click="showRawJson = !showRawJson">
              {{ showRawJson ? '格式化视图' : '原始JSON' }}
            </el-button>
          </div>
        </div>
      </template>

      <div v-if="selectedReport" class="report-detail-body" ref="reportPrintEl">
        <div class="rd-meta">
          <div class="rd-meta-item">
            <span class="label">触发方式</span>
            <span class="value">{{ formatTriggerSource(selectedReport.input_summary) }}</span>
          </div>
          <div class="rd-meta-item">
            <span class="label">生成时间</span>
            <span class="value">{{ selectedReport.created_at }}</span>
          </div>
          <div v-if="reportTimeRange" class="rd-meta-item">
            <span class="label">分析时间范围</span>
            <span class="value">{{ reportTimeRange }}</span>
          </div>
          <div class="rd-meta-item">
            <span class="label">分析模式</span>
            <span class="value">
              <el-tag :type="reportMode === 'cloud' ? '' : 'info'" size="small" effect="plain" round>
                {{ reportMode === 'cloud' ? '☁ 云端智能' : '💻 本地规则' }}
              </el-tag>
            </span>
          </div>
        </div>

        <template v-if="showRawJson">
          <pre class="report-json">{{ JSON.stringify(selectedReport.output_json, null, 2) }}</pre>
        </template>

        <template v-else>
          <template v-if="selectedReport.report_type === 'analysis'">
            <div class="rp-section">
              <h3 class="rp-section-title">
                <span class="rp-section-icon">📋</span>分析摘要
              </h3>
              <div class="rp-summary-box">
                {{ reportData.summary || '无摘要信息' }}
              </div>
            </div>

            <div class="rp-section">
              <h3 class="rp-section-title">
                <span class="rp-section-icon">📊</span>关键指标
              </h3>
              <el-row :gutter="16">
                <el-col :sm="8" :xs="24">
                  <div class="rp-kpi-card">
                    <div class="kpi-value">
                      {{ reportData.total_power_avg ?? '-' }}
                      <span class="kpi-unit" v-if="reportData.total_power_avg != null">kW</span>
                    </div>
                    <div class="kpi-label">平均功率</div>
                    <el-progress
                      v-if="reportData.total_power_avg != null"
                      :percentage="Math.round((reportData.total_power_avg / 75) * 100)"
                      :stroke-width="6"
                      :show-text="false"
                    />
                  </div>
                </el-col>
                <el-col :sm="8" :xs="24">
                  <div class="rp-kpi-card">
                    <div class="kpi-value">{{ reportData.analyzed_devices ?? '-' }}<span class="kpi-unit">台</span></div>
                    <div class="kpi-label">分析设备数</div>
                  </div>
                </el-col>
                <el-col :sm="8" :xs="24">
                  <div class="rp-kpi-card" :class="anomalyCount > 0 ? 'rp-kpi-warn' : 'rp-kpi-ok'">
                    <div class="kpi-value">{{ anomalyCount }}</div>
                    <div class="kpi-label">{{ anomalyCount > 0 ? '⚠ 检测到异常' : '✓ 运行正常' }}</div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <div class="rp-section" v-if="anomalyCount > 0">
              <h3 class="rp-section-title">
                <span class="rp-section-icon">⚠️</span>异常检测 ({{ anomalyCount }}项)
              </h3>
              <div v-for="(a, i) in reportData.anomalies" :key="i" class="rp-anomaly-item" :class="'severity-' + (a.severity || 'medium')">
                <div class="anomaly-header">
                  <el-tag
                    :type="a.severity === 'high' ? 'danger' : a.severity === 'medium' ? 'warning' : 'info'"
                    size="small"
                    effect="dark"
                    round
                  >
                    {{ a.severity === 'high' ? '严重' : a.severity === 'medium' ? '中等' : '提示' }}
                  </el-tag>
                  <span class="anomaly-device" v-if="a.device_name">{{ a.device_name }}</span>
                </div>
                <p class="anomaly-msg">{{ a.message }}</p>
              </div>
            </div>
          </template>

          <template v-else>
            <div class="rp-section">
              <h3 class="rp-section-title">
                <span class="rp-section-icon">🧠</span>优化推理
              </h3>
              <div class="rp-summary-box">
                {{ reportData.reasoning || '基于电价和设备特性进行优化调度' }}
              </div>
            </div>

            <div class="rp-section">
              <h3 class="rp-section-title">
                <span class="rp-section-icon">📊</span>关键指标
              </h3>
              <el-row :gutter="16">
                <el-col :sm="8" :xs="24">
                  <div class="rp-kpi-card rp-kpi-ok">
                    <div class="kpi-value">¥{{ reportData.estimated_cost_saved ?? '-' }}</div>
                    <div class="kpi-label">预计节省成本</div>
                  </div>
                </el-col>
                <el-col :sm="8" :xs="24">
                  <div class="rp-kpi-card">
                    <div class="kpi-value">{{ reportData.schedule?.length ?? '-' }}<span class="kpi-unit">条</span></div>
                    <div class="kpi-label">调度任务数</div>
                  </div>
                </el-col>
              </el-row>
            </div>

            <div class="rp-section" v-if="reportData.schedule?.length > 0">
              <h3 class="rp-section-title">
                <span class="rp-section-icon">📅</span>调度计划
              </h3>
              <el-table :data="reportData.schedule" border size="small" style="width: 100%" :default-sort="{ prop: 'start', order: 'ascending' }">
                <el-table-column prop="device_name" label="设备" min-width="100" />
                <el-table-column prop="start" label="开始" sortable min-width="80" />
                <el-table-column prop="end" label="结束" min-width="80" />
                <el-table-column label="动作" min-width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.action === 'run' ? 'success' : 'warning'" size="small" effect="dark" round>
                      {{ row.action === 'run' ? '运行' : '待机' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="电价" min-width="80">
                  <template #default="{ row }">
                    ¥{{ row.price_per_kwh }}/kWh
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </template>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, reactive, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Plus, Loading, CircleCheck, CircleClose, Printer, Document } from '@element-plus/icons-vue'
import {
  getDevices, analyzeEnergy, getAgentReports, getSubscriptionReports,
  getSubscriptions, createSubscription, updateSubscription, deleteSubscription, runSubscription
} from '../api/api.js'
import EmailNotifyConfig from '../components/config/EmailNotifyConfig.vue'
import DingtalkNotifyConfig from '../components/config/DingtalkNotifyConfig.vue'
import PageTitle from '../components/common/PageTitle.vue'
import Toolbar from '../components/common/Toolbar.vue'

const activeTab = ref('analysis')
const devices = ref([])
const reports = ref([])
const reportLoading = ref(false)
const reportType = ref('')
const selectedDeviceId = ref(null)
const deviceNameFilter = ref('')
const reportDateRange = ref(null)
const reportPage = ref(1)
const reportPageSize = ref(20)
const reportTotal = ref(0)
const reportTotalPages = ref(1)
const analyzing = ref(false)
const analysisResult = ref(null)

const analyzeForm = ref({ device_id: null })

const detailVisible = ref(false)
const selectedReport = ref(null)
const showRawJson = ref(false)
const reportPrintEl = ref(null)

const reportData = computed(() => {
  return selectedReport.value?.output_json || {}
})
const reportTimeRange = computed(() => {
  return reportData.value.time_range || ''
})
const reportMode = computed(() => {
  return reportData.value._mode || reportData.value.mode || 'unknown'
})
const anomalyCount = computed(() => {
  return reportData.value.anomalies?.length || 0
})

const route = useRoute()
const router = useRouter()

const activeFiltersCount = computed(() => {
  let n = 0
  if (reportType.value) n++
  if (selectedDeviceId.value) n++
  if (deviceNameFilter.value) n++
  if (reportDateRange.value) n++
  return n
})

// ===== 订阅执行状态管理 =====
const executingRows = reactive(new Set())
const executionProgress = reactive(new Map())
const executionResults = reactive(new Map())
const currentExecutionStage = ref('')
let executionTimer = null

function clearExecutionTimer() {
  if (executionTimer) {
    clearInterval(executionTimer)
    executionTimer = null
  }
}

function startProgressSim(subId) {
  executionProgress.set(subId, 5)
  currentExecutionStage.value = '数据采集中...'
  let progress = 5
  clearExecutionTimer()
  executionTimer = setInterval(() => {
    if (progress < 60) {
      progress += Math.random() * 8 + 2
      currentExecutionStage.value = progress < 25 ? '数据采集中...' : 'AI 分析计算中...'
    } else if (progress < 90) {
      progress += Math.random() * 3 + 1
      currentExecutionStage.value = '结果汇总中...'
    }
    if (progress >= 99) {
      progress = 99
      clearExecutionTimer()
    }
    executionProgress.set(subId, Math.min(99, Math.floor(progress)))
  }, 800)
}

function finishProgress(subId) {
  clearExecutionTimer()
  executionProgress.set(subId, 100)
  currentExecutionStage.value = ''
}

// ===== 订阅管理 =====
const subscriptions = ref([])
const subLoading = ref(false)
const subDialogVisible = ref(false)
const subSaving = ref(false)
const isEditing = ref(false)
const editingId = ref(null)

// ===== 订阅报告查看 =====
const subReportDialogVisible = ref(false)
const selectedSubscription = ref(null)
const subReports = ref([])
const subReportLoading = ref(false)
const subReportDateRange = ref(null)
const subReportPage = ref(1)
const subReportPageSize = ref(10)
const subReportTotal = ref(0)
const subReportTotalPages = ref(1)

const subForm = ref({
  name: '',
  report_type: 'daily',
  cron_time_obj: null,
  notify_method: 'system',
  notify_config: {},
  device_ids_list: [],
  is_active: true,
})

const emailConfigRef = ref(null)
const dingtalkConfigRef = ref(null)

async function fetchDevicesList() {
  const res = await getDevices()
  if (res.code === 200) devices.value = res.data
}

async function fetchReports() {
  reportLoading.value = true
  try {
    const params = {
      report_type: reportType.value || undefined,
      device_id: selectedDeviceId.value || undefined,
      device_name: deviceNameFilter.value || undefined,
      page: reportPage.value,
      page_size: reportPageSize.value,
    }
    if (reportDateRange.value && reportDateRange.value.length === 2) {
      params.start_time = reportDateRange.value[0] + 'T00:00:00'
      params.end_time = reportDateRange.value[1] + 'T23:59:59'
    }
    const res = await getAgentReports(params)
    if (res.code === 200) {
      const data = res.data
      reports.value = data.items || []
      reportTotal.value = data.pagination?.total || data.items?.length || 0
      reportTotalPages.value = data.pagination?.total_pages || 1
      reportPage.value = data.pagination?.page || 1
    }
  } finally { reportLoading.value = false }
}

function onDateRangeChange() {
  reportPage.value = 1
  fetchReports()
}

function onDeviceFilterChange() {
  if (selectedDeviceId.value) {
    deviceNameFilter.value = ''
  }
  fetchReports()
}

function onDeviceNameFilterClear() {
  fetchReports()
}

function resetReportFilters() {
  reportType.value = ''
  selectedDeviceId.value = null
  deviceNameFilter.value = ''
  reportDateRange.value = null
  reportPage.value = 1
  fetchReports()
}

function getDeviceNameById(id) {
  const d = devices.value.find(d => d.id === id)
  return d ? d.name : `#${id}`
}

async function runAnalysis() {
  analyzing.value = true
  analysisResult.value = null
  try {
    const res = await analyzeEnergy({
      device_id: analyzeForm.value.device_id || undefined,
    })
    if (res.code === 200) {
      analysisResult.value = res.data
      ElMessage.success('分析完成')
      await fetchReports()
    }
  } catch (e) {
    ElMessage.error('分析失败')
  } finally {
    analyzing.value = false
  }
}

function selectReport(r) {
  selectedReport.value = r
  showRawJson.value = false
  detailVisible.value = true
}

function formatTriggerSource(summary) {
  if (!summary) return '手动分析'
  if (summary.includes('subscription_manual') || summary.includes('subscription_id') && !summary.includes('scheduled')) return '📌 订阅手动执行'
  if (summary.includes('scheduled')) return '⏰ 定时执行'
  if (summary.includes('device_id=')) return '🔍 手动分析'
  return summary
}

function printReport() {
  if (!reportPrintEl.value) return
  const win = window.open('', '_blank', 'width=900,height=700')
  if (!win) return
  const styles = document.querySelectorAll('style, link[rel="stylesheet"]')
  let styleHtml = ''
  styles.forEach(s => { styleHtml += s.outerHTML })
  win.document.write(`
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>能耗分析报告</title>${styleHtml}</head>
    <body style="padding:24px 32px; font-size:14px; color:#303133; max-width:900px; margin:0 auto;">
      ${reportPrintEl.value.innerHTML}
    </body>
    </html>
  `)
  win.document.close()
  setTimeout(() => win.print(), 300)
}

// ========== 订阅管理方法 ==========
async function fetchSubscriptions() {
  subLoading.value = true
  try {
    const res = await getSubscriptions()
    if (res.code === 200) {
      subscriptions.value = res.data.items || res.data || []
    }
  } finally { subLoading.value = false }
}

function openCreateDialog() {
  isEditing.value = false
  editingId.value = null
  subForm.value = {
    name: '',
    report_type: 'daily',
    cron_time_obj: null,
    notify_method: 'system',
    notify_config: {},
    device_ids_list: [],
    is_active: true,
  }
  subDialogVisible.value = true
}

function openEditDialog(row) {
  isEditing.value = true
  editingId.value = row.id
  subForm.value = {
    name: row.name,
    report_type: row.report_type,
    cron_time_obj: row.cron_time,
    notify_method: row.notify_method,
    notify_config: row.notify_config || {},
    device_ids_list: row.device_ids ? row.device_ids.split(',').map(Number) : [],
    is_active: row.is_active,
  }
  subDialogVisible.value = true
}

function onNotifyMethodChange(val) {
  subForm.value.notify_config = {}
}

async function handleSaveSub() {
  subSaving.value = true
  try {
    if (subForm.value.notify_method === 'email' && emailConfigRef.value) {
      const valid = await emailConfigRef.value.validate()
      if (!valid) {
        ElMessage.warning('请检查邮件配置表单')
        return
      }
      subForm.value.notify_config = emailConfigRef.value.getConfig()
    }
    if (subForm.value.notify_method === 'dingtalk' && dingtalkConfigRef.value) {
      const valid = await dingtalkConfigRef.value.validate()
      if (!valid) {
        ElMessage.warning('请检查钉钉配置表单')
        return
      }
      subForm.value.notify_config = dingtalkConfigRef.value.getConfig()
    }

    const payload = {
      name: subForm.value.name,
      report_type: subForm.value.report_type,
      cron_time: subForm.value.cron_time_obj || '00:00',
      device_ids: subForm.value.device_ids_list.length > 0 ? subForm.value.device_ids_list.join(',') : null,
      notify_method: subForm.value.notify_method,
      is_active: subForm.value.is_active,
    }
    if (subForm.value.notify_method !== 'system') {
      payload.notify_config = subForm.value.notify_config
    }
    if (isEditing.value) {
      await updateSubscription(editingId.value, payload)
      ElMessage.success('订阅更新成功')
    } else {
      await createSubscription(payload)
      ElMessage.success('订阅创建成功')
    }
    subDialogVisible.value = false
    await fetchSubscriptions()
  } catch (e) {
    ElMessage.error('操作失败')
  } finally { subSaving.value = false }
}

async function handleRun(row) {
  if (executingRows.has(row.id)) return
  executionResults.delete(row.id)
  executingRows.add(row.id)
  startProgressSim(row.id)

  try {
    const res = await runSubscription(row.id)
    finishProgress(row.id)

    if (res.code === 200) {
      executionResults.set(row.id, {
        success: true,
        reportId: res.data?.report_id || null,
        error: null,
      })
      await fetchSubscriptions()
      ElMessage.success(`「${row.name}」执行完成`)
    } else {
      executionResults.set(row.id, {
        success: false,
        reportId: null,
        error: res.message || '未知错误',
      })
      ElMessage.error(`「${row.name}」执行失败: ${res.message || '未知错误'}`)
    }
  } catch (e) {
    finishProgress(row.id)
    const errMsg = e?.response?.data?.message || e?.message || '网络超时或服务器错误'
    executionResults.set(row.id, {
      success: false,
      reportId: null,
      error: errMsg,
    })
    ElMessage.error(`「${row.name}」执行失败: ${errMsg}`)
  } finally {
    executingRows.delete(row.id)
    setTimeout(() => {
      executionProgress.delete(row.id)
    }, 1500)
  }
}

function viewExecutionResult(subId) {
  const result = executionResults.get(subId)
  if (result && result.reportId) {
    activeTab.value = 'analysis'
    router.push({ path: '/reports', query: { report_id: result.reportId, tab: 'analysis' } })
  } else {
    activeTab.value = 'analysis'
  }
}

async function handleDelete(id) {
  try {
    await deleteSubscription(id)
    ElMessage.success('订阅已删除')
    await fetchSubscriptions()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

// ========== 订阅报告查看 ==========
function viewSubReports(sub) {
  selectedSubscription.value = sub
  subReportDateRange.value = null
  subReportPage.value = 1
  subReports.value = []
  subReportTotal.value = 0
  subReportTotalPages.value = 1
  subReportDialogVisible.value = true
  fetchSubReports()
}

async function fetchSubReports() {
  if (!selectedSubscription.value) return
  subReportLoading.value = true
  try {
    const params = {
      page: subReportPage.value,
      page_size: subReportPageSize.value,
    }
    if (subReportDateRange.value && subReportDateRange.value.length === 2) {
      params.start_time = subReportDateRange.value[0] + 'T00:00:00'
      params.end_time = subReportDateRange.value[1] + 'T23:59:59'
    }
    const res = await getSubscriptionReports(selectedSubscription.value.id, params)
    if (res.code === 200) {
      const data = res.data
      subReports.value = data.items || []
      subReportTotal.value = data.pagination?.total || 0
      subReportTotalPages.value = data.pagination?.total_pages || 1
      subReportPage.value = data.pagination?.page || 1
    }
  } finally {
    subReportLoading.value = false
  }
}

function selectSubReport(r) {
  subReportDialogVisible.value = false
  selectedReport.value = {
    ...r,
    output_json: r.output_json || {},
  }
  showRawJson.value = false
  detailVisible.value = true
}

onMounted(async () => {
  await fetchDevicesList()
  await fetchReports()
  await fetchSubscriptions()

  const qTab = route.query.tab
  const qReportId = route.query.report_id
  if (qTab) activeTab.value = qTab
  if (qReportId) {
    const target = reports.value.find(r => String(r.id) === String(qReportId))
    if (target) {
      selectReport(target)
    }
  }
})

watch(activeTab, (newTab) => {
  if (newTab === 'subscription') {
    fetchSubscriptions()
  }
})

onUnmounted(() => {
  clearExecutionTimer()
})
</script>

<style scoped>
/* ──── 执行状态栏 ──── */
.execution-status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  margin-bottom: 12px;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: #303133;
}

.status-fade-enter-active,
.status-fade-leave-active {
  transition: all 0.3s ease;
}
.status-fade-enter-from,
.status-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ──── 报告筛选 ──── */
.report-filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-filter-bar {
  padding: 8px 0;
}

.active-filters {
  margin-bottom: 8px;
}
.active-filters .el-tag {
  margin-right: 6px;
  margin-bottom: 4px;
}

.report-list-container {
  max-height: 520px;
  overflow-y: auto;
}

.report-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.report-item:hover {
  border-color: var(--brand-primary);
  background: #ecf5ff;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.report-time {
  font-size: 12px;
  color: var(--text-placeholder);
}
.report-summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.report-empty {
  text-align: center;
  padding: 32px;
  color: var(--text-placeholder);
}

/* ════════ 正式报告视图样式 ════════ */
.rd-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.rd-title {
  margin: 0;
  display: flex;
  align-items: center;
}
.rd-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.report-detail-body {
  padding: 0 4px;
}
.rd-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 16px 32px;
  padding: 12px 16px;
  background: var(--surface-bg);
  border-radius: var(--radius-md);
  margin-bottom: 20px;
  font-size: 13px;
}
.rd-meta-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.rd-meta-item .label {
  font-size: 11px;
  color: var(--text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.rd-meta-item .value {
  font-weight: 500;
  color: #303133;
}
.rp-section {
  margin-bottom: 24px;
}
.rp-section-title {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--brand-primary);
}
.rp-section-icon {
  font-size: 16px;
}
.rp-section-ok .rp-section-title {
  border-bottom-color: #52c41a;
}
.rp-summary-box {
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
  border-radius: var(--radius-md);
  padding: 14px 18px;
  font-size: 14px;
  line-height: 1.7;
  color: #1d4ed8;
}
.rp-kpi-card {
  background: var(--surface-bg);
  border-radius: var(--radius-md);
  padding: 16px;
  text-align: center;
  margin-bottom: 12px;
  transition: background 0.2s;
}
.rp-kpi-ok {
  background: #f0f9ff;
  border: 1px solid #b3d8ff;
}
.rp-kpi-warn {
  background: #fef3c7;
  border: 1px solid #fbbf24;
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: #303133;
  line-height: 1.2;
}
.kpi-unit {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-tertiary);
  margin-left: 4px;
}
.kpi-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 6px 0 10px;
}
.rp-anomaly-item {
  padding: 12px 16px;
  border-left: 4px solid #faad14;
  background: #fdf6ec;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  margin-bottom: 10px;
}
.rp-anomaly-item.severity-high {
  border-left-color: #f5222d;
  background: #fef0f0;
}
.rp-anomaly-item.severity-info {
  border-left-color: var(--brand-primary);
  background: #ecf5ff;
}
.anomaly-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.anomaly-device {
  font-size: 13px;
  color: var(--text-secondary);
  font-weight: 500;
}
.anomaly-msg {
  margin: 0;
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
}
.rp-suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  margin-bottom: 8px;
  background: var(--surface-bg);
  border-radius: var(--radius-sm);
}
.sugg-num {
  flex-shrink: 0;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--brand-primary);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sugg-text {
  font-size: 13px;
  color: #303133;
  line-height: 1.5;
}
.rp-no-data {
  text-align: center;
  padding: 16px;
  color: var(--text-tertiary);
  font-size: 13px;
}
.rp-no-data-happy {
  text-align: center;
  padding: 20px;
  color: #52c41a;
  font-size: 14px;
  font-weight: 500;
  background: #f0fdf4;
  border-radius: var(--radius-md);
}
.report-json {
  background: var(--surface-bg);
  padding: 16px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  max-height: 520px;
  overflow-y: auto;
  white-space: pre-wrap;
  border: 1px solid var(--border-color);
}

@media print {
  .rd-actions, .el-dialog__headerbtn {
    display: none !important;
  }
  .rp-section {
    margin-bottom: 16px;
  }
  .rp-section-title {
    border-bottom: 1px solid #333;
  }
  .rp-summary-box {
    border: 1px solid #ccc;
    background: none;
  }
}

/* ──── 分页控件 ──── */
.report-pagination {
  display: flex;
  justify-content: center;
  padding: 12px 0;
  margin-top: 8px;
  border-top: 1px solid var(--border-light);
}

/* ──── 订阅报告对话框 ──── */
.sub-report-filter {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-light);
}

.sub-report-item {
  padding: 12px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.sub-report-item:hover {
  border-color: #52c41a;
  background: #f0fdf4;
}

.sub-report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>
