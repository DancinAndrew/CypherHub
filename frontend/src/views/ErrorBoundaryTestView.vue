<script setup lang="ts">
// Dev-only: 用於驗證 error boundary，造訪 /__test-error 會觸發
throw new Error("[ErrorBoundary 驗證] 刻意拋出錯誤以測試邊界");
</script>

<template>
  <div>此內容不應顯示</div>
</template>
