<script setup>
import { formatDateTime } from '@/utils/format'

defineProps({
  bid: { type: Object, required: true },
  reviewing: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle'])
</script>

<template>
  <div class="card">
    <div class="card-body">
      <h2 class="h6">검토 결과 확인</h2>
      <p class="small text-muted">
        요구사항·판정을 검토했으면 확인 완료로 표시하세요. 대시보드의 확인/미확인 건수에 반영됩니다.
        초안 편집과 PDF 다운로드는 초안 생성 기능과 함께 제공됩니다.
      </p>
      <dl class="row small">
        <dt class="col-sm-3">판정 요약</dt>
        <dd class="col-sm-9">
          <template v-if="bid.verdict_counts?.total">
            충족 {{ bid.verdict_counts.MET }} · 보완 필요
            {{ bid.verdict_counts.NEEDS_SUPPLEMENT }} · 확인 필요
            {{ bid.verdict_counts.NEEDS_CONFIRMATION }} · HIGH 위험 {{ bid.verdict_counts.HIGH }}
          </template>
          <span v-else class="text-muted">판정 전</span>
        </dd>
        <dt class="col-sm-3">담당자 수정</dt>
        <dd class="col-sm-9">{{ bid.modified_evaluation_count }}건</dd>
        <dt class="col-sm-3">확인 상태</dt>
        <dd class="col-sm-9">
          <template v-if="bid.review_status === 'REVIEWED'">
            확인 완료 — {{ bid.reviewed_by_name }} ({{ formatDateTime(bid.reviewed_at) }})
          </template>
          <template v-else>미확인</template>
        </dd>
      </dl>
      <button
        class="btn"
        :class="bid.review_status === 'REVIEWED' ? 'btn-outline-secondary' : 'btn-success'"
        :disabled="reviewing"
        @click="emit('toggle')"
      >
        {{ bid.review_status === 'REVIEWED' ? '확인 취소' : '확인 완료' }}
      </button>
    </div>
  </div>
</template>
